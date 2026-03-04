from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from payment.models import Earning
from marketer.models import MarketerCommission
from shop.models import Shop

from .models import (
    MarketerDailyAnalytics,
    PlatformDailyAnalytics,
    ShopDailyAnalytics,
    SupplierDailyAnalytics,
)


def _decimal(value) -> Decimal:
    return Decimal(str(value or "0"))


def _last_days_series(qs, date_field: str, value_field: str, key_name: str, days: int = 7):
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    rows = qs.filter(**{f"{date_field}__gte": start}).values(date_field).annotate(
        total=Sum(value_field)
    )
    by_date = {row[date_field]: _decimal(row["total"]) for row in rows}
    result = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        result.append({"date": str(day), key_name: str(by_date.get(day, Decimal("0.00")))})
    return result


def get_shop_dashboard(shop: Shop) -> dict:
    today = timezone.localdate()
    month_start = today.replace(day=1)
    qs = ShopDailyAnalytics.objects.filter(shop=shop)
    totals = qs.aggregate(
        total_revenue=Sum("revenue"),
        orders_count=Sum("orders_count"),
        units_sold=Sum("units_sold"),
        refund_amount=Sum("refund_amount"),
        commission_paid=Sum("commission_paid"),
        platform_fee=Sum("platform_fee"),
    )
    this_month = qs.filter(date__gte=month_start).aggregate(total=Sum("revenue"))["total"]
    today_orders = qs.filter(date=today).aggregate(total=Sum("orders_count"))["total"]
    return {
        "total_revenue": str(_decimal(totals["total_revenue"])),
        "this_month_revenue": str(_decimal(this_month)),
        "orders_count": int(totals["orders_count"] or 0),
        "units_sold": int(totals["units_sold"] or 0),
        "refund_amount": str(_decimal(totals["refund_amount"])),
        "commission_paid": str(_decimal(totals["commission_paid"])),
        "platform_fee": str(_decimal(totals["platform_fee"])),
        "today_orders": int(today_orders or 0),
        "last_7_days": _last_days_series(qs, "date", "revenue", "revenue", days=7),
    }


def get_supplier_dashboard(user) -> dict:
    today = timezone.localdate()
    month_start = today.replace(day=1)
    qs = SupplierDailyAnalytics.objects.filter(supplier=user)
    totals = qs.aggregate(
        total_revenue=Sum("revenue"),
        units_sold=Sum("units_sold"),
        orders_count=Sum("orders_count"),
    )
    this_month = qs.filter(date__gte=month_start).aggregate(total=Sum("revenue"))["total"]
    pending_payout = (
        Earning.objects.filter(user=user, status=Earning.Status.AVAILABLE)
        .aggregate(total=Sum("amount"))["total"]
    )
    return {
        "total_revenue": str(_decimal(totals["total_revenue"])),
        "this_month_revenue": str(_decimal(this_month)),
        "units_sold": int(totals["units_sold"] or 0),
        "orders_count": int(totals["orders_count"] or 0),
        "pending_payout": str(_decimal(pending_payout)),
        "last_7_days": _last_days_series(qs, "date", "revenue", "revenue", days=7),
    }


def get_marketer_dashboard(user) -> dict:
    today = timezone.localdate()
    month_start = today.replace(day=1)
    qs = MarketerDailyAnalytics.objects.filter(marketer=user)
    totals = qs.aggregate(
        total_revenue=Sum("revenue_generated"),
        commission_earned=Sum("commission_earned"),
        orders_count=Sum("orders_count"),
    )
    this_month = qs.filter(date__gte=month_start).aggregate(total=Sum("revenue_generated"))["total"]
    pending_commissions = (
        MarketerCommission.objects.filter(contract__marketer=user, status=MarketerCommission.Status.PENDING)
        .aggregate(total=Sum("amount"))["total"]
    )
    return {
        "total_revenue_generated": str(_decimal(totals["total_revenue"])),
        "commission_earned": str(_decimal(totals["commission_earned"])),
        "this_month_revenue": str(_decimal(this_month)),
        "orders_count": int(totals["orders_count"] or 0),
        "pending_commissions": str(_decimal(pending_commissions)),
        "last_7_days": _last_days_series(qs, "date", "revenue_generated", "revenue", days=7),
    }


def get_admin_dashboard() -> dict:
    today = timezone.localdate()
    month_start = today.replace(day=1)
    qs = PlatformDailyAnalytics.objects.all()
    totals = qs.aggregate(
        total_gmv=Sum("total_gmv"),
        total_platform_fee=Sum("total_platform_fee"),
        total_orders=Sum("total_orders"),
    )
    this_month = qs.filter(date__gte=month_start).aggregate(total=Sum("total_gmv"))["total"]
    return {
        "total_gmv": str(_decimal(totals["total_gmv"])),
        "this_month_gmv": str(_decimal(this_month)),
        "total_platform_fee": str(_decimal(totals["total_platform_fee"])),
        "total_orders": int(totals["total_orders"] or 0),
        "last_7_days": _last_days_series(qs, "date", "total_gmv", "gmv", days=7),
    }
