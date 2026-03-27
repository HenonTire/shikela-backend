import json
import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.db import transaction
from django.core.mail import send_mail

from .models import DeviceToken, Notification

logger = logging.getLogger(__name__)


class NotificationService:
    _firebase_app_initialized = False
    _INVALID_TOKEN_ERROR_MARKERS = (
        "registration-token-not-registered",
        "invalid-registration-token",
        "unregistered",
    )
    _EMAIL_ALWAYS_NOTIFICATION_TYPES = {
        Notification.Type.NEW_ORDER,
        Notification.Type.PAYMENT_SUCCESS,
        Notification.Type.PAYMENT_CONFIRMED,
        Notification.Type.PRODUCT_SOLD,
        Notification.Type.COMMISSION_CREATED,
        Notification.Type.COMMISSION_APPROVED,
        Notification.Type.ORDER_CANCELLED,
        Notification.Type.REFUND_COMPLETED,
    }

    @classmethod
    def _init_firebase(cls) -> bool:
        if cls._firebase_app_initialized:
            return True
        try:
            import firebase_admin
            from firebase_admin import credentials

            if firebase_admin._apps:
                cls._firebase_app_initialized = True
                return True

            service_account_path = getattr(settings, "FCM_SERVICE_ACCOUNT_FILE", "")
            service_account_json = getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "")
            project_id = getattr(settings, "FCM_PROJECT_ID", "")

            if service_account_json:
                cred = credentials.Certificate(json.loads(service_account_json))
                firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
            elif service_account_path:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
            else:
                logger.info("FCM credentials are not configured. Push sending is disabled.")
                return False

            cls._firebase_app_initialized = True
            return True
        except Exception:
            logger.exception("Failed to initialize Firebase app")
            return False

    @classmethod
    @transaction.atomic
    def notify(
        cls,
        *,
        user,
        notification_type: str,
        title: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        payload = payload or {}
        notification = Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message,
            payload=payload,
        )
        user_id = user.id
        user_email = (getattr(user, "email", "") or "").strip()
        push_payload = dict(payload)
        transaction.on_commit(
            lambda: cls._send_push_safely(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                payload=push_payload,
            )
        )
        if user_email and cls._should_send_email_for_notification(notification_type=notification_type, payload=push_payload):
            transaction.on_commit(
                lambda: cls._send_email_safely(
                    recipient_email=user_email,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    payload=push_payload,
                )
            )
        return notification

    @classmethod
    def _send_push_safely(
        cls,
        *,
        user_id,
        notification_type: str,
        title: str,
        message: str,
        payload: Dict[str, Any],
    ) -> None:
        try:
            cls._send_push_to_user(user_id=user_id, title=title, message=message, payload=payload)
        except Exception:
            logger.exception("Push send failed for user=%s type=%s", user_id, notification_type)

    @classmethod
    def _is_email_enabled(cls) -> bool:
        return bool(getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", False))

    @classmethod
    def _payload_flag(cls, payload: Dict[str, Any], key: str, default: bool = False) -> bool:
        value = payload.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @classmethod
    def _should_send_email_for_notification(cls, *, notification_type: str, payload: Dict[str, Any]) -> bool:
        if not cls._is_email_enabled():
            return False

        if notification_type in cls._EMAIL_ALWAYS_NOTIFICATION_TYPES:
            return True

        if notification_type == Notification.Type.ORDER_DELIVERED:
            return bool(getattr(settings, "EMAIL_SEND_ORDER_DELIVERED", False))

        if notification_type == Notification.Type.ORDER_SHIPPED:
            return bool(getattr(settings, "EMAIL_SEND_ORDER_SHIPPED", False))

        if notification_type == Notification.Type.LOW_STOCK_ALERT:
            urgent_only_enabled = bool(getattr(settings, "EMAIL_SEND_URGENT_LOW_STOCK", True))
            return urgent_only_enabled and cls._payload_flag(payload, "urgent", default=False)

        return bool(getattr(settings, "EMAIL_SEND_OTHER_NOTIFICATION_TYPES", False))

    @classmethod
    def _build_email_body(cls, *, message: str, payload: Dict[str, Any]) -> str:
        lines = [message, "", f"Notification type: {payload.get('type', 'general')}"]

        order_number = payload.get("order_number")
        if order_number:
            lines.append(f"Order number: {order_number}")
        total_amount = payload.get("total_amount")
        if total_amount is not None:
            lines.append(f"Amount: {total_amount} {payload.get('currency', 'ETB')}")
        refund_amount = payload.get("refund_amount")
        if refund_amount is not None:
            lines.append(f"Refund amount: {refund_amount} {payload.get('currency', 'ETB')}")
        reason = payload.get("reason")
        if reason:
            lines.append(f"Reason: {reason}")
        next_steps = payload.get("next_steps")
        if next_steps:
            lines.append(f"Next steps: {next_steps}")

        lines.extend(["", f"Details: {json.dumps(payload, ensure_ascii=True, default=str)}"])
        return "\n".join(lines)

    @classmethod
    def _send_email_to_recipient(
        cls,
        *,
        recipient_email: str,
        title: str,
        message: str,
        payload: Dict[str, Any],
    ) -> None:
        email_body = cls._build_email_body(message=message, payload=payload)
        send_mail(
            subject=title,
            message=email_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", ""),
            recipient_list=[recipient_email],
            fail_silently=False,
        )

    @classmethod
    def _send_email_safely(
        cls,
        *,
        recipient_email: str,
        notification_type: str,
        title: str,
        message: str,
        payload: Dict[str, Any],
    ) -> None:
        if not cls._is_email_enabled():
            return
        if not recipient_email:
            return
        try:
            cls._send_email_to_recipient(
                recipient_email=recipient_email,
                title=title,
                message=message,
                payload=payload,
            )
        except Exception:
            logger.exception("Email send failed for email=%s type=%s", recipient_email, notification_type)

    @classmethod
    def _should_deactivate_token(cls, error_code: str) -> bool:
        normalized_error = (error_code or "").lower()
        return any(marker in normalized_error for marker in cls._INVALID_TOKEN_ERROR_MARKERS)

    @classmethod
    def _send_push_to_user(cls, *, user_id, title: str, message: str, payload: Dict[str, Any]) -> None:
        if not cls._init_firebase():
            return
        tokens = list(DeviceToken.objects.filter(user_id=user_id, is_active=True).values_list("token", flat=True))
        if not tokens:
            return

        from firebase_admin import messaging
        from firebase_admin.exceptions import FirebaseError

        for token in tokens:
            try:
                msg = messaging.Message(
                    notification=messaging.Notification(title=title, body=message),
                    data={k: str(v) for k, v in payload.items()},
                    token=token,
                )
                messaging.send(msg)
            except FirebaseError as exc:
                error_code = getattr(exc, "code", "") or str(exc)
                # Deactivate known invalid token scenarios.
                if cls._should_deactivate_token(error_code):
                    DeviceToken.objects.filter(token=token).update(is_active=False)
                logger.warning("FCM send failed token=%s code=%s", token[:12], error_code)
            except Exception:
                logger.exception("Unexpected FCM error token=%s", token[:12])


class NotificationTemplates:
    @staticmethod
    def payment_success(order):
        items_count = order.items.count() if hasattr(order, "items") else 0
        return (
            "Payment Successful",
            f"Your order #{order.order_number} has been confirmed.",
            {
                "type": "payment_success",
                "entity_id": str(order.id),
                "entity_type": "order",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "total_amount": str(order.total_amount),
                "currency": "ETB",
                "items_count": items_count,
                "paid_at": order.updated_at.isoformat() if getattr(order, "updated_at", None) else "",
            },
        )

    @staticmethod
    def order_shipped(order):
        return (
            "Order Shipped",
            f"Your order #{order.order_number} is on the way.",
            {
                "type": "order_shipped",
                "entity_id": str(order.id),
                "entity_type": "order",
                "order_id": str(order.id),
            },
        )

    @staticmethod
    def order_delivered(order):
        return (
            "Order Delivered",
            f"Your order #{order.order_number} has been delivered.",
            {
                "type": "order_delivered",
                "entity_id": str(order.id),
                "entity_type": "order",
                "order_id": str(order.id),
            },
        )

    @staticmethod
    def order_cancelled(order, reason: str = "Payment failed or was cancelled"):
        return (
            "Order Cancelled",
            f"Your order #{order.order_number} was cancelled.",
            {
                "type": "order_cancelled",
                "entity_id": str(order.id),
                "entity_type": "order",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "total_amount": str(order.total_amount),
                "currency": "ETB",
                "reason": reason,
                "next_steps": "Please retry payment or contact support if you were charged.",
            },
        )

    @staticmethod
    def refund_completed(order, refund):
        return (
            "Refund Completed",
            f"Refund processed for order #{order.order_number}.",
            {
                "type": "refund_completed",
                "entity_id": str(refund.id),
                "entity_type": "refund",
                "refund_id": str(refund.id),
                "order_id": str(order.id),
                "order_number": order.order_number,
                "refund_amount": str(refund.amount),
                "currency": "ETB",
                "reason": refund.reason or "",
                "next_steps": "Funds usually reflect based on your payment provider timeline.",
            },
        )

    @staticmethod
    def low_stock_alert(product, threshold: int, current_stock: int, urgent: bool = False):
        return (
            "Low Stock Alert",
            f"Product {product.name} is low on stock ({current_stock} left).",
            {
                "type": "low_stock_alert",
                "entity_id": str(product.id),
                "entity_type": "product",
                "product_id": str(product.id),
                "threshold": int(threshold),
                "current_stock": int(current_stock),
                "urgent": bool(urgent),
            },
        )

    @staticmethod
    def new_order(order):
        return (
            "New Order",
            f"You received a new order #{order.order_number}.",
            {
                "type": "new_order",
                "entity_id": str(order.id),
                "entity_type": "order",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "total_amount": str(order.total_amount),
                "currency": "ETB",
            },
        )

    @staticmethod
    def payment_confirmed(order):
        return (
            "Payment Confirmed",
            f"Payment received for order #{order.order_number}.",
            {
                "type": "payment_confirmed",
                "entity_id": str(order.id),
                "entity_type": "order",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "total_amount": str(order.total_amount),
                "currency": "ETB",
            },
        )

    @staticmethod
    def product_sold(order, product):
        return (
            "Product Sold",
            f"Your product {product.name} was sold.",
            {
                "type": "product_sold",
                "entity_id": str(order.id),
                "entity_type": "order",
                "order_id": str(order.id),
                "product_id": str(product.id),
            },
        )

    @staticmethod
    def commission_created(order, commission):
        return (
            "Commission Created",
            f"You earned commission for order #{order.order_number}.",
            {
                "type": "commission_created",
                "entity_id": str(commission.id),
                "entity_type": "commission",
                "commission_id": str(commission.id),
                "order_id": str(order.id),
            },
        )

    @staticmethod
    def commission_approved(order, commission):
        return (
            "Commission Approved",
            f"Your commission for order #{order.order_number} is approved.",
            {
                "type": "commission_approved",
                "entity_id": str(commission.id),
                "entity_type": "commission",
                "commission_id": str(commission.id),
                "order_id": str(order.id),
            },
        )
