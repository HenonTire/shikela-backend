from __future__ import annotations

import logging

from celery import shared_task

from payment.views import _get_platform_merchant_id
from payment.services.service import PaymentService


logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_santimpay_webhook(self, webhook_log_id: int) -> None:
    logger.info("SantimPay webhook task started", extra={"webhook_log_id": webhook_log_id})
    merchant_id = _get_platform_merchant_id()
    service = PaymentService(merchant_id=merchant_id)
    service.process_santimpay_webhook(webhook_log_id)
    logger.info("SantimPay webhook task finished", extra={"webhook_log_id": webhook_log_id})
