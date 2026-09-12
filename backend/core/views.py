from django.http import JsonResponse


def health(request):
    """Liveness only - no DB/cache/etc. touched, so a slow dependency can't
    false-negative this. Used by docker-compose.prod.yml's healthcheck."""
    return JsonResponse({"status": "ok"})
