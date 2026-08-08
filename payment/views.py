import logging
from django.conf import settings
from django.db.models import Q
from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser

from analytics.services import AnalyticsService
from core.pagination import paginated_response

from .serializers import (
    EarningSerializer,
    PayoutCreateSerializer,
    PayoutRequestSerializer,
    RefundSerializer,
    RefundRequestSerializer,
)
from django.shortcuts import get_object_or_404

from order.models import Order
from payment.models import Earning, Payment, PayoutRequest, Refund, WebhookLog
from payment.services.service import (
    PaymentConfigurationError,
    PaymentGatewayError,
    PaymentService,
    PaymentServiceError,
)
from payment.webhooks import (
    WebhookConfigurationError,
    WebhookPayloadError,
    WebhookSignatureError,
    extract_santimpay_event_id,
    extract_santimpay_reference,
    get_santimpay_webhook_secret,
    get_webhook_signature,
    parse_webhook_payload,
    verify_santimpay_signature,
)


def _get_platform_merchant_id() -> str:
    merchant_id = getattr(settings, "SANTIMPAY_MERCHANT_ID", "") or getattr(settings, "PLATFORM_MERCHANT_ID", "")
    if not merchant_id:
        raise PaymentServiceError("SANTIMPAY_MERCHANT_ID is required for payment")
    return merchant_id


class DirectPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        payment_method = request.data.get("payment_method")
        phone_number = request.data.get("phone_number")
        notify_url = request.data.get("notify_url")

        if not order_id or not payment_method or not phone_number:
            return Response(
                {
                    "detail": "order_id, payment_method and phone_number are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = Order.objects.filter(id=order_id, user=request.user).select_related("shop__owner").first()
        if not order:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status != Order.Status.PENDING:
            return Response(
                {"detail": f"Order cannot be paid in status '{order.status}'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            merchant_id = _get_platform_merchant_id()
            service = PaymentService(merchant_id=merchant_id)
            tx_id = service.normalize_santimpay_tx_id(order.payment_reference or str(order.id))
            provider_response = service.direct_payment(
                amount=order.total_amount,
                payment_reason=f"Order payment {order.order_number}",
                notify_url=notify_url,
                phone_number=phone_number,
                payment_method=payment_method,
                tx_id=tx_id,
            )
        except PaymentConfigurationError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except PaymentServiceError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except PaymentGatewayError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            logger.exception("Unexpected direct payment error for order=%s", order.id)
            return Response(
                {"detail": "Unexpected payment error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        payment, _ = Payment.objects.update_or_create(
            order=order,
            user=request.user,
            provider="SANTIMPAY",
            defaults={
                "amount": order.total_amount,
                "status": Payment.Status.PROCESSING,
                "provider_reference": tx_id,
                "metadata": {
                    "merchant_id": merchant_id,
                    "provider_response": provider_response,
                },
            },
        )

        if order.payment_reference != tx_id:
            order.payment_reference = tx_id
            order.save(update_fields=["payment_reference", "updated_at"])

        return Response(
            {
                "message": "Direct payment initiated",
                "order_id": str(order.id),
                "transaction_id": tx_id,
                "payment_id": str(payment.id),
                "provider_response": provider_response,
            },
            status=status.HTTP_200_OK,
        )


class RefundListCreateView(APIView):
    """List refunds for the requesting user (staff see all) and allow creating refund requests."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            qs = Refund.objects.select_related("payment", "requested_by").all().order_by("-created_at")
        else:
            qs = Refund.objects.select_related("payment").filter(requested_by=request.user).order_by("-created_at")
        return paginated_response(self, request, qs, RefundSerializer)

    def post(self, request):
        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.validated_data["payment"]
        amount = serializer.validated_data["amount"]
        reason = serializer.validated_data.get("reason", "")

        # Only allow requesting refunds for own payments unless staff
        if not request.user.is_staff and payment.user != request.user:
            return Response({"detail": "Cannot request refund for this payment"}, status=status.HTTP_403_FORBIDDEN)

        refund = Refund.objects.create(
            payment=payment,
            amount=amount,
            reason=reason,
            status=Refund.Status.REQUESTED,
            requested_by=request.user,
        )
        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)


class RefundApproveView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        refund = get_object_or_404(Refund, pk=pk)
        if refund.status != Refund.Status.REQUESTED:
            return Response({"detail": "Only requested refunds can be approved"}, status=status.HTTP_400_BAD_REQUEST)
        refund.status = Refund.Status.APPROVED
        refund.save(update_fields=["status", "updated_at"])
        try:
            AnalyticsService.handle_refund_approved(refund)
        except Exception:
            logger.exception("Failed to update analytics for refund=%s", refund.id)
        return Response(RefundSerializer(refund).data)


class RefundExecuteView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        refund = get_object_or_404(
            Refund.objects.select_related("payment", "payment__order__shop__owner", "requested_by"),
            pk=pk,
        )
        if refund.status != Refund.Status.APPROVED:
            return Response({"detail": "Only approved refunds can be executed"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            merchant_id = _get_platform_merchant_id()
            service = PaymentService(merchant_id=merchant_id)
            target_user = refund.requested_by or refund.payment.user
            payout_info = service._resolve_payout_target(target_user)
            phone = payout_info.get("account")
            method = payout_info.get("method")
            tx_id = f"REF-{refund.payment.id}-{refund.id.hex[:8].upper()}"
            response = service.payout_to_customer(
                amount=refund.amount,
                payment_reason=refund.reason or f"Refund for order {refund.payment.order.order_number}",
                phone_number=phone,
                payment_method=method,
                tx_id=tx_id,
            )
            refund.provider_reference = response.get("id")
            refund.status = Refund.Status.PROCESSING
            metadata = dict(refund.metadata or {})
            metadata.setdefault("provider_response", {})
            metadata["provider_response"].update(response)
            refund.metadata = metadata
            refund.save(update_fields=["provider_reference", "status", "metadata", "updated_at"])
            return Response(RefundSerializer(refund).data)
        except PaymentServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PayoutRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PayoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            merchant_id = _get_platform_merchant_id()
            service = PaymentService(merchant_id=merchant_id)
            payout_request = service.request_total_user_payout(
                user=request.user,
                amount=serializer.validated_data.get("amount"),
                idempotency_key=serializer.validated_data.get("idempotency_key")
                or request.headers.get("Idempotency-Key"),
            )
        except PaymentServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except PaymentGatewayError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response_status = (
            status.HTTP_400_BAD_REQUEST
            if payout_request.status == PayoutRequest.Status.FAILED
            else status.HTTP_201_CREATED
        )
        return Response(PayoutRequestSerializer(payout_request).data, status=response_status)


class EarningsDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(PaymentService.get_earnings_dashboard(request.user))


class EarningsHistoryView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EarningSerializer

    def get_queryset(self):
        queryset = (
            Earning.objects.select_related("payment", "order", "payout_request", "user")
            .filter(user=self.request.user)
            .order_by("-created_at")
        )
        status_filter = (self.request.query_params.get("status") or "").strip().upper()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        role = (self.request.query_params.get("role") or "").strip()
        if role:
            queryset = queryset.filter(role__icontains=role)
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(order__order_number__icontains=search)
                | Q(payment__provider_reference__icontains=search)
                | Q(role__icontains=search)
            )
        return queryset


class PayoutHistoryView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PayoutRequestSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = PayoutRequest.objects.select_related("payment", "order", "user").all().order_by("-created_at")
        else:
            queryset = PayoutRequest.objects.select_related("payment", "order").filter(user=self.request.user).order_by("-created_at")
        status_filter = (self.request.query_params.get("status") or "").strip().upper()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(provider_reference__icontains=search)
                | Q(payout_method__icontains=search)
                | Q(payout_account__icontains=search)
                | Q(user__email__icontains=search)
            )
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        payload = dict(response.data)
        summary = PaymentService.get_earnings_dashboard(request.user)
        payload.update(
            {
                **summary,
                "total_earnings": summary["total"],
                "available_earnings": summary["available"],
                "pending_payouts": summary["pending"],
                "withdrawn_earnings": summary["withdrawn"],
                "summary": summary,
                "history": payload.get("results", []),
            }
        )
        return Response(payload, status=response.status_code)




logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name="dispatch")
class SantimPayWebhookView(APIView):
    """
    Endpoint to receive SantimPay webhook notifications.
    Handles both Payments and Refunds.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "santimpay_webhook"

    def get(self, request: HttpRequest):
        # Simple GET for sanity checks
        return JsonResponse({"info": "SantimPay Webhook endpoint, POST only"})

    def post(self, request: HttpRequest):
        raw_body = request.body
        logger.info(
            "SantimPay webhook received",
            extra={"content_length": len(raw_body)},
        )

        try:
            signature = get_webhook_signature(request)
            secret = get_santimpay_webhook_secret()
        except WebhookSignatureError:
            logger.warning("SantimPay webhook signature missing")
            return JsonResponse({"error": "Missing signature"}, status=401)
        except WebhookConfigurationError:
            logger.exception("SantimPay webhook secret is not configured")
            return JsonResponse({"error": "Webhook verification unavailable"}, status=500)

        if not verify_santimpay_signature(raw_body, signature, secret):
            logger.warning("SantimPay webhook signature verification failed")
            return JsonResponse({"error": "Invalid signature"}, status=403)

        logger.info("SantimPay webhook signature verification succeeded")

        try:
            payload = parse_webhook_payload(raw_body)
            event_id = extract_santimpay_event_id(payload)
            tx_id = extract_santimpay_reference(payload)
        except WebhookPayloadError as exc:
            logger.warning("SantimPay webhook malformed payload: %s", str(exc))
            WebhookLog.objects.create(
                provider="SANTIMPAY",
                event_type="MALFORMED_PAYLOAD",
                event_id=None,
                reference="MALFORMED_PAYLOAD",
                payload={"error": str(exc)},
                processed=False,
                processing_attempts=0,
            )
            return JsonResponse({"error": str(exc)}, status=400)

        try:
            with transaction.atomic():
                webhook_log = WebhookLog.objects.create(
                    provider="SANTIMPAY",
                    event_type="RECEIVED",
                    event_id=event_id,
                    reference=tx_id,
                    payload=payload,
                    processed=False,
                    processing_attempts=0,
                )
        except IntegrityError:
            logger.info(
                "Duplicate SantimPay webhook ignored",
                extra={"event_id": event_id, "tx_id": tx_id},
            )
            return JsonResponse({"status": "duplicate ignored"}, status=200)

        from payment.tasks import process_santimpay_webhook

        try:
            process_santimpay_webhook.delay(webhook_log.id)
        except Exception:
            logger.exception(
                "Failed to queue SantimPay webhook",
                extra={"webhook_log_id": webhook_log.id, "event_id": event_id, "tx_id": tx_id},
            )
            return JsonResponse({"error": "Webhook processing unavailable"}, status=503)

        logger.info(
            "SantimPay webhook queued",
            extra={"webhook_log_id": webhook_log.id, "event_id": event_id, "tx_id": tx_id},
        )
        return JsonResponse({"status": "accepted"}, status=200)
