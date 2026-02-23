from rest_framework import status
from rest_framework.test import APITestCase

from account.models import User
from catalog.models import Category, Product, ProductVariant
from shop.models import Shop

from .models import Cart, CartItem, Order


class OrderViewsTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner_order_tests@example.com",
            password="pass1234",
            role="SHOP_OWNER",
            marketer_type="CREATOR",
        )
        self.buyer = User.objects.create_user(
            email="buyer_order_tests@example.com",
            password="pass1234",
            role="CUSTOMER",
            marketer_type="CREATOR",
        )

        self.shop = Shop.objects.create(name="Order Test Shop", owner=self.owner)
        self.category = Category.objects.create(name="Order Test Category")
        self.product = Product.objects.create(
            name="Order Test Product",
            shop=self.shop,
            category=self.category,
            price="100.00",
            description="test",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="Default",
            price="120.00",
            stock=20,
        )

        self.client.force_authenticate(user=self.buyer)

    def test_buynow_creates_order_and_generates_unique_order_numbers(self):
        payload = {
            "shop_id": str(self.shop.id),
            "product_id": str(self.product.id),
            "variant_id": str(self.variant.id),
            "quantity": 1,
            "delivery_address": "123 Main St",
            "payment_method": "santimpay",
        }

        first = self.client.post("/order/create/", payload, format="json")
        second = self.client.post("/order/create/", payload, format="json")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 2)

        numbers = list(Order.objects.values_list("order_number", flat=True))
        self.assertEqual(len(numbers), len(set(numbers)))
        for order_number in numbers:
            self.assertTrue(order_number)

    def test_checkout_cart_creates_order_from_active_cart(self):
        cart = Cart.objects.create(user=self.buyer, shop=self.shop, is_active=True)
        CartItem.objects.create(cart=cart, product=self.product, variant=self.variant, quantity=2)

        response = self.client.post(
            "/order/cart/checkout/",
            {
                "delivery_address": "123 Main St",
                "payment_method": "santimpay",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.shop_id, self.shop.id)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 2)

    def test_list_orders_returns_user_orders(self):
        payload = {
            "shop_id": str(self.shop.id),
            "product_id": str(self.product.id),
            "variant_id": str(self.variant.id),
            "quantity": 1,
            "delivery_address": "123 Main St",
            "payment_method": "santimpay",
        }
        self.client.post("/order/create/", payload, format="json")

        response = self.client.get("/order/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("orders", response.data)
        self.assertEqual(len(response.data["orders"]), 1)
