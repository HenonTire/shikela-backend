from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .selectors import (
    get_admin_dashboard,
    get_shop_dashboard,
    get_supplier_dashboard,
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
                }
            )
        return Response(get_shop_dashboard(shop))


class SupplierAnalyticsDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSupplier]

    def get(self, request):
        return Response(get_supplier_dashboard(request.user))


class AdminAnalyticsDashboardView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(get_admin_dashboard())
