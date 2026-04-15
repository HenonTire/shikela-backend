
from pathlib import Path
from datetime import timedelta
import os
import glob
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = "django-insecure-a5mnheq-h^(s0si(td8&-+g47bnk9q+lxf0t-kk=2n%fn0dn_f"


DEBUG = True

ALLOWED_HOSTS = []



INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'rest_framework',
    #apps
    'account',
    'shop',
    'catalog',
    'inventory',
    'order',
    'payment',
    'courier',
    'supliers',
    'marketer.apps.MarketerConfig',
    'notifications',
    'analytics',
    'hub',

]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"



DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]



LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True



STATIC_URL = "static/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "account.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}



SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),   # 1 hour
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),     # 30 days

    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# Email engine
EMAIL_NOTIFICATIONS_ENABLED = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "false").lower() in {"1", "true", "yes", "on"}
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@shikela.local")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
EMAIL_VERIFICATION_ENABLED = os.getenv("EMAIL_VERIFICATION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
EMAIL_VERIFICATION_REQUIRED_FOR_LOGIN = os.getenv("EMAIL_VERIFICATION_REQUIRED_FOR_LOGIN", "true").lower() in {"1", "true", "yes", "on"}
EMAIL_VERIFICATION_BACKEND_BASE_URL = os.getenv("EMAIL_VERIFICATION_BACKEND_BASE_URL", "")
EMAIL_VERIFICATION_FRONTEND_URL = os.getenv("EMAIL_VERIFICATION_FRONTEND_URL", "")
# Optional event toggles (policy-based email rules)
EMAIL_SEND_ORDER_SHIPPED = os.getenv("EMAIL_SEND_ORDER_SHIPPED", "false").lower() in {"1", "true", "yes", "on"}
EMAIL_SEND_ORDER_DELIVERED = os.getenv("EMAIL_SEND_ORDER_DELIVERED", "false").lower() in {"1", "true", "yes", "on"}
EMAIL_SEND_URGENT_LOW_STOCK = os.getenv("EMAIL_SEND_URGENT_LOW_STOCK", "true").lower() in {"1", "true", "yes", "on"}
EMAIL_SEND_OTHER_NOTIFICATION_TYPES = os.getenv("EMAIL_SEND_OTHER_NOTIFICATION_TYPES", "false").lower() in {"1", "true", "yes", "on"}

# SantimPay (test mode by default for local development)
def _normalize_pem(value: str) -> str:
    # Support env values stored with literal '\n' characters.
    return (value or "").replace("\\n", "\n")


# Default to SantimPay testnet unless explicitly opting into production.
SANTIMPAY_TEST_BED = os.getenv("SANTIMPAY_TEST_BED", "true").lower() in {"1", "true", "yes", "on"}
SANTIMPAY_MERCHANT_ID = os.getenv("SANTIMPAY_MERCHANT_ID", "9e2dab64-e2bb-4837-9b85-d855dd878d2b")
SANTIMPAY_PRIVATE_KEY = _normalize_pem(
    os.getenv(
        "SANTIMPAY_PRIVATE_KEY",
        """
-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIA6End3PsH0SIKGrNSv1Oie2xcubUtIbkiiWO36ZM6JXoAoGCCqGSM49
AwEHoUQDQgAEPT1BI//IvDUZn3vFBrwSM+Q1CT9KF64XVyMeidH7XSc4bRsszQUf
FGcp7Hy7iV4Bf9U5MRY8YKpExoThMGfJBw==
-----END EC PRIVATE KEY-----
""".strip(),
    )
)
SANTIMPAY_SIGN_TOKEN_URL = os.getenv("SANTIMPAY_SIGN_TOKEN_URL", "")
SANTIMPAY_SUCCESS_REDIRECT_URL = os.getenv("SANTIMPAY_SUCCESS_REDIRECT_URL", "http://localhost:8000/payment/success")
SANTIMPAY_FAILURE_REDIRECT_URL = os.getenv("SANTIMPAY_FAILURE_REDIRECT_URL", "http://localhost:8000/payment/failure")
SANTIMPAY_CANCEL_REDIRECT_URL = os.getenv("SANTIMPAY_CANCEL_REDIRECT_URL", "http://localhost:8000/payment/cancel")
SANTIMPAY_NOTIFY_URL = os.getenv("SANTIMPAY_NOTIFY_URL", "http://localhost:8000/payment/webhook/santimpay/")

# Platform payout resolution
PLATFORM_USER_ID = os.getenv("PLATFORM_USER_ID", "")
PLATFORM_USER_EMAIL = os.getenv("PLATFORM_USER_EMAIL", "")
PLATFORM_MERCHANT_ID = os.getenv("PLATFORM_MERCHANT_ID", "")

# Firebase Cloud Messaging
FCM_PROJECT_ID = os.getenv("FCM_PROJECT_ID", "")
# Auto-discover service account from notifications/fcm if env var is not set.
_default_fcm_service_account = ""
_fcm_candidates = glob.glob(str(BASE_DIR / "notifications" / "fcm" / "*firebase-adminsdk*.json"))
if _fcm_candidates:
    _default_fcm_service_account = _fcm_candidates[0]

FCM_SERVICE_ACCOUNT_FILE = os.getenv("FCM_SERVICE_ACCOUNT_FILE", _default_fcm_service_account)
FCM_SERVICE_ACCOUNT_JSON = os.getenv("FCM_SERVICE_ACCOUNT_JSON", "")
