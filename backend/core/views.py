from django.http import JsonResponse


def health(request):
    """Liveness only - no DB/cache/etc. touched, so a slow dependency can't
    false-negative this. Used by k8s/backend-deployment.yaml's readiness/
    liveness probes, and the deploy workflow's post-deploy health check."""
    return JsonResponse({'status': 'ok'})
