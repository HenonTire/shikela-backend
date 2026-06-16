from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from order.models import Order
from payment.models import Refund

from .models import (
    PlatformDailyAnalytics,
    ShopDailyAnalytics,
    SupplierDailyAnalytics,
)


PLATFORM_FEE_RATE = Decimal("0.10")


def _decimal(value) -> Decimal:
    return Decimal(str(value or "0"))


def _get_locked_row(model, **lookup):
    row = model.objects.select_for_update().filter(**lookup).first()
    if row:
        return row
    return model.objects.create(**lookup)


class AnalyticsService:
    @staticmethod
    @transaction.atomic
    def handle_payment_success(order: Order) -> None:
        if order.status != Order.Status.PAID:
            return

        today = timezone.localdate()
        items = list(
            order.items.select_related(
                "product__supplier",
                "variant__product__supplier",
                "product",
            ).all()
        )

        order_total = _decimal(order.total_amount)
        units_sold = sum(int(item.quantity) for item in items)
        platform_fee = (order_total * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))

        shop_row = _get_locked_row(ShopDailyAnalytics, shop=order.shop, date=today)
        ShopDailyAnalytics.objects.filter(pk=shop_row.pk).update(
            revenue=F("revenue") + order_total,
            orders_count=F("orders_count") + 1,
            units_sold=F("units_sold") + units_sold,
            platform_fee=F("platform_fee") + platform_fee,
            updated_at=timezone.now(),
        )

        platform_row = _get_locked_row(PlatformDailyAnalytics, date=today)
        PlatformDailyAnalytics.objects.filter(pk=platform_row.pk).update(
            total_gmv=F("total_gmv") + order_total,
            total_platform_fee=F("total_platform_fee") + platform_fee,
            total_orders=F("total_orders") + 1,
            updated_at=timezone.now(),
        )

        supplier_rollup = {}
        for item in items:
            product = item.product if item.product else (item.variant.product if item.variant else None)
            supplier = getattr(product, "supplier", None) if product else None
            if not supplier:
                continue
            supplier_price = product.supplier_price if product.supplier_price is not None else item.price
            line_amount = _decimal(supplier_price) * _decimal(item.quantity)
            payload = supplier_rollup.setdefault(
                supplier.id,
                {"supplier": supplier, "revenue": Decimal("0.00"), "units": 0},
            )
            payload["revenue"] += line_amount
            payload["units"] += int(item.quantity)

        for payload in supplier_rollup.values():
            row = _get_locked_row(
                SupplierDailyAnalytics,
                supplier=payload["supplier"],
                date=today,
            )
            SupplierDailyAnalytics.objects.filter(pk=row.pk).update(
                revenue=F("revenue") + payload["revenue"],
                units_sold=F("units_sold") + payload["units"],
                orders_count=F("orders_count") + 1,
                updated_at=timezone.now(),
            )

    @staticmethod
    @transaction.atomic
    def handle_refund_approved(refund: Refund) -> None:
        if refund.status != Refund.Status.APPROVED:
            return

        order = refund.payment.order
        items = list(
            order.items.select_related(
                "product__supplier",
                "variant__product__supplier",
                "product",
            ).all()
        )
        item_total = sum((_decimal(item.total) for item in items), Decimal("0.00"))
        if item_total <= Decimal("0.00"):
            return

        refund_amount = _decimal(refund.amount)
        refund_ratio = min(Decimal("1.00"), refund_amount / item_total)
        today = timezone.localdate(refund.updated_at or timezone.now())

        shop_row = _get_locked_row(ShopDailyAnalytics, shop=order.shop, date=today)
        platform_fee = (refund_amount * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))
        ShopDailyAnalytics.objects.filter(pk=shop_row.pk).update(
            revenue=F("revenue") - refund_amount,
            refund_amount=F("refund_amount") + refund_amount,
            platform_fee=F("platform_fee") - platform_fee,
            updated_at=timezone.now(),
        )

        platform_row = _get_locked_row(PlatformDailyAnalytics, date=today)
        PlatformDailyAnalytics.objects.filter(pk=platform_row.pk).update(
            total_gmv=F("total_gmv") - refund_amount,
            total_platform_fee=F("total_platform_fee") - platform_fee,
            updated_at=timezone.now(),
        )

        supplier_rollup = {}
        for item in items:
            product = item.product if item.product else (item.variant.product if item.variant else None)
            supplier = getattr(product, "supplier", None) if product else None
            if not supplier:
                continue
            supplier_price = product.supplier_price if product.supplier_price is not None else item.price
            line_amount = _decimal(supplier_price) * _decimal(item.quantity)
            payload = supplier_rollup.setdefault(
                supplier.id,
                {"supplier": supplier, "refund": Decimal("0.00")},
            )
            payload["refund"] += (line_amount * refund_ratio)

        for payload in supplier_rollup.values():
            row = _get_locked_row(
                SupplierDailyAnalytics,
                supplier=payload["supplier"],
                date=today,
            )
            SupplierDailyAnalytics.objects.filter(pk=row.pk).update(
                revenue=F("revenue") - payload["refund"],
                updated_at=timezone.now(),
            )
