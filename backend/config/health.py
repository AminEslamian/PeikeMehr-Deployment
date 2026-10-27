import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache


logger = logging.getLogger(__name__)


@never_cache
def health(request):
    """Lightweight liveness/readiness probe (no secrets, no stack traces)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Health check failed: database is unavailable")
        return JsonResponse(
            {"status": "error", "database": "error"},
            status=503,
        )

    return JsonResponse({"status": "ok", "database": "ok"})
