from django.db import connection
from django.http import JsonResponse


def health_check(_request):
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    payload = {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
    }
    return JsonResponse(payload, status=200 if db_ok else 503)
