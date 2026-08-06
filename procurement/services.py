from __future__ import annotations

import hashlib
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg
from django.utils import timezone

from account.models import User
from catalog.models import Category, Product, ProductVariant
from .models import PurchaseOrder, SupplierRelationship

LOW_STOCK_THRESHOLD = 5


def _avatar_color(seed: str) -> str:
    digest = hashlib.md5(seed.encode()).hexdigest()
    return f"#{digest[:6].upper()}"


def _supplier_display_name(supplier: User) -> str:
    full = f"{supplier.first_name} {supplier.last_name}".strip()
    return full or supplier.email


def _supplier_categories(supplier: User) -> str:
    names = (
        Product.objects.filter(supplier=supplier, category__isnull=False)
        .values_list("category__name", flat=True)
        .distinct()[:3]
    )
    return ", ".join(names) if names else "General"


def _supplier_rating(supplier: User) -> float:
    agg = Product.objects.filter(supplier=supplier).aggregate(avg=Avg("reviews__rating"))
    return round(float(agg["avg"] or 0), 1)


def _order_total(order: PurchaseOrder) -> Decimal:
    return sum((item.quantity * item.unit_price for item in order.items.all()), Decimal("0.00"))


def get_supplier_dashboard_data(shop) -> dict:
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_end = month_start - timedelta(seconds=1)
    prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    shop_orders = list(
        PurchaseOrder.objects.filter(shop=shop).prefetch_related("items", "supplier")
    )

    this_month_orders = [o for o in shop_orders if o.created_at >= month_start]
    prev_month_orders = [o for o in shop_orders if prev_month_start <= o.created_at <= prev_month_end]

    this_month_amount = sum((_order_total(o) for o in this_month_orders), Decimal("0.00"))
    prev_month_amount = sum((_order_total(o) for o in prev_month_orders), Decimal("0.00"))

    if prev_month_amount > 0:
        trend_pct = ((this_month_amount - prev_month_amount) / prev_month_amount) * 100
        trend = f"{'+' if trend_pct >= 0 else ''}{trend_pct:.0f}%"
    else:
        trend = "New" if this_month_amount > 0 else "+0%"

    active_statuses = {"PENDING", "PREPARING", "ACCEPTED", "IN_TRANSIT"}
    active_orders = [o for o in shop_orders if o.status in active_statuses]
    pending_deliveries = [o for o in shop_orders if o.status == "IN_TRANSIT"]

    relationships = list(SupplierRelationship.objects.filter(shop=shop).select_related("supplier"))
    total_suppliers = len(relationships)

    low_stock_variants = list(
        ProductVariant.objects.filter(product__shop=shop, stock__lte=LOW_STOCK_THRESHOLD)
        .select_related("product", "product__supplier")
    )

    quick_stats = [
        {"label": "Monthly Purchases", "value": f"ETB {this_month_amount:,.2f}", "icon": "trending_up", "trend": trend},
        {"label": "Total Suppliers", "value": str(total_suppliers), "icon": "groups", "trend": ""},
        {"label": "Active Orders", "value": str(len(active_orders)), "icon": "receipt_long", "trend": ""},
        {"label": "Pending Deliveries", "value": str(len(pending_deliveries)), "icon": "local_shipping", "trend": ""},
        {"label": "Low Stock Products", "value": str(len(low_stock_variants)), "icon": "warning", "trend": ""},
    ]

    reorder_suggestions = []
    for variant in low_stock_variants[:10]:
        product = variant.product
        supplier = product.supplier
        stock = variant.stock
        urgency = "critical" if stock <= 0 else "urgent" if stock <= 2 else "moderate"
        reorder_suggestions.append({
            "product": product.name,
            "current_stock": stock,
            "reorder_qty": max(product.minimum_wholesale_quantity, 10),
            "supplier": _supplier_display_name(supplier) if supplier else "Unassigned",
            "unit_price": float(product.supplier_price or product.price),
            "eta": "3-5 days",
            "urgency": urgency,
        })

    trusted_suppliers = []
    for rel in relationships:
        if not rel.is_trusted:
            continue
        supplier = rel.supplier
        last_order = next((o for o in shop_orders if o.supplier_id == supplier.id), None)
        trusted_suppliers.append({
            "id": str(supplier.id),
            "name": _supplier_display_name(supplier),
            "rating": _supplier_rating(supplier),
            "speed": "Fast",
            "categories": _supplier_categories(supplier),
            "last_interaction": last_order.created_at.strftime("%b %d, %Y") if last_order else "No orders yet",
            "verified": True,
            "avatar_color": _avatar_color(str(supplier.id)),
        })

    related_supplier_ids = {rel.supplier_id for rel in relationships}
    market_suppliers = []
    for supplier in User.objects.filter(role="SUPPLIER").exclude(id__in=related_supplier_ids):
        products = Product.objects.filter(supplier=supplier, is_active=True)
        if not products.exists():
            continue
        min_price = products.order_by("price").values_list("price", flat=True).first()
        market_suppliers.append({
            "id": str(supplier.id),
            "name": _supplier_display_name(supplier),
            "specialties": _supplier_categories(supplier),
            "start_price": f"ETB {min_price:,.2f}" if min_price else "Contact for pricing",
            "region": "Ethiopia",
            "delivery": "3-7 days",
            "rating": _supplier_rating(supplier),
            "verified": False,
            "avatar_color": _avatar_color(str(supplier.id)),
        })

    orders_payload = []
    for order in sorted(shop_orders, key=lambda o: o.created_at, reverse=True)[:20]:
        orders_payload.append({
            "id": f"PO-{str(order.id)[:8].upper()}",
            "supplier": _supplier_display_name(order.supplier),
            "product_count": order.total_product_count(),
            "amount": f"ETB {_order_total(order):,.2f}",
            "order_date": order.created_at.strftime("%b %d, %Y"),
            "eta": order.eta.strftime("%b %d, %Y") if order.eta else "TBD",
            "status": order.status.lower(),
        })

    activities = []
    for order in sorted(shop_orders, key=lambda o: o.updated_at, reverse=True)[:10]:
        activities.append({
            "title": f"Order {order.status.replace('_', ' ').title()}",
            "subtitle": f"{_supplier_display_name(order.supplier)} - PO-{str(order.id)[:8].upper()}",
            "time": order.updated_at.strftime("%b %d, %H:%M"),
            "icon": "check_circle" if order.status == "DELIVERED" else "history",
            "color": _avatar_color(str(order.id)),
        })

    return {
        "quick_stats": quick_stats,
        "reorder_suggestions": reorder_suggestions,
        "trusted_suppliers": trusted_suppliers,
        "orders": orders_payload,
        "market_suppliers": market_suppliers,
        "activities": activities,
        "category_chips": list(Category.objects.values_list("name", flat=True).distinct()[:10]),
        "region_chips": ["Addis Ababa", "Hosaena", "Hawassa", "Bahir Dar"],
        "speed_chips": ["Fast", "Standard", "Economy"],
        "rating_chips": ["4.5+", "4.0+", "3.5+"],
    }