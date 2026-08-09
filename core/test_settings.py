from .settings import *

# Disable celery during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use local filesystem storage during tests instead of real Cloudinary uploads
STORAGES = {
    **STORAGES,
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
}

# Use local filesystem storage during tests instead of real Cloudinary uploads
STORAGES = {
    **STORAGES,
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
}
