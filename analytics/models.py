from decimal import Decimal

from django.conf import settings
from django.db import models

from shop.models import Shop


# ---------------------------------------------------------------------------
# Daily
# ---------------------------------------------------------------------------

class ShopDailyAnalytics(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="daily_analytics")
    date = models.DateField(db_index=True)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    orders_count = models.IntegerField(default=0)
    units_sold = models.IntegerField(default=0)
    refund_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    commission_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    platform_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("shop", "date")
        indexes = [
            models.Index(fields=["shop", "date"]),
        ]

    def __str__(self):
        return f"{self.shop_id} - {self.date}"


class SupplierDailyAnalytics(models.Model):
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="supplier_daily_analytics",
    )
    date = models.DateField(db_index=True)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    units_sold = models.IntegerField(default=0)
    orders_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("supplier", "date")
        indexes = [
            models.Index(fields=["supplier", "date"]),
        ]

    def __str__(self):
        return f"{self.supplier_id} - {self.date}"


class PlatformDailyAnalytics(models.Model):
    date = models.DateField(unique=True, db_index=True)
    total_gmv = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_platform_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_orders = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date}"


# ---------------------------------------------------------------------------
# Shared abstract bases for Weekly/Monthly/Yearly — one copy each
# ---------------------------------------------------------------------------

class BaseShopPeriodAnalytics(models.Model):
    shop = models.ForeignKey(
        Shop, on_delete=models.CASCADE, related_name="%(class)s"
    )
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    orders_count = models.IntegerField(default=0)
    units_sold = models.IntegerField(default=0)
    refund_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    commission_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    platform_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseSupplierPeriodAnalytics(models.Model):
    supplier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)s",
    )
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    units_sold = models.IntegerField(default=0)
    orders_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BasePlatformPeriodAnalytics(models.Model):
    total_gmv = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_platform_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_orders = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------

class ShopWeeklyAnalytics(BaseShopPeriodAnalytics):
    week_start = models.DateField(db_index=True)  # Monday of the ISO week

    class Meta:
        unique_together = ("shop", "week_start")
        indexes = [models.Index(fields=["shop", "week_start"])]

    def __str__(self):
        return f"{self.shop_id} - week of {self.week_start}"


class ShopMonthlyAnalytics(BaseShopPeriodAnalytics):
    month_start = models.DateField(db_index=True)  # 1st of the month

    class Meta:
        unique_together = ("shop", "month_start")
        indexes = [models.Index(fields=["shop", "month_start"])]

    def __str__(self):
        return f"{self.shop_id} - {self.month_start:%Y-%m}"


class ShopYearlyAnalytics(BaseShopPeriodAnalytics):
    year_start = models.DateField(db_index=True)  # Jan 1st of the year

    class Meta:
        unique_together = ("shop", "year_start")
        indexes = [models.Index(fields=["shop", "year_start"])]

    def __str__(self):
        return f"{self.shop_id} - {self.year_start:%Y}"


# ---------------------------------------------------------------------------
# Supplier
# ---------------------------------------------------------------------------

class SupplierWeeklyAnalytics(BaseSupplierPeriodAnalytics):
    week_start = models.DateField(db_index=True)

    class Meta:
        unique_together = ("supplier", "week_start")
        indexes = [models.Index(fields=["supplier", "week_start"])]

    def __str__(self):
        return f"{self.supplier_id} - week of {self.week_start}"


class SupplierMonthlyAnalytics(BaseSupplierPeriodAnalytics):
    month_start = models.DateField(db_index=True)

    class Meta:
        unique_together = ("supplier", "month_start")
        indexes = [models.Index(fields=["supplier", "month_start"])]

    def __str__(self):
        return f"{self.supplier_id} - {self.month_start:%Y-%m}"


class SupplierYearlyAnalytics(BaseSupplierPeriodAnalytics):
    year_start = models.DateField(db_index=True)

    class Meta:
        unique_together = ("supplier", "year_start")
        indexes = [models.Index(fields=["supplier", "year_start"])]

    def __str__(self):
        return f"{self.supplier_id} - {self.year_start:%Y}"


# ---------------------------------------------------------------------------
# Platform
# ---------------------------------------------------------------------------

class PlatformWeeklyAnalytics(BasePlatformPeriodAnalytics):
    week_start = models.DateField(unique=True, db_index=True)

    def __str__(self):
        return f"week of {self.week_start}"


class PlatformMonthlyAnalytics(BasePlatformPeriodAnalytics):
    month_start = models.DateField(unique=True, db_index=True)

    def __str__(self):
        return f"{self.month_start:%Y-%m}"


class PlatformYearlyAnalytics(BasePlatformPeriodAnalytics):
    year_start = models.DateField(unique=True, db_index=True)

    def __str__(self):
        return f"{self.year_start:%Y}"