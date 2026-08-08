from decimal import Decimal

from django.contrib.auth import get_user_model

from catalog.models import Product
from order.models import Order, OrderItem
from shop.models import Shop
from analytics.services import AnalyticsService
from analytics.models import ShopDailyAnalytics, SupplierDailyAnalytics

User = get_user_model()

print("=" * 60)
print("STEP 1: Create (or reuse) a test supplier user")
print("=" * 60)

# Adjust the field names below (phone/email/username) to match whatever
# your User model actually requires — check with:
#   [f.name for f in User._meta.get_fields() if f.concrete]
# if this errors on a missing/unexpected required field.
supplier_user, created = User.objects.get_or_create(
    phone_number="0900000001",
    defaults={
        "role": "SUPPLIER",
        "first_name": "Test",
        "last_name": "Supplier",
    },
)
if not created and supplier_user.role != "SUPPLIER":
    supplier_user.role = "SUPPLIER"
    supplier_user.save(update_fields=["role"])

print(("Created" if created else "Reused"), "supplier user:", supplier_user.id, "role=", supplier_user.role)

print("\n" + "=" * 60)
print("STEP 2: Assign supplier to a product")
print("=" * 60)
product = Product.objects.first()
if not product:
    print("ABORT: no Product exists at all.")
else:
    product.supplier = supplier_user
    product.save(update_fields=["supplier"])
    product.refresh_from_db()
    print("Product:", product.id, "supplier now:", product.supplier_id)

print("\n" + "=" * 60)
print("STEP 3: Find a shop and a customer")
print("=" * 60)
shop = Shop.objects.first()
print("Shop:", shop.id if shop else None)

customer = User.objects.exclude(id=supplier_user.id).first()
print("Customer:", customer.id if customer else None)

print("\n" + "=" * 60)
print("STEP 4: Create order + item, mark PAID, run analytics")
print("=" * 60)

ready = bool(product and shop and customer and product.supplier_id)
if not ready:
    print("ABORT: missing one of product/shop/customer/product.supplier.")
else:
    order = Order.objects.create(
        order_number="TEST-0004",
        user=customer,
        shop=shop,
        status=Order.Status.PENDING,
        subtotal=Decimal("50.00"),
        total_amount=Decimal("50.00"),
        payment_method="TEST",
        delivery_address="Test address",
    )
    print("Created order:", order.id, order.order_number)

    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        sku=getattr(product, "sku", "TEST-SKU"),
        price=Decimal("25.00"),
        quantity=2,
        total=Decimal("50.00"),
    )
    print("Created order item: qty=2, total=50.00")

    order.status = Order.Status.PAID
    order.save(update_fields=["status", "updated_at"])
    print("Order marked PAID")

    AnalyticsService.handle_payment_success(order)
    print("AnalyticsService.handle_payment_success called")

    print("\n--- RESULTS ---")
    print("Shop daily:", list(
        ShopDailyAnalytics.objects.filter(shop=shop).values(
            "date", "revenue", "orders_count", "units_sold"
        )
    ))
    print("Supplier daily:", list(
        SupplierDailyAnalytics.objects.filter(supplier=product.supplier).values(
            "date", "revenue", "units_sold", "orders_count"
        )
    ))