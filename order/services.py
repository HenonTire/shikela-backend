from django.db import transaction
import uuid
from catalog.models import Product, ProductVariant
from shop.models import Shop
from .models import *
from marketer.models import MarketerContract, MarketerContractProduct

class CartService:

    @staticmethod
    def _resolve_variant_for_product(product, variant=None):
        if variant:
            return variant
        return ProductVariant.objects.filter(product=product).order_by("created_at").first()

    @staticmethod
    @transaction.atomic
    def add_to_cart(user, shop_id, product_id, variant_id=None, quantity=1, marketer_contract_id=None):

        # 1. Validate shop and product
        shop = Shop.objects.get(id=shop_id)
        product = Product.objects.get(id=product_id, shop=shop)

        # 2. Variant (optional)
        variant = None
        if variant_id:
            variant = ProductVariant.objects.get(id=variant_id, product=product)
        else:
            variant = CartService._resolve_variant_for_product(product)

        # 2b. Optional marketer contract
        marketer_contract = None
        if marketer_contract_id:
            marketer_contract = MarketerContract.objects.select_related("shop").filter(id=marketer_contract_id).first()
            if not marketer_contract or not marketer_contract.is_active():
                raise ValueError("Marketer contract is not active")
            if marketer_contract.shop_id != shop.id:
                raise ValueError("Marketer contract does not belong to this shop")
            if not MarketerContractProduct.objects.filter(contract=marketer_contract, product=product).exists():
                raise ValueError("Product is not part of the marketer contract")

        # 3. Check stock
        if not variant:
            raise ValueError("No variant available for this product")
        stock = variant.stock
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
            if marketer_contract:
                item.marketer_contract = marketer_contract
            item.save()
        elif marketer_contract:
            item.marketer_contract = marketer_contract
            item.save(update_fields=["marketer_contract"])

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
    def _resolve_variant_for_item(item):
        variant = item.get("variant")
        if variant:
            return variant
        product = item["product"]
        return ProductVariant.objects.filter(product=product).order_by("created_at").first()

    @staticmethod
    @transaction.atomic
    def create_order(user, shop, items, delivery_address, payment_method):
        """
        items: list of dicts like:
        [{"product": Product obj, "variant": Variant obj or None, "quantity": 2}]
        """
        normalized_items = []
        # 1. Validate stock
        for item in items:
            resolved_variant = OrderService._resolve_variant_for_item(item)
            if not resolved_variant:
                raise ValueError(f"No variant available for {item['product'].name}")
            stock = resolved_variant.stock
            if item["quantity"] > stock:
                raise ValueError(f"Insufficient stock for {item['product'].name}")
            contract = item.get("marketer_contract")
            if contract:
                if not contract.is_active():
                    raise ValueError("Marketer contract is not active")
                if contract.shop_id != shop.id:
                    raise ValueError("Marketer contract does not belong to this shop")
                if not MarketerContractProduct.objects.filter(contract=contract, product=item["product"]).exists():
                    raise ValueError("Product is not part of the marketer contract")
            normalized_items.append(
                {
                    "product": item["product"],
                    "variant": resolved_variant,
                    "quantity": item["quantity"],
                    "marketer_contract": contract,
                }
            )

        # 2. Calculate totals
        subtotal = sum(
            (item["variant"].price if item.get("variant") else item["product"].price) * item["quantity"]
            for item in normalized_items
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
        for item in normalized_items:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                variant=item.get("variant"),
                marketer_contract=item.get("marketer_contract"),
                product_name=item["product"].name,
                sku=item["product"].sku,
                price=item["variant"].price if item.get("variant") else item["product"].price,
                quantity=item["quantity"],
                total=(item["variant"].price if item.get("variant") else item["product"].price) * item["quantity"]
            )

        return order
