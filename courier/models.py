import uuid

from django.conf import settings
from django.db import models

from order.models import Order


class CourierProfile(models.Model):
    class VehicleType(models.TextChoices):
        BIKE = "BIKE", "Bike"
        CAR = "CAR", "Car"
        VAN = "VAN", "Van"
        TRUCK = "TRUCK", "Truck"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name="courier_profile",
        on_delete=models.CASCADE,
    )
    is_available = models.BooleanField(default=True)
    phone = models.CharField(max_length=20, blank=True)
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.BIKE,
    )
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_available", "user_id"]

    def __str__(self):
        return f"CourierProfile<{self.user_id}>"


class Shipment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PICKED_UP = "PICKED_UP", "Picked Up"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, related_name="shipment", on_delete=models.CASCADE)
    courier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_shipments",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(null=True, blank=True, db_index=True)

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    last_event = models.CharField(max_length=100, blank=True)
    last_payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["courier", "status"]),
        ]

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"
