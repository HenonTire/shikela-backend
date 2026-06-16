from django.contrib import admin

from .models import CourierProfile, Shipment


@admin.register(CourierProfile)
class CourierProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone", "vehicle_type", "is_available", "updated_at")
    list_filter = ("is_available", "vehicle_type")
    search_fields = ("user__email", "user__phone_number", "phone")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "courier", "status", "assigned_at", "updated_at")
    list_filter = ("status", "courier")
    search_fields = ("order__order_number", "courier__email")
