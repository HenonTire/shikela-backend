from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from account.models import User
from analytics.models import ShopDailyAnalytics
from shop.models import Shop


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "analytics-limit-tests",
        }
    }
)
class AnalyticsLimitValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email="analytics-owner@example.com",
            password="Pass123!",
            role="SHOP_OWNER",
        )
        self.shop = Shop.objects.create(name="Analytics Shop", owner=self.owner)
        self.client.force_authenticate(self.owner)

    def test_invalid_limit_uses_default_instead_of_500(self):
        response = self.client.get("/analytics/shop/dashboard/?limit=not-a-number")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("trend", response.data)

    def test_limit_is_clamped_to_maximum(self):
        today = timezone.localdate()
        rows = [
            ShopDailyAnalytics(
                shop=self.shop,
                date=today - timedelta(days=offset),
                revenue="1.00",
                orders_count=1,
                units_sold=1,
            )
            for offset in range(105)
        ]
        ShopDailyAnalytics.objects.bulk_create(rows)

        response = self.client.get("/analytics/shop/dashboard/?limit=500")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["trend"]), 100)
