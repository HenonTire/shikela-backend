from decimal import Decimal

from django.conf import settings
from django.db import models

from shop.models import Shop


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
