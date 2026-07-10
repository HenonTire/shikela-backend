from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from order.models import Order
from payment.models import Refund

from .models import (
    PlatformDailyAnalytics,
    PlatformWeeklyAnalytics,
    PlatformMonthlyAnalytics,
    PlatformYearlyAnalytics,
    ShopDailyAnalytics,
    ShopWeeklyAnalytics,
    ShopMonthlyAnalytics,
    ShopYearlyAnalytics,
    SupplierDailyAnalytics,
    SupplierWeeklyAnalytics,
    SupplierMonthlyAnalytics,
    SupplierYearlyAnalytics,
)


PLATFORM_FEE_RATE = Decimal("0.10")


def _decimal(value) -> Decimal:
    return Decimal(str(value or "0"))


def _get_locked_row(model, **lookup):
    row = model.objects.select_for_update().filter(**lookup).first()
    if row:
        return row
    return model.objects.create(**lookup)


def _accumulate(model, filters: dict, increments: dict) -> None:
    """Lock (or create) a period row and atomically bump its counters."""
    row = _get_locked_row(model, **filters)
    updates = {field: F(field) + value for field, value in increments.items()}
    updates["updated_at"] = timezone.now()
    model.objects.filter(pk=row.pk).update(**updates)


def _period_bounds(for_date=None):
    """Returns (day, week_start, month_start, year_start) for a given date.
    Week starts on Monday."""
    day = for_date or timezone.localdate()
    week_start = day - timedelta(days=day.weekday())
    month_start = day.replace(day=1)
    year_start = day.replace(month=1, day=1)
    return day, week_start, month_start, year_start


class AnalyticsService:
    @staticmethod
    @transaction.atomic
    def handle_payment_success(order: Order) -> None:
        if order.status != Order.Status.PAID:
            return

        day, week_start, month_start, year_start = _period_bounds()
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

        # ---- Shop ----
        shop_increments = {
            "revenue": order_total,
            "orders_count": 1,
            "units_sold": units_sold,
            "platform_fee": platform_fee,
        }
        shop_periods = [
            (ShopDailyAnalytics, "date", day),
            (ShopWeeklyAnalytics, "week_start", week_start),
            (ShopMonthlyAnalytics, "month_start", month_start),
            (ShopYearlyAnalytics, "year_start", year_start),
        ]
        for model, field, value in shop_periods:
            _accumulate(model, {"shop": order.shop, field: value}, shop_increments)

        # ---- Platform ----
        platform_increments = {
            "total_gmv": order_total,
            "total_platform_fee": platform_fee,
            "total_orders": 1,
        }
        platform_periods = [
            (PlatformDailyAnalytics, "date", day),
            (PlatformWeeklyAnalytics, "week_start", week_start),
            (PlatformMonthlyAnalytics, "month_start", month_start),
            (PlatformYearlyAnalytics, "year_start", year_start),
        ]
        for model, field, value in platform_periods:
            _accumulate(model, {field: value}, platform_increments)

        # ---- Supplier rollup ----
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
            supplier_increments = {
                "revenue": payload["revenue"],
                "units_sold": payload["units"],
                "orders_count": 1,
            }
            supplier_periods = [
                (SupplierDailyAnalytics, "date", day),
                (SupplierWeeklyAnalytics, "week_start", week_start),
                (SupplierMonthlyAnalytics, "month_start", month_start),
                (SupplierYearlyAnalytics, "year_start", year_start),
            ]
            for model, field, value in supplier_periods:
                _accumulate(
                    model,
                    {"supplier": payload["supplier"], field: value},
                    supplier_increments,
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
        ref_date = timezone.localdate(refund.updated_at or timezone.now())
        day, week_start, month_start, year_start = _period_bounds(ref_date)
        platform_fee = (refund_amount * PLATFORM_FEE_RATE).quantize(Decimal("0.01"))

        # ---- Shop ----
        shop_increments = {
            "revenue": -refund_amount,
            "refund_amount": refund_amount,
            "platform_fee": -platform_fee,
        }
        shop_periods = [
            (ShopDailyAnalytics, "date", day),
            (ShopWeeklyAnalytics, "week_start", week_start),
            (ShopMonthlyAnalytics, "month_start", month_start),
            (ShopYearlyAnalytics, "year_start", year_start),
        ]
        for model, field, value in shop_periods:
            _accumulate(model, {"shop": order.shop, field: value}, shop_increments)

        # ---- Platform ----
        platform_increments = {
            "total_gmv": -refund_amount,
            "total_platform_fee": -platform_fee,
        }
        platform_periods = [
            (PlatformDailyAnalytics, "date", day),
            (PlatformWeeklyAnalytics, "week_start", week_start),
            (PlatformMonthlyAnalytics, "month_start", month_start),
            (PlatformYearlyAnalytics, "year_start", year_start),
        ]
        for model, field, value in platform_periods:
            _accumulate(model, {field: value}, platform_increments)

        # ---- Supplier rollup ----
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
            supplier_increments = {"revenue": -payload["refund"]}
            supplier_periods = [
                (SupplierDailyAnalytics, "date", day),
                (SupplierWeeklyAnalytics, "week_start", week_start),
                (SupplierMonthlyAnalytics, "month_start", month_start),
                (SupplierYearlyAnalytics, "year_start", year_start),
            ]
            for model, field, value in supplier_periods:
                _accumulate(
                    model,
                    {"supplier": payload["supplier"], field: value},
                    supplier_increments,
                )