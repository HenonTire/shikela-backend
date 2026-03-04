from django.urls import path

from .api import (
    AdminAnalyticsDashboardView,
    MarketerAnalyticsDashboardView,
    ShopAnalyticsDashboardView,
    SupplierAnalyticsDashboardView,
)


urlpatterns = [
    path("shop/dashboard/", ShopAnalyticsDashboardView.as_view(), name="analytics-shop-dashboard"),
    path("supplier/dashboard/", SupplierAnalyticsDashboardView.as_view(), name="analytics-supplier-dashboard"),
    path("marketer/dashboard/", MarketerAnalyticsDashboardView.as_view(), name="analytics-marketer-dashboard"),
    path("admin/dashboard/", AdminAnalyticsDashboardView.as_view(), name="analytics-admin-dashboard"),
]
