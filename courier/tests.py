from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from account.models import User
from catalog.models import Category, Product, ProductVariant
from courier.models import CourierProfile, Shipment
from courier.services import LogisticsError, assign_courier, create_shipment_for_order, update_shipment_status
from order.models import Order, OrderItem
from shop.models import Shop


class CourierFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email="owner_courier@example.com",
            password="Pass123!",
            role="SHOP_OWNER",
        )
        self.customer = User.objects.create_user(
            email="customer_courier@example.com",
            password="Pass123!",
            role="CUSTOMER",
        )
        self.courier_user = User.objects.create_user(
            email="courier_one@example.com",
            password="Pass123!",
            role="COURIER",
        )
        self.other_courier = User.objects.create_user(
            email="courier_two@example.com",
            password="Pass123!",
            role="COURIER",
        )

        CourierProfile.objects.create(user=self.courier_user, phone="+251911000001", vehicle_type="BIKE")
        CourierProfile.objects.create(user=self.other_courier, phone="+251911000002", vehicle_type="CAR")

        self.shop = Shop.objects.create(name="Courier Shop", owner=self.owner)
        self.category = Category.objects.create(name="Courier Category")
        self.product = Product.objects.create(
            name="Courier Product",
            shop=self.shop,
            category=self.category,
            price=Decimal("100.00"),
            supplier_price=Decimal("70.00"),
            minimum_wholesale_quantity=1,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="Default",
            price=Decimal("100.00"),
            stock=20,
        )
        self.order = Order.objects.create(
            order_number="ORD-COURIER-001",
            user=self.customer,
            shop=self.shop,
            status=Order.Status.PAID,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            payment_method="santimpay",
            delivery_address="Addis Ababa",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=self.variant,
            product_name=self.product.name,
            sku=self.product.sku,
            price=Decimal("100.00"),
            quantity=1,
            total=Decimal("100.00"),
        )

    def _create_paid_order(self, order_number: str, delivery_address: str = "Addis Ababa") -> Order:
        order = Order.objects.create(
            order_number=order_number,
            user=self.customer,
            shop=self.shop,
            status=Order.Status.PAID,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            payment_method="santimpay",
            delivery_address=delivery_address,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            variant=self.variant,
            product_name=self.product.name,
            sku=self.product.sku,
            price=Decimal("100.00"),
            quantity=1,
            total=Decimal("100.00"),
        )
        return order

    def test_create_shipment_auto_assigns_available_courier(self):
        shipment = create_shipment_for_order(self.order)
        self.assertEqual(shipment.order_id, self.order.id)
        self.assertIsNotNone(shipment.courier_id)
        self.assertIn(shipment.courier_id, {self.courier_user.id, self.other_courier.id})
        self.assertIsNotNone(shipment.assigned_at)
        self.assertEqual(shipment.status, Shipment.Status.PENDING)

    def test_assign_courier_validates_role(self):
        shipment = create_shipment_for_order(self.order)
        assigned = assign_courier(shipment, self.courier_user)
        self.assertEqual(assigned.courier_id, self.courier_user.id)
        self.assertIsNotNone(assigned.assigned_at)

        with self.assertRaises(LogisticsError):
            assign_courier(shipment, self.customer)

    @patch("courier.services.NotificationService.notify")
    def test_out_for_delivery_is_not_duplicated_or_regressed_by_in_transit(self, mock_notify):
        shipment = create_shipment_for_order(self.order)

        update_shipment_status(shipment, Shipment.Status.OUT_FOR_DELIVERY, payload={"status": "OUT_FOR_DELIVERY"})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.SHIPPED)

        update_shipment_status(shipment, Shipment.Status.OUT_FOR_DELIVERY, payload={"status": "OUT_FOR_DELIVERY"})
        update_shipment_status(shipment, Shipment.Status.IN_TRANSIT, payload={"status": "IN_TRANSIT"})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.SHIPPED)
        self.assertEqual(mock_notify.call_count, 1)

    def test_courier_dashboard_status_update(self):
        shipment = create_shipment_for_order(self.order)
        self.client.force_authenticate(user=shipment.courier)
        response = self.client.post(
            f"/courier/shipments/{shipment.id}/status/",
            {"status": "DELIVERED"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        shipment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(shipment.status, Shipment.Status.DELIVERED)
        self.assertEqual(self.order.status, Order.Status.DELIVERED)

    def test_courier_list_returns_only_assigned_shipments(self):
        first_shipment = create_shipment_for_order(self.order)
        second_order = self._create_paid_order("ORD-COURIER-002", delivery_address="Hawassa")
        second_shipment = create_shipment_for_order(second_order)
        self.assertNotEqual(first_shipment.courier_id, second_shipment.courier_id)

        self.client.force_authenticate(user=first_shipment.courier)
        response = self.client.get("/courier/shipments/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(first_shipment.id))

    def test_round_robin_auto_assignment_across_orders(self):
        first_shipment = create_shipment_for_order(self.order)
        second_order = self._create_paid_order("ORD-COURIER-003", delivery_address="Jimma")
        second_shipment = create_shipment_for_order(second_order)
        third_order = self._create_paid_order("ORD-COURIER-004", delivery_address="Adama")
        third_shipment = create_shipment_for_order(third_order)

        self.assertNotEqual(first_shipment.courier_id, second_shipment.courier_id)
        self.assertEqual(first_shipment.courier_id, third_shipment.courier_id)
