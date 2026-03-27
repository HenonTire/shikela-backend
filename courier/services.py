from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from account.badge_logic import resolve_badge
from order.models import Order
from notifications.services import NotificationService, NotificationTemplates

from .models import CourierProfile, Shipment

User = get_user_model()


class LogisticsError(Exception):
    pass


def normalize_shipment_status(raw_status: str) -> str:
    status = (raw_status or "").strip().upper()
    mapping = {
        "PENDING": Shipment.Status.PENDING,
        "PICKED_UP": Shipment.Status.PICKED_UP,
        "PICKUP": Shipment.Status.PICKED_UP,
        "IN_TRANSIT": Shipment.Status.IN_TRANSIT,
        "TRANSIT": Shipment.Status.IN_TRANSIT,
        "OUT_FOR_DELIVERY": Shipment.Status.OUT_FOR_DELIVERY,
        "DELIVERED": Shipment.Status.DELIVERED,
        "FAILED": Shipment.Status.FAILED,
        "CANCELLED": Shipment.Status.CANCELLED,
    }
    if status not in mapping:
        raise LogisticsError("Invalid shipment status")
    return mapping[status]


def select_next_available_courier():
    couriers = list(
        User.objects.filter(role="COURIER", is_active=True)
        .filter(
            Q(courier_profile__is_available=True)
            | Q(courier_profile__isnull=True, is_available=True)
        )
        .order_by("created_at", "id")
        .distinct()
    )
    if not couriers:
        return None

    last_assigned_courier_id = (
        Shipment.objects.exclude(courier__isnull=True)
        .order_by("-assigned_at", "-created_at")
        .values_list("courier_id", flat=True)
        .first()
    )
    if not last_assigned_courier_id:
        return couriers[0]

    courier_ids = [courier.id for courier in couriers]
    try:
        current_index = courier_ids.index(last_assigned_courier_id)
    except ValueError:
        return couriers[0]

    next_index = (current_index + 1) % len(couriers)
    return couriers[next_index]


@transaction.atomic
def create_shipment_for_order(order: Order) -> Shipment:
    if hasattr(order, "shipment"):
        return order.shipment

    shipment = Shipment.objects.create(
        order=order,
        status=Shipment.Status.PENDING,
        last_event="shipment_created",
        last_payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
        },
    )

    next_courier = select_next_available_courier()
    if not next_courier:
        return shipment

    try:
        shipment = assign_courier(shipment, next_courier)
    except LogisticsError:
        # Keep shipment created even if assignment fails due to availability races.
        return shipment
    return shipment


@transaction.atomic
def assign_courier(shipment: Shipment, courier_user) -> Shipment:
    if not courier_user:
        raise LogisticsError("Courier user is required")
    if getattr(courier_user, "role", "") != "COURIER":
        raise LogisticsError("Assigned user must have COURIER role")
    if not getattr(courier_user, "is_active", True):
        raise LogisticsError("Assigned courier is inactive")

    profile = CourierProfile.objects.filter(user=courier_user).first()
    if profile and not profile.is_available:
        raise LogisticsError("Assigned courier is not available")

    if shipment.status in {Shipment.Status.DELIVERED, Shipment.Status.FAILED, Shipment.Status.CANCELLED}:
        raise LogisticsError("Cannot assign courier to terminal shipment")

    shipment.courier = courier_user
    shipment.assigned_at = timezone.now()
    shipment.last_event = "courier_assigned"
    shipment.last_payload = {
        "courier_id": str(courier_user.id),
        "courier_email": getattr(courier_user, "email", ""),
    }
    shipment.save(update_fields=["courier", "assigned_at", "last_event", "last_payload", "updated_at"])
    return shipment


@transaction.atomic
def update_shipment_status(
    shipment: Shipment,
    new_status: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Shipment:
    payload = payload or {}
    normalized_status = normalize_shipment_status(new_status)

    shipment.status = normalized_status
    shipment.last_event = "status_update"
    shipment.last_payload = payload
    shipment.save(update_fields=["status", "last_event", "last_payload", "updated_at"])

    order = shipment.order
    if normalized_status == Shipment.Status.PICKED_UP and order.status in {Order.Status.PAID, Order.Status.CONFIRMED}:
        order.status = Order.Status.CONFIRMED
        order.save(update_fields=["status", "updated_at"])
    elif normalized_status in {Shipment.Status.IN_TRANSIT, Shipment.Status.OUT_FOR_DELIVERY}:
        if order.status != Order.Status.DELIVERED:
            current_status = order.status
            target_status = (
                Order.Status.SHIPPED
                if normalized_status == Shipment.Status.OUT_FOR_DELIVERY
                else Order.Status.PROCESSING
            )

            # Ignore stale in-transit updates after the order is already shipped.
            if current_status == Order.Status.SHIPPED and target_status == Order.Status.PROCESSING:
                target_status = current_status

            if current_status != target_status:
                order.status = target_status
                order.save(update_fields=["status", "updated_at"])
                if target_status == Order.Status.SHIPPED:
                    try:
                        title, message, notification_payload = NotificationTemplates.order_shipped(order)
                        NotificationService.notify(
                            user=order.user,
                            notification_type="order_shipped",
                            title=title,
                            message=message,
                            payload=notification_payload,
                        )
                    except Exception:
                        pass
    elif normalized_status == Shipment.Status.DELIVERED:
        if order.status != Order.Status.DELIVERED:
            order.status = Order.Status.DELIVERED
            order.save(update_fields=["status", "updated_at"])
            try:
                title, message, notification_payload = NotificationTemplates.order_delivered(order)
                NotificationService.notify(
                    user=order.user,
                    notification_type="order_delivered",
                    title=title,
                    message=message,
                    payload=notification_payload,
                )
            except Exception:
                pass
        resolve_badge(order.user, persist=True)
        resolve_badge(order.shop.owner, persist=True)
    elif normalized_status in {Shipment.Status.FAILED, Shipment.Status.CANCELLED}:
        if order.status != Order.Status.DELIVERED:
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status", "updated_at"])

    return shipment
