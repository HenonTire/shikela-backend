from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from django.conf import settings
from django.http import HttpRequest


SANTIMPAY_SIGNATURE_HEADERS = (
    "HTTP_X_SANTIMPAY_SIGNATURE",
    "HTTP_X_SANTIMPAY_SIGNATURE_SHA256",
    "HTTP_X_WEBHOOK_SIGNATURE",
    "HTTP_X_HUB_SIGNATURE_256",
)


class WebhookConfigurationError(Exception):
    """Raised when webhook verification cannot be configured safely."""


class WebhookSignatureError(Exception):
    """Raised when a webhook signature is missing or invalid."""


class WebhookPayloadError(Exception):
    """Raised when a webhook payload is malformed or incomplete."""


def get_santimpay_webhook_secret() -> str:
    secret = getattr(settings, "SANTIMPAY_WEBHOOK_SECRET", None) or os.getenv("SANTIMPAY_WEBHOOK_SECRET")
    if not secret:
        raise WebhookConfigurationError("SANTIMPAY_WEBHOOK_SECRET is not configured")
    return str(secret)


def get_webhook_signature(request: HttpRequest) -> str:
    for header in SANTIMPAY_SIGNATURE_HEADERS:
        value = request.META.get(header)
        if value:
            return str(value).strip()
    raise WebhookSignatureError("Missing SantimPay webhook signature")


def build_santimpay_signature(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def verify_santimpay_signature(raw_body: bytes, signature: str, secret: str | None = None) -> bool:
    expected = build_santimpay_signature(raw_body, secret or get_santimpay_webhook_secret())
    normalized_signature = signature.strip().lower()
    candidates = {normalized_signature}
    if normalized_signature.startswith("sha256="):
        candidates.add(normalized_signature.split("=", 1)[1].strip())
    else:
        candidates.add(f"sha256={normalized_signature}")

    return any(
        hmac.compare_digest(candidate, expected) or hmac.compare_digest(candidate, f"sha256={expected}")
        for candidate in candidates
    )


def parse_webhook_payload(raw_body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebhookPayloadError("Malformed JSON payload") from exc

    if not isinstance(payload, dict):
        raise WebhookPayloadError("Webhook payload must be a JSON object")
    return payload


def extract_santimpay_reference(payload: dict[str, Any]) -> str:
    for key in ("id", "transaction_id", "transactionId", "tx_id", "txId", "payment_reference", "reference"):
        value = payload.get(key)
        if value:
            return str(value)
    raise WebhookPayloadError("Missing transaction reference")


def extract_santimpay_event_id(payload: dict[str, Any]) -> str:
    for key in (
        "event_id",
        "eventId",
        "webhook_id",
        "webhookId",
        "notification_id",
        "notificationId",
        "id",
        "transaction_id",
        "transactionId",
        "tx_id",
        "txId",
        "payment_reference",
        "reference",
    ):
        value = payload.get(key)
        if value:
            return str(value)
    raise WebhookPayloadError("Missing webhook event identifier")
