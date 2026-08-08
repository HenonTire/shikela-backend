import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import Mock, patch

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from account.models import User
from catalog.models import Category, Product, ProductVariant
from order.models import Order, OrderItem
from payment.models import Earning, Payment, Refund, WebhookLog
from payment.services.service import PaymentService, PaymentServiceError
from payment.services.santimpay_sdk import SantimpaySDK
from payment.tasks import process_santimpay_webhook
from payment.webhooks import build_santimpay_signature
from shop.models import Shop


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "payout-request-tests",
        }
    },
    SANTIMPAY_PRIVATE_KEY="dummy-private-key",
    SANTIMPAY_MERCHANT_ID="TEST-MERCHANT-ID",
    SANTIMPAY_TEST_BED=True,
    SANTIMPAY_NOTIFY_URL="http://localhost:8000/payment/webhook/santimpay/",
)
class PayoutRequestTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.shop_owner = User.objects.create_user(
            email="owner@shop.com",
            password="Pass123!",
            role="SHOP_OWNER",
            phone_number="0911000000",
        )
        self.supplier = User.objects.create_user(
            email="supplier@shop.com",
            password="Pass123!",
            role="SUPPLIER",
            phone_number="0911223344",
        )
        self.customer = User.objects.create_user(
            email="customer@shop.com",
            password="Pass123!",
            role="CUSTOMER",
        )
        self.shop = Shop.objects.create(name="Test Shop", owner=self.shop_owner)
        self.product = Product.objects.create(
            name="Supplier Product X",
            shop=self.shop,
            supplier=self.supplier,
            price=Decimal("120.00"),
            supplier_price=Decimal("80.00"),
            minimum_wholesale_quantity=1,
        )
        self.order = Order.objects.create(
            order_number="ORD-TEST-PAYOUT-001",
            user=self.customer,
            shop=self.shop,
            status=Order.Status.DELIVERED,
            subtotal=Decimal("240.00"),
            total_amount=Decimal("240.00"),
            payment_method="santimpay",
            delivery_address="addr",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=None,
            product_name=self.product.name,
            sku=self.product.sku,
            price=Decimal("120.00"),
            quantity=2,
            total=Decimal("240.00"),
        )
        self.payment = Payment.objects.create(
            order=self.order,
            user=self.customer,
            amount=Decimal("240.00"),
            status=Payment.Status.COMPLETED,
            provider="SANTIMPAY",
            provider_reference="TXN-TEST-1",
            metadata={"merchant_id": "TEST-MERCHANT-ID"},
        )
        PaymentService(merchant_id="TEST-MERCHANT-ID").record_settlement_earnings(self.payment)

    @patch("payment.services.service.PaymentService._pay_user")
    def test_payout_executes_only_on_user_request(self, mock_pay_user):
        mock_pay_user.return_value = {
            "tx_id": "PYO-TEST-1",
            "method": "TELEBIRR",
            "account": "0911223344",
            "provider_response": {"id": "PAYOUT-REF-1"},
        }
        self.client.force_authenticate(self.supplier)

        response = self.client.post(
            "/payment/payouts/request/",
            {"confirm": True},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "COMPLETED")
        self.assertEqual(response.data["amount"], "160.00")
        self.assertEqual(response.data["provider_reference"], "PAYOUT-REF-1")
        self.assertEqual(mock_pay_user.call_count, 1)
        self.assertEqual(Earning.objects.filter(user=self.supplier, status=Earning.Status.AVAILABLE).count(), 0)

    @patch("payment.services.service.PaymentService._pay_user")
    def test_non_allocated_user_cannot_request_payout(self, mock_pay_user):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            "/payment/payouts/request/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("No available earnings", response.data["detail"])
        self.assertEqual(mock_pay_user.call_count, 0)

    @patch("payment.services.service.PaymentService._pay_user")
    def test_user_can_list_payout_history(self, mock_pay_user):
        mock_pay_user.return_value = {
            "tx_id": "PYO-TEST-2",
            "method": "TELEBIRR",
            "account": "0911223344",
            "provider_response": {"id": "PAYOUT-REF-2"},
        }
        self.client.force_authenticate(self.supplier)
        create_resp = self.client.post(
            "/payment/payouts/request/",
            {"confirm": True},
            format="json",
        )
        self.assertEqual(create_resp.status_code, 201, create_resp.data)

        history_resp = self.client.get("/payment/payouts/history/")
        self.assertEqual(history_resp.status_code, 200, history_resp.data)
        self.assertEqual(history_resp.data["count"], 1)
        self.assertIn("next", history_resp.data)
        self.assertIn("previous", history_resp.data)
        self.assertEqual(len(history_resp.data["results"]), 1)
        self.assertEqual(len(history_resp.data["history"]), 1)
        self.assertEqual(history_resp.data["available_earnings"], "0.00")

    def test_settlement_is_blocked_until_order_delivered(self):
        self.order.status = Order.Status.PAID
        self.order.save(update_fields=["status", "updated_at"])
        self.payment.metadata = {"merchant_id": "TEST-MERCHANT-ID"}
        self.payment.save(update_fields=["metadata", "updated_at"])

        with self.assertRaises(PaymentServiceError):
            PaymentService(merchant_id="TEST-MERCHANT-ID").record_settlement_earnings(self.payment)


@override_settings(
    SANTIMPAY_PRIVATE_KEY="dummy-private-key",
    SANTIMPAY_MERCHANT_ID="TEST-MERCHANT-ID",
    SANTIMPAY_WEBHOOK_SECRET="test-webhook-secret",
    SANTIMPAY_TEST_BED=True,
    SANTIMPAY_NOTIFY_URL="http://localhost:8000/payment/webhook/santimpay/",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class PaymentLifecycleLogicTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.shop_owner = User.objects.create_user(
            email="owner_logic@shop.com",
            password="Pass123!",
            role="SHOP_OWNER",
            phone_number="0911001111",
        )
        self.customer = User.objects.create_user(
            email="customer_logic@shop.com",
            password="Pass123!",
            role="CUSTOMER",
        )
        self.shop = Shop.objects.create(name="Logic Shop", owner=self.shop_owner)
        self.category = Category.objects.create(name="Logic Category")
        self.product = Product.objects.create(
            name="Logic Product",
            shop=self.shop,
            category=self.category,
            price=Decimal("100.00"),
            supplier_price=Decimal("0.00"),
            minimum_wholesale_quantity=1,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            variant_name="Default",
            price=Decimal("100.00"),
            stock=5,
        )
        self.order = Order.objects.create(
            order_number="ORD-TEST-LOGIC-001",
            user=self.customer,
            shop=self.shop,
            status=Order.Status.PENDING,
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            payment_method="santimpay",
            payment_reference="TXN-LOGIC-001",
            delivery_address="addr",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            variant=self.variant,
            product_name=self.product.name,
            sku=self.product.sku,
            price=Decimal("100.00"),
            quantity=2,
            total=Decimal("200.00"),
        )
        self.payment = Payment.objects.create(
            order=self.order,
            user=self.customer,
            amount=Decimal("100.00"),
            status=Payment.Status.PENDING,
            provider="SANTIMPAY",
            provider_reference="TXN-LOGIC-001",
            metadata={"merchant_id": "TEST-MERCHANT-ID"},
        )
        self.service = PaymentService(merchant_id="TEST-MERCHANT-ID")

    def post_signed_webhook(self, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = build_santimpay_signature(body, "test-webhook-secret")
        return self.client.post(
            "/payment/webhook/santimpay/",
            data=body,
            content_type="application/json",
            HTTP_X_SANTIMPAY_SIGNATURE=f"sha256={signature}",
        )

    def test_transition_matrix_allows_direct_pending_completion_and_failure(self):
        self.assertTrue(self.service._can_transition("PENDING", "COMPLETED"))
        self.assertTrue(self.service._can_transition("PENDING", "FAILED"))
        self.assertTrue(self.service._can_transition("PENDING", "PROCESSING"))
        self.assertFalse(self.service._can_transition("FAILED", "COMPLETED"))
        self.assertFalse(self.service._can_transition("REFUNDED", "COMPLETED"))

    def test_normalize_santimpay_tx_id_keeps_digits_only(self):
        tx_id = self.service.normalize_santimpay_tx_id("ORD-abc-1234-XYZ-5678")
        self.assertEqual(tx_id, "12345678")

    def test_normalize_santimpay_tx_id_generates_fallback_when_missing_digits(self):
        tx_id = self.service.normalize_santimpay_tx_id("ORD-ONLY-LETTERS")
        self.assertTrue(tx_id.isdigit())
        self.assertGreaterEqual(len(tx_id), 8)
        self.assertLessEqual(len(tx_id), 20)

    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_sync_order_status_moves_pending_to_completed_on_success_gateway_status(self, mock_status):
        mock_status.return_value = {"status": "SUCCESS"}

        self.service.sync_order_status(self.order, tx_id=self.payment.provider_reference)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)
        self.assertEqual(self.order.status, Order.Status.PAID)

    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_sync_order_status_moves_pending_to_failed_on_failure_gateway_status(self, mock_status):
        self.variant.stock = 3
        self.variant.save(update_fields=["stock", "updated_at"])
        mock_status.return_value = {"status": "FAILED"}

        self.service.sync_order_status(self.order, tx_id=self.payment.provider_reference)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.variant.stock, 5)

    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_sync_order_status_keeps_terminal_payment_state_unchanged(self, mock_status):
        self.payment.status = Payment.Status.FAILED
        self.payment.save(update_fields=["status", "updated_at"])
        mock_status.return_value = {"status": "SUCCESS"}

        self.service.sync_order_status(self.order, tx_id=self.payment.provider_reference)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.status, Order.Status.PAID)

    @patch("payment.services.service.NotificationService.notify")
    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_webhook_sends_order_cancelled_notification_on_failed_sync(self, mock_status, mock_notify):
        mock_status.return_value = {"status": "FAILED"}

        response = self.post_signed_webhook({"id": self.payment.provider_reference})

        self.assertEqual(response.status_code, 200, response.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertTrue(
            any(call.kwargs.get("notification_type") == "order_cancelled" for call in mock_notify.call_args_list)
        )

    @patch("payment.services.service.NotificationService.notify")
    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_webhook_sends_refund_completed_notification(self, mock_status, mock_notify):
        refund = Refund.objects.create(
            payment=self.payment,
            amount=self.payment.amount,
            reason="Customer requested refund",
            status=Refund.Status.PROCESSING,
            provider_reference="TXN-REFUND-LOGIC-001",
            requested_by=self.customer,
        )
        mock_status.return_value = {"status": "SUCCESS"}

        response = self.post_signed_webhook({"id": refund.provider_reference})

        self.assertEqual(response.status_code, 200, response.content)
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.Status.COMPLETED)
        self.assertTrue(
            any(call.kwargs.get("notification_type") == "refund_completed" for call in mock_notify.call_args_list)
        )

    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_valid_webhook_queues_and_processes_payment(self, mock_status):
        mock_status.return_value = {"status": "SUCCESS"}

        response = self.post_signed_webhook({"event_id": "evt-valid-1", "id": self.payment.provider_reference})

        self.assertEqual(response.status_code, 200, response.content)
        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        webhook_log = WebhookLog.objects.get(event_id="evt-valid-1")
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)
        self.assertTrue(webhook_log.processed)

    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_duplicate_webhook_is_ignored_without_second_processing(self, mock_status):
        mock_status.return_value = {"status": "SUCCESS"}
        payload = {"event_id": "evt-duplicate-1", "id": self.payment.provider_reference}

        first_response = self.post_signed_webhook(payload)
        second_response = self.post_signed_webhook(payload)

        self.assertEqual(first_response.status_code, 200, first_response.content)
        self.assertEqual(second_response.status_code, 200, second_response.content)
        self.assertEqual(WebhookLog.objects.filter(event_id="evt-duplicate-1").count(), 1)
        self.assertEqual(mock_status.call_count, 1)

    @patch("payment.tasks.process_santimpay_webhook.delay")
    def test_webhook_returns_after_queueing_task(self, mock_delay):
        response = self.post_signed_webhook({"event_id": "evt-queued-1", "id": self.payment.provider_reference})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(mock_delay.call_count, 1)
        self.assertEqual(WebhookLog.objects.get(event_id="evt-queued-1").processed, False)

    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_invalid_signature_rejects_without_processing(self, mock_status):
        body = json.dumps({"event_id": "evt-invalid-sig", "id": self.payment.provider_reference}).encode("utf-8")
        response = self.client.post(
            "/payment/webhook/santimpay/",
            data=body,
            content_type="application/json",
            HTTP_X_SANTIMPAY_SIGNATURE="sha256=bad",
        )

        self.assertEqual(response.status_code, 403, response.content)
        self.assertFalse(WebhookLog.objects.filter(event_id="evt-invalid-sig").exists())
        self.assertEqual(mock_status.call_count, 0)

    def test_malformed_payload_is_rejected_gracefully_after_signature_verification(self):
        body = b"{not-json"
        signature = build_santimpay_signature(body, "test-webhook-secret")

        response = self.client.post(
            "/payment/webhook/santimpay/",
            data=body,
            content_type="application/json",
            HTTP_X_SANTIMPAY_SIGNATURE=f"sha256={signature}",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertTrue(WebhookLog.objects.filter(event_type="MALFORMED_PAYLOAD").exists())

    @patch("payment.services.service.NotificationService.notify")
    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_already_paid_order_does_not_trigger_duplicate_side_effects(self, mock_status, mock_notify):
        self.order.status = Order.Status.PAID
        self.order.save(update_fields=["status", "updated_at"])
        mock_status.return_value = {"status": "SUCCESS"}

        response = self.post_signed_webhook({"event_id": "evt-paid-1", "id": self.payment.provider_reference})

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(mock_status.call_count, 0)
        self.assertEqual(mock_notify.call_count, 0)

    @patch("payment.services.service.PaymentService.get_transaction_status")
    def test_celery_task_execution_processes_existing_webhook_log(self, mock_status):
        mock_status.return_value = {"status": "SUCCESS"}
        webhook_log = WebhookLog.objects.create(
            provider="SANTIMPAY",
            event_type="RECEIVED",
            event_id="evt-task-1",
            reference=self.payment.provider_reference,
            payload={"id": self.payment.provider_reference},
        )

        process_santimpay_webhook(webhook_log.id)

        self.order.refresh_from_db()
        webhook_log.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertTrue(webhook_log.processed)

    def test_prepare_and_settle_split_payout_blocked_before_delivery(self):
        self.payment.status = Payment.Status.COMPLETED
        self.payment.save(update_fields=["status", "updated_at"])
        self.order.status = Order.Status.PAID
        self.order.save(update_fields=["status", "updated_at"])

        with self.assertRaises(PaymentServiceError):
            self.service.prepare_split_settlement(self.payment)
        with self.assertRaises(PaymentServiceError):
            self.service.settle_split_payout(self.payment)

    def test_delivery_signal_records_earnings_only_after_status_turns_delivered(self):
        self.payment.status = Payment.Status.COMPLETED
        self.payment.save(update_fields=["status", "updated_at"])

        self.order.status = Order.Status.PROCESSING
        self.order.save(update_fields=["status", "updated_at"])
        self.assertEqual(Earning.objects.filter(payment=self.payment).count(), 0)

        self.order.status = Order.Status.DELIVERED
        self.order.save(update_fields=["status", "updated_at"])
        self.assertGreater(Earning.objects.filter(payment=self.payment).count(), 0)


@override_settings(
    SANTIMPAY_PRIVATE_KEY="dummy-private-key",
    SANTIMPAY_MERCHANT_ID="TEST-MERCHANT-ID",
    SANTIMPAY_WEBHOOK_SECRET="test-webhook-secret",
    SANTIMPAY_TEST_BED=True,
    SANTIMPAY_NOTIFY_URL="http://localhost:8000/payment/webhook/santimpay/",
)
class SantimPayWebhookConcurrencyTests(TransactionTestCase):
    def signed_body_and_header(self, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = build_santimpay_signature(body, "test-webhook-secret")
        return body, f"sha256={signature}"

    @patch("payment.tasks.process_santimpay_webhook.delay")
    def test_concurrent_duplicate_webhook_requests_create_single_log(self, mock_delay):
        body, signature = self.signed_body_and_header(
            {"event_id": "evt-concurrent-1", "id": "TXN-CONCURRENT-1"}
        )

        def post_webhook():
            close_old_connections()
            client = APIClient()
            try:
                return client.post(
                    "/payment/webhook/santimpay/",
                    data=body,
                    content_type="application/json",
                    HTTP_X_SANTIMPAY_SIGNATURE=signature,
                ).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(lambda _: post_webhook(), range(2)))

        self.assertEqual(statuses, [200, 200])
        self.assertEqual(WebhookLog.objects.filter(event_id="evt-concurrent-1").count(), 1)
        self.assertEqual(mock_delay.call_count, 1)


class SantimPaySdkSignerTests(TestCase):
    @patch("payment.services.santimpay_sdk.requests.post")
    def test_direct_payment_token_uses_remote_signer_when_configured(self, mock_post):
        sign_response = Mock()
        sign_response.ok = True
        sign_response.json.return_value = {"signedToken": "REMOTE-SIGNED-TOKEN"}
        mock_post.return_value = sign_response

        sdk = SantimpaySDK(
            merchant_id="MERCHANT-1",
            private_key="dummy-private-key",
            test_bed=True,
            sign_token_url="https://signer.example.com/sign",
        )

        token = sdk.generate_signed_token_for_direct_payment(
            amount=1.0,
            payment_reason="Payment for a coffee",
            payment_method="Telebirr",
            phone_number="+251938646985",
        )

        self.assertEqual(token, "REMOTE-SIGNED-TOKEN")
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["paymentReason"],
            "Payment for a coffee",
        )
