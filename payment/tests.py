from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from account.models import User
from catalog.models import Product
from order.models import Order, OrderItem
from payment.models import Earning, Payment
from payment.services.service import PaymentService
from shop.models import Shop


@override_settings(
    SANTIMPAY_PRIVATE_KEY="dummy-private-key",
    SANTIMPAY_TEST_BED=True,
    SANTIMPAY_NOTIFY_URL="http://localhost:8000/payment/webhook/santimpay/",
)
class PayoutRequestTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.shop_owner = User.objects.create_user(
            email="owner@shop.com",
            password="Pass123!",
            role="SHOP_OWNER",
            merchant_id="OWNER-MERCHANT-001",
            marketer_type="CREATOR",
            phone_number="0911000000",
        )
        self.supplier = User.objects.create_user(
            email="supplier@shop.com",
            password="Pass123!",
            role="SUPPLIER",
            merchant_id="SUP-MERCHANT-001",
            marketer_type="CREATOR",
            phone_number="0911223344",
        )
        self.customer = User.objects.create_user(
            email="customer@shop.com",
            password="Pass123!",
            role="CUSTOMER",
            marketer_type="CREATOR",
        )
        self.shop = Shop.objects.create(name="Test Shop", owner=self.shop_owner)
        self.product = Product.objects.create(
            name="Supplier Product X",
            shop=self.shop,
            supplier=self.supplier,
            price=Decimal("120.00"),
            supplier_price=Decimal("80.00"),
            minimum_wholesale_quantity=1,
        )
        self.order = Order.objects.create(
            order_number="ORD-TEST-PAYOUT-001",
            user=self.customer,
            shop=self.shop,
            status=Order.Status.PAID,
            subtotal=Decimal("240.00"),
            total_amount=Decimal("240.00"),
            payment_method="santimpay",
            delivery_address="addr",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=None,
            product_name=self.product.name,
            sku=self.product.sku,
            price=Decimal("120.00"),
            quantity=2,
            total=Decimal("240.00"),
        )
        self.payment = Payment.objects.create(
            order=self.order,
            user=self.customer,
            amount=Decimal("240.00"),
            status=Payment.Status.COMPLETED,
            provider="SANTIMPAY",
            provider_reference="TXN-TEST-1",
            metadata={"merchant_id": self.shop_owner.merchant_id},
        )
        PaymentService(merchant_id=self.shop_owner.merchant_id).record_settlement_earnings(self.payment)

    @patch("payment.services.service.PaymentService._pay_user")
    def test_payout_executes_only_on_user_request(self, mock_pay_user):
        mock_pay_user.return_value = {
            "tx_id": "PYO-TEST-1",
            "method": "TELEBIRR",
            "account": "0911223344",
            "provider_response": {"id": "PAYOUT-REF-1"},
        }
        self.client.force_authenticate(self.supplier)

        response = self.client.post(
            "/payment/payouts/request/",
            {"confirm": True},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "COMPLETED")
        self.assertEqual(response.data["amount"], "160.00")
        self.assertEqual(response.data["provider_reference"], "PAYOUT-REF-1")
        self.assertEqual(mock_pay_user.call_count, 1)
        self.assertEqual(Earning.objects.filter(user=self.supplier, status=Earning.Status.AVAILABLE).count(), 0)

    @patch("payment.services.service.PaymentService._pay_user")
    def test_non_allocated_user_cannot_request_payout(self, mock_pay_user):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            "/payment/payouts/request/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("No available earnings", response.data["detail"])
        self.assertEqual(mock_pay_user.call_count, 0)

    @patch("payment.services.service.PaymentService._pay_user")
    def test_user_can_list_payout_history(self, mock_pay_user):
        mock_pay_user.return_value = {
            "tx_id": "PYO-TEST-2",
            "method": "TELEBIRR",
            "account": "0911223344",
            "provider_response": {"id": "PAYOUT-REF-2"},
        }
        self.client.force_authenticate(self.supplier)
        create_resp = self.client.post(
            "/payment/payouts/request/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.data)

        history_resp = self.client.get("/payment/payouts/history/")
        self.assertEqual(history_resp.status_code, 200, history_resp.data)
        self.assertEqual(len(history_resp.data["history"]), 1)
        self.assertEqual(history_resp.data["available_earnings"], "0.00")
