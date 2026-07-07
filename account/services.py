import logging
from urllib.parse import urlencode
from django.core.mail import EmailMultiAlternatives
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

    subject = "Verify your Shikela account ✉️"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Shikela Team <shikelateam@gmail.com>")
    recipient_list = [user.email]

    # 📩 Plain text version (fallback)
    text_body = (
        "👋 Welcome to Shikela!\n\n"
        "You're almost ready to get started.\n\n"
        "Please verify your account by clicking the link below:\n\n"
        f"{verification_link}\n\n"
        "This helps us keep your account secure.\n\n"
        "If you didn’t create this account, ignore this email.\n\n"
        "— The Shikela Team"
    )

    # 🌐 HTML version (what user actually sees)
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px;">
        
        <h2 style="color:#333;">Welcome to Shikela 👋</h2>

        <p style="font-size:16px;color:#555;">
            You're almost ready to get started.
        </p>

        <p style="font-size:16px;color:#555;">
            Please verify your account by clicking the button below:
        </p>

        <div style="margin:30px 0;">
            <a href="{verification_link}"
               style="background:#4F46E5;color:white;padding:12px 20px;
                      text-decoration:none;border-radius:6px;display:inline-block;">
                Verify Account
            </a>
        </div>

        <p style="font-size:14px;color:#777;">
            This helps us keep your account secure.
        </p>

        <hr>

        <p style="font-size:12px;color:#999;">
            If you didn’t create this account, you can ignore this email.<br>
            — The Shikela Team
        </p>

    </div>
    """

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=recipient_list,
        )

        email.attach_alternative(html_body, "text/html")
        email.send()

        return True

    except Exception:
        logger.exception(
            "Failed to send verification email to user=%s",
            getattr(user, "id", "unknown"),
        )
        return False