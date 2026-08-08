from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .selectors import (
    get_admin_dashboard,
    get_shop_dashboard,
    get_shop_trend,
    get_supplier_dashboard,
    get_supplier_trend,
    get_platform_trend,
    get_weekly_report,
)


class IsShopOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "SHOP_OWNER"
        )


class IsSupplier(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "SUPPLIER"
        )


class ShopAnalyticsDashboardView(APIView):
    """GET /analytics/shop/dashboard/?period=monthly&limit=12"""
    permission_classes = [permissions.IsAuthenticated, IsShopOwner]

    def get(self, request):
        shop = getattr(request.user, "owned_shop", None)
        if not shop:
            return Response(
                {
                    "total_revenue": "0.00",
                    "this_month_revenue": "0.00",
                    "orders_count": 0,
                    "units_sold": 0,
                    "refund_amount": "0.00",
                    "commission_paid": "0.00",
                    "platform_fee": "0.00",
                    "today_orders": 0,
                    "last_7_days": [],
                    "trend": [],
                }
            )
        data = get_shop_dashboard(shop)
        period = request.query_params.get("period", "daily")
        limit = int(request.query_params.get("limit", 12))
        data["trend"] = get_shop_trend(shop, period=period, limit=limit)
        return Response(data)


class SupplierAnalyticsDashboardView(APIView):
    """GET /analytics/supplier/dashboard/?period=weekly&limit=8"""
    permission_classes = [permissions.IsAuthenticated, IsSupplier]

    def get(self, request):
        data = get_supplier_dashboard(request.user)
        period = request.query_params.get("period", "daily")
        limit = int(request.query_params.get("limit", 12))
        data["trend"] = get_supplier_trend(request.user, period=period, limit=limit)
        return Response(data)


class AdminAnalyticsDashboardView(APIView):
    """GET /analytics/admin/dashboard/?period=yearly&limit=5"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        data = get_admin_dashboard()
        period = request.query_params.get("period", "daily")
        limit = int(request.query_params.get("limit", 12))
        data["trend"] = get_platform_trend(period=period, limit=limit)
        return Response(data)


class WeeklyReportView(APIView):
    """GET /analytics/weekly/
    Now reads from precomputed Daily analytics tables instead of scanning
    Order directly on every request."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(get_weekly_report(request.user))