import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


def _append_query(url: str, params: dict) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(params)}"


def build_email_verification_link(*, user, request=None) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    query_params = {"uid": uid, "token": token}
    path = f"{reverse('verify-email')}?{urlencode(query_params)}"

    frontend_url = getattr(settings, "EMAIL_VERIFICATION_FRONTEND_URL", "").strip()
    if frontend_url:
        return _append_query(frontend_url, query_params)

    if request is not None:
        return request.build_absolute_uri(path)

    backend_base = getattr(settings, "EMAIL_VERIFICATION_BACKEND_BASE_URL", "").strip()
    if backend_base:
        return f"{backend_base.rstrip('/')}{path}"

    return path


def send_verification_email(*, user, request=None) -> bool:
    if not getattr(settings, "EMAIL_VERIFICATION_ENABLED", True):
        return False
    if not getattr(user, "email", ""):
        return False
    if getattr(user, "is_verified", False):
        return False

    verification_link = build_email_verification_link(user=user, request=request)
    subject = "Verify your account"
    body = (
        "Welcome to Shikela.\n\n"
        "Please verify your account by clicking the link below:\n"
        f"{verification_link}\n\n"
        "If you did not create this account, you can ignore this email."
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", ""),
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send verification email to user=%s", getattr(user, "id", "unknown"))
        return False
