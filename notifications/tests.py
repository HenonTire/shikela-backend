from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from account.models import User
from .models import DeviceToken, Notification
from .services import NotificationService


class NotificationsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@shikela.com",
            password="Pass123!",
            role="CUSTOMER",
        )
        self.other = User.objects.create_user(
            email="other@shikela.com",
            password="Pass123!",
            role="CUSTOMER",
        )
        self.client.force_authenticate(self.user)

    def test_device_token_upsert_and_reassign(self):
        resp1 = self.client.post(
            "/api/notifications/device-token/",
            {"token": "token-123", "device_type": "web"},
            format="json",
        )
        self.assertEqual(resp1.status_code, 200, resp1.data)
        token_row = DeviceToken.objects.get(token="token-123")
        self.assertEqual(token_row.user_id, self.user.id)
        self.assertTrue(token_row.is_active)

        self.client.force_authenticate(self.other)
        resp2 = self.client.post(
            "/api/notifications/device-token/",
            {"token": "token-123", "device_type": "android"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200, resp2.data)
        token_row.refresh_from_db()
        self.assertEqual(token_row.user_id, self.other.id)
        self.assertEqual(token_row.device_type, "android")

    def test_device_token_deactivate(self):
        DeviceToken.objects.create(user=self.user, token="token-a", device_type="web", is_active=True)
        resp = self.client.delete(
            "/api/notifications/device-token/",
            {"token": "token-a"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["deactivated"], 1)
        self.assertFalse(DeviceToken.objects.get(token="token-a").is_active)

    def test_notification_read_endpoints(self):
        note1 = Notification.objects.create(
            user=self.user,
            type="payment_success",
            title="Payment Successful",
            message="Order paid",
            payload={"type": "payment_success", "entity_id": "1", "entity_type": "order"},
        )
        note2 = Notification.objects.create(
            user=self.user,
            type="order_shipped",
            title="Order Shipped",
            message="On the way",
            payload={"type": "order_shipped", "entity_id": "1", "entity_type": "order"},
        )

        list_resp = self.client.get("/api/notifications/")
        self.assertEqual(list_resp.status_code, 200, list_resp.data)
        self.assertEqual(list_resp.data["count"], 2)

        read_one = self.client.patch(f"/api/notifications/{note1.id}/read/", {}, format="json")
        self.assertEqual(read_one.status_code, 200, read_one.data)
        note1.refresh_from_db()
        self.assertTrue(note1.is_read)

        read_all = self.client.post("/api/notifications/mark-all-read/", {}, format="json")
        self.assertEqual(read_all.status_code, 200, read_all.data)
        note2.refresh_from_db()
        self.assertTrue(note2.is_read)


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="service-user@shikela.com",
            password="Pass123!",
            role="CUSTOMER",
        )

    @patch("notifications.services.NotificationService._send_push_to_user")
    def test_notify_schedules_push_on_commit(self, mock_send_push):
        payload = {"type": "payment_success", "order_id": "1"}
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            notification = NotificationService.notify(
                user=self.user,
                notification_type="payment_success",
                title="Payment Successful",
                message="Order paid",
                payload=payload,
            )

        self.assertTrue(Notification.objects.filter(id=notification.id).exists())
        self.assertEqual(len(callbacks), 1)
        mock_send_push.assert_not_called()

        callbacks[0]()
        mock_send_push.assert_called_once_with(
            user_id=self.user.id,
            title="Payment Successful",
            message="Order paid",
            payload=payload,
        )

    def test_should_deactivate_token_only_for_invalid_token_errors(self):
        self.assertTrue(
            NotificationService._should_deactivate_token("messaging/registration-token-not-registered")
        )
        self.assertTrue(NotificationService._should_deactivate_token("UNREGISTERED"))
        self.assertFalse(NotificationService._should_deactivate_token("invalid-argument"))

    @override_settings(EMAIL_NOTIFICATIONS_ENABLED=True)
    def test_notify_schedules_email_on_commit_when_enabled(self):
        payload = {"type": "payment_success", "order_id": "1"}
        with patch("notifications.services.NotificationService._send_push_to_user") as mock_send_push:
            with patch("notifications.services.NotificationService._send_email_to_recipient") as mock_send_email:
                with self.captureOnCommitCallbacks(execute=False) as callbacks:
                    NotificationService.notify(
                        user=self.user,
                        notification_type="payment_success",
                        title="Payment Successful",
                        message="Order paid",
                        payload=payload,
                    )

                self.assertEqual(len(callbacks), 2)
                for callback in callbacks:
                    callback()

                mock_send_push.assert_called_once()
                mock_send_email.assert_called_once_with(
                    recipient_email=self.user.email,
                    title="Payment Successful",
                    message="Order paid",
                    payload=payload,
                )

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        EMAIL_SEND_ORDER_DELIVERED=False,
    )
    def test_order_delivered_email_is_optional_and_disabled_by_default(self):
        payload = {"type": "order_delivered", "order_id": "1"}
        with patch("notifications.services.NotificationService._send_push_to_user") as mock_send_push:
            with patch("notifications.services.NotificationService._send_email_to_recipient") as mock_send_email:
                with self.captureOnCommitCallbacks(execute=False) as callbacks:
                    NotificationService.notify(
                        user=self.user,
                        notification_type="order_delivered",
                        title="Order Delivered",
                        message="Delivered",
                        payload=payload,
                    )

                self.assertEqual(len(callbacks), 1)
                callbacks[0]()
                mock_send_push.assert_called_once()
                mock_send_email.assert_not_called()

    @override_settings(
        EMAIL_NOTIFICATIONS_ENABLED=True,
        EMAIL_SEND_URGENT_LOW_STOCK=True,
    )
    def test_low_stock_email_sent_only_when_urgent(self):
        with patch("notifications.services.NotificationService._send_push_to_user"):
            with patch("notifications.services.NotificationService._send_email_to_recipient") as mock_send_email:
                with self.captureOnCommitCallbacks(execute=False) as callbacks:
                    NotificationService.notify(
                        user=self.user,
                        notification_type="low_stock_alert",
                        title="Low Stock Alert",
                        message="Urgent restock needed",
                        payload={"type": "low_stock_alert", "urgent": True, "product_id": "p1"},
                    )
                self.assertEqual(len(callbacks), 2)
                for callback in callbacks:
                    callback()
                mock_send_email.assert_called_once()

                mock_send_email.reset_mock()
                with self.captureOnCommitCallbacks(execute=False) as callbacks:
                    NotificationService.notify(
                        user=self.user,
                        notification_type="low_stock_alert",
                        title="Low Stock Alert",
                        message="Stock below threshold",
                        payload={"type": "low_stock_alert", "urgent": False, "product_id": "p2"},
                    )
                self.assertEqual(len(callbacks), 1)
                callbacks[0]()
                mock_send_email.assert_not_called()

