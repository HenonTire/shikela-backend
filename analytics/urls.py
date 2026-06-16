from django.urls import path

from .api import (
    AdminAnalyticsDashboardView,
    ShopAnalyticsDashboardView,
    SupplierAnalyticsDashboardView,
)


urlpatterns = [
    path("shop/dashboard/", ShopAnalyticsDashboardView.as_view(), name="analytics-shop-dashboard"),
    path("supplier/dashboard/", SupplierAnalyticsDashboardView.as_view(), name="analytics-supplier-dashboard"),
    path("admin/dashboard/", AdminAnalyticsDashboardView.as_view(), name="analytics-admin-dashboard"),
]
