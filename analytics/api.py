from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from order.models import Order 
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
 # adjust import to your actual Order model


class WeeklyReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        start_date = today - timedelta(days=6)  # last 7 days including today

        # Filter orders relevant to this user (adjust based on role)
        orders_qs = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=today,
        )

        if user.role == "SHOP_OWNER":
            orders_qs = orders_qs.filter(shop__owner=user)
        elif user.role == "SUPPLIER":
            orders_qs = orders_qs.filter(items__product__supplier=user).distinct()

        # Aggregate by day
        daily_data = (
            orders_qs
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                sales=Sum("total_amount"),  # adjust field name to your Order model
                orders=Count("id"),
            )
            .order_by("day")
        )

        # Build a dict for quick lookup
        data_by_day = {entry["day"]: entry for entry in daily_data}

        day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        points = []

        for i in range(7):
            current_date = start_date + timedelta(days=i)
            entry = data_by_day.get(current_date)
            points.append({
                "day_label": day_labels[current_date.weekday()],
                "sales": float(entry["sales"]) if entry and entry["sales"] else 0.0,
                "orders": entry["orders"] if entry else 0,
            })

        # Calculate growth rate (compare this week's total vs last week's total)
        this_week_total = sum(p["sales"] for p in points)

        last_week_start = start_date - timedelta(days=7)
        last_week_end = start_date - timedelta(days=1)
        last_week_orders = orders_qs.model.objects.filter(
            created_at__date__gte=last_week_start,
            created_at__date__lte=last_week_end,
        )
        if user.role == "SHOP_OWNER":
            last_week_orders = last_week_orders.filter(shop__owner=user)
        elif user.role == "SUPPLIER":
            last_week_orders = last_week_orders.filter(items__product__supplier=user).distinct()

        last_week_total = last_week_orders.aggregate(total=Sum("total_amount"))["total"] or 0
        last_week_total = float(last_week_total)

        growth_rate = (
            (this_week_total - last_week_total) / last_week_total
            if last_week_total > 0 else 0.0
        )

        return Response({
            "points": points,
            "generated_at": timezone.now().isoformat(),
            "growth_rate": round(growth_rate, 3),
        })