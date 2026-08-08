from pathlib import Path
from datetime import timedelta
import os
import glob
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent


# 0107269
load_dotenv(BASE_DIR / ".env")

# DEBUG is read first so the code can enforce secure defaults in production
DEBUG = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"}

from django.core.exceptions import ImproperlyConfigured

# SECRET_KEY must be provided via environment in production. When DEBUG is True
# an obviously insecure development default is allowed for convenience only.
_secret = os.getenv("DJANGO_SECRET_KEY", "")
if not _secret:
    if DEBUG:
        SECRET_KEY = "insecure-dev-secret-for-local-testing-only"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY environment variable is required when DEBUG is False")
else:
    SECRET_KEY = _secret

ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]
if DEBUG:
    ALLOWED_HOSTS.append(".ngrok-free.app")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if DEBUG:
    CSRF_TRUSTED_ORIGINS.append("https://*.ngrok-free.app")
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework_simplejwt.token_blacklist",  
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
    'procurement',
    'cloudinary_storage',
    'django.contrib.staticfiles',
  

]

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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



if os.getenv("DATABASE_URL"):
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.config(
            default=os.getenv("DATABASE_URL"),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
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
STATIC_ROOT = BASE_DIR / "staticfiles"

# Modern Django storage config — this is the real source of truth
#
# NOTE: switched from CompressedManifestStaticFilesStorage to
# CompressedStaticFilesStorage. The manifest variant hashes filenames and
# rewrites url()/@import references inside CSS during collectstatic — that
# rewrite step currently crashes on Django 6.0.2's admin/css/forms.css
# reference to admin/css/widgets.css under whitenoise 6.12.0
# (MissingFileError), and WHITENOISE_MANIFEST_STRICT does not suppress it
# since it's a collectstatic-time failure, not a runtime lookup. Dropping
# the manifest/hashing layer avoids that crash entirely. We keep
# compression (gzip/brotli) for serving performance. Static files just
# won't get cache-busting hashed filenames until this is fixed upstream —
# fine for now since this mainly affects the Django admin panel.
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "core.staticfiles.ResilientCompressedStaticFilesStorage",
    },
}

STATICFILES_STORAGE = "core.staticfiles.ResilientCompressedStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


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
    "DEFAULT_PAGINATION_CLASS": "core.pagination.DefaultPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth": "10/min",
        "santimpay_webhook": "60/min",
    },
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

# SantimPay credentials must be provided via environment when running with DEBUG=False.
SANTIMPAY_MERCHANT_ID = os.getenv("SANTIMPAY_MERCHANT_ID", "")
_santimpay_private_key_raw = os.getenv("SANTIMPAY_PRIVATE_KEY", "")
if not SANTIMPAY_MERCHANT_ID and not DEBUG:
    raise ImproperlyConfigured("SANTIMPAY_MERCHANT_ID environment variable is required when DEBUG is False")
if not _santimpay_private_key_raw and not DEBUG:
    raise ImproperlyConfigured("SANTIMPAY_PRIVATE_KEY environment variable is required when DEBUG is False")
SANTIMPAY_PRIVATE_KEY = _normalize_pem(_santimpay_private_key_raw)
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

# Celery
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
