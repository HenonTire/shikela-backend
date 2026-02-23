from django.db import transaction
import uuid
from catalog.models import Product, ProductVariant
from shop.models import Shop
from .models import *

class CartService:

    @staticmethod
    @transaction.atomic
    def add_to_cart(user, shop_id, product_id, variant_id=None, quantity=1):

        # 1. Validate shop and product
        shop = Shop.objects.get(id=shop_id)
        product = Product.objects.get(id=product_id, shop=shop)

        # 2. Variant (optional)
        variant = None
        if variant_id:
            variant = ProductVariant.objects.get(id=variant_id, product=product)

        # 3. Check stock
        stock = variant.stock if variant else product.stock
        if quantity > stock:
            raise ValueError("Insufficient stock")

        # 4. Get or create active cart
        cart, _ = Cart.objects.get_or_create(
            user=user,
            shop=shop,
            is_active=True
        )

        # 5. Get or create cart item
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={"quantity": quantity}
        )

        if not created:
            new_qty = item.quantity + quantity
            if new_qty > stock:
                raise ValueError("Insufficient stock")
            item.quantity = new_qty
            item.save()

        # 6. Return cart
        return cart

class OrderService:

    @staticmethod
    def _generate_order_number():
        while True:
            candidate = f"ORD-{uuid.uuid4().hex[:12].upper()}"
            if not Order.objects.filter(order_number=candidate).exists():
                return candidate

    @staticmethod
    @transaction.atomic
    def create_order(user, shop, items, delivery_address, payment_method):
        """
        items: list of dicts like:
        [{"product": Product obj, "variant": Variant obj or None, "quantity": 2}]
        """
        # 1. Validate stock
        for item in items:
            stock = item["variant"].stock if item.get("variant") else item["product"].stock
            if item["quantity"] > stock:
                raise ValueError(f"Insufficient stock for {item['product'].name}")

        # 2. Calculate totals
        subtotal = sum(
            (item["variant"].price if item.get("variant") else item["product"].price) * item["quantity"]
            for item in items
        )
        total = subtotal  # + delivery_fee if any

        # 3. Create Order
        order = Order.objects.create(
            order_number=OrderService._generate_order_number(),
            user=user,
            shop=shop,
            subtotal=subtotal,
            total_amount=total,
            status=Order.Status.PENDING,
            payment_method=payment_method,
            delivery_address=delivery_address
        )

        # 4. Create OrderItems
        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                variant=item.get("variant"),
                product_name=item["product"].name,
                sku=item["product"].sku,
                price=item["variant"].price if item.get("variant") else item["product"].price,
                quantity=item["quantity"],
                total=(item["variant"].price if item.get("variant") else item["product"].price) * item["quantity"]
            )

        return order
