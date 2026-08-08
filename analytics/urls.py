from django.urls import path

from .api import (
    AdminAnalyticsDashboardView,
    ShopAnalyticsDashboardView,
    SupplierAnalyticsDashboardView,
    WeeklyReportView
)


urlpatterns = [
    path("shop/dashboard/", ShopAnalyticsDashboardView.as_view(), name="analytics-shop-dashboard"),
    path("supplier/dashboard/", SupplierAnalyticsDashboardView.as_view(), name="analytics-supplier-dashboard"),
    path("admin/dashboard/", AdminAnalyticsDashboardView.as_view(), name="analytics-admin-dashboard"),
    path("weekly/", WeeklyReportView.as_view(), name="weekly report")
]
