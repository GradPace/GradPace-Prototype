import logging

from rest_framework.throttling import ScopedRateThrottle

logger = logging.getLogger(__name__)


class AuthRateThrottle(ScopedRateThrottle):
    """ScopedRateThrottle for the public auth endpoints (see
    DEFAULT_THROTTLE_RATES), keyed on the real client IP and failing open.

    gradpace-api is proxied through Cloudflare, so REMOTE_ADDR is only
    Traefik - DRF's default would put every anonymous client in one shared
    bucket. CF-Connecting-IP is the real client, same as accounts/turnstile.py
    uses.

    On an authenticated endpoint (the transcript upload) ScopedRateThrottle
    keys on the user instead, so get_ident() isn't used there."""

    def get_ident(self, request):
        return request.META.get('HTTP_CF_CONNECTING_IP') or super().get_ident(request)

    def allow_request(self, request, view):
        # The counts live in the cache (Redis in prod). If it's unreachable,
        # let the request through rather than take login down with it -
        # Turnstile still stands in front of login/register.
        try:
            return super().allow_request(request, view)
        except Exception:
            logger.exception('Throttle cache unavailable - allowing request')
            return True
