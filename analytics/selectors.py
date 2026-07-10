from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from payment.models import Earning
from shop.models import Shop

from .models import (
    PlatformDailyAnalytics,
    PlatformMonthlyAnalytics,
    PlatformWeeklyAnalytics,
    PlatformYearlyAnalytics,
    ShopDailyAnalytics,
    ShopMonthlyAnalytics,
    ShopWeeklyAnalytics,
    ShopYearlyAnalytics,
    SupplierDailyAnalytics,
    SupplierMonthlyAnalytics,
    SupplierWeeklyAnalytics,
    SupplierYearlyAnalytics,
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


# ---------------------------------------------------------------------------
# Period-aware trend series (daily / weekly / monthly / yearly)
# Backed directly by the precomputed period tables, not live Order scans.
# ---------------------------------------------------------------------------

PERIOD_FIELDS = {
    "daily": "date",
    "weekly": "week_start",
    "monthly": "month_start",
    "yearly": "year_start",
}

SHOP_PERIOD_MODELS = {
    "daily": ShopDailyAnalytics,
    "weekly": ShopWeeklyAnalytics,
    "monthly": ShopMonthlyAnalytics,
    "yearly": ShopYearlyAnalytics,
}

SUPPLIER_PERIOD_MODELS = {
    "daily": SupplierDailyAnalytics,
    "weekly": SupplierWeeklyAnalytics,
    "monthly": SupplierMonthlyAnalytics,
    "yearly": SupplierYearlyAnalytics,
}

PLATFORM_PERIOD_MODELS = {
    "daily": PlatformDailyAnalytics,
    "weekly": PlatformWeeklyAnalytics,
    "monthly": PlatformMonthlyAnalytics,
    "yearly": PlatformYearlyAnalytics,
}


def get_shop_trend(shop: Shop, period: str = "daily", limit: int = 12) -> list:
    period = period if period in SHOP_PERIOD_MODELS else "daily"
    model = SHOP_PERIOD_MODELS[period]
    field = PERIOD_FIELDS[period]
    rows = list(
        model.objects.filter(shop=shop)
        .order_by(f"-{field}")
        .values(field, "revenue", "orders_count", "units_sold")[:limit]
    )
    rows.reverse()  # chronological order for charting
    return [
        {
            "period": str(row[field]),
            "revenue": str(_decimal(row["revenue"])),
            "orders_count": int(row["orders_count"] or 0),
            "units_sold": int(row["units_sold"] or 0),
        }
        for row in rows
    ]


def get_supplier_trend(user, period: str = "daily", limit: int = 12) -> list:
    period = period if period in SUPPLIER_PERIOD_MODELS else "daily"
    model = SUPPLIER_PERIOD_MODELS[period]
    field = PERIOD_FIELDS[period]
    rows = list(
        model.objects.filter(supplier=user)
        .order_by(f"-{field}")
        .values(field, "revenue", "orders_count", "units_sold")[:limit]
    )
    rows.reverse()
    return [
        {
            "period": str(row[field]),
            "revenue": str(_decimal(row["revenue"])),
            "orders_count": int(row["orders_count"] or 0),
            "units_sold": int(row["units_sold"] or 0),
        }
        for row in rows
    ]


def get_platform_trend(period: str = "daily", limit: int = 12) -> list:
    period = period if period in PLATFORM_PERIOD_MODELS else "daily"
    model = PLATFORM_PERIOD_MODELS[period]
    field = PERIOD_FIELDS[period]
    rows = list(
        model.objects.order_by(f"-{field}")
        .values(field, "total_gmv", "total_platform_fee", "total_orders")[:limit]
    )
    rows.reverse()
    return [
        {
            "period": str(row[field]),
            "total_gmv": str(_decimal(row["total_gmv"])),
            "total_platform_fee": str(_decimal(row["total_platform_fee"])),
            "total_orders": int(row["total_orders"] or 0),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Weekly report — now reads precomputed Daily analytics instead of scanning
# Order directly. Same output shape as before (points/growth_rate), cheaper.
# ---------------------------------------------------------------------------

_DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def get_weekly_report(user) -> dict:
    today = timezone.localdate()
    start = today - timedelta(days=6)
    prev_start = start - timedelta(days=7)
    prev_end = start - timedelta(days=1)

    role = getattr(user, "role", None)
    if role == "SHOP_OWNER":
        shop = getattr(user, "owned_shop", None)
        qs = ShopDailyAnalytics.objects.filter(shop=shop) if shop else ShopDailyAnalytics.objects.none()
        value_field, count_field = "revenue", "orders_count"
    elif role == "SUPPLIER":
        qs = SupplierDailyAnalytics.objects.filter(supplier=user)
        value_field, count_field = "revenue", "orders_count"
    else:
        qs = PlatformDailyAnalytics.objects.all()
        value_field, count_field = "total_gmv", "total_orders"

    this_week_rows = qs.filter(date__gte=start, date__lte=today).values("date").annotate(
        sales=Sum(value_field), orders=Sum(count_field)
    )
    by_date = {row["date"]: row for row in this_week_rows}

    points = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        row = by_date.get(day)
        points.append({
            "day_label": _DAY_LABELS[day.weekday()],
            "sales": float(_decimal(row["sales"])) if row else 0.0,
            "orders": int(row["orders"] or 0) if row else 0,
        })

    this_week_total = sum(p["sales"] for p in points)

    last_week_total = qs.filter(date__gte=prev_start, date__lte=prev_end).aggregate(
        total=Sum(value_field)
    )["total"]
    last_week_total = float(_decimal(last_week_total))

    growth_rate = (
        (this_week_total - last_week_total) / last_week_total
        if last_week_total > 0 else 0.0
    )

    return {
        "points": points,
        "generated_at": timezone.now().isoformat(),
        "growth_rate": round(growth_rate, 3),
    }