"""Cloudflare Turnstile verification for the public auth forms (login,
register). The frontend widget hands the browser a single-use token; the
backend confirms it with Cloudflare's siteverify API before doing anything
expensive (password hashing) with the request.

Fails closed, unlike PwnedPasswordValidator: this is a bot gate, so a
Cloudflare outage blocks login/registration rather than silently letting
every request through."""

import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from rest_framework import serializers

SITEVERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'

# The request field the frontend sends the widget's token in - same name the
# widget itself gives its hidden form input.
TOKEN_FIELD = 'cf_turnstile_response'


def _client_ip(request):
    """gradpace-api is proxied through Cloudflare, so REMOTE_ADDR is only
    Traefik - CF-Connecting-IP is the real client. Optional for siteverify
    (an extra signal, not a requirement), so None when it's absent."""
    if request is None:
        return None
    return request.META.get('HTTP_CF_CONNECTING_IP')


def verify_turnstile(token, action, request=None):
    """Raises a DRF ValidationError (under TOKEN_FIELD) unless `token` is a
    valid, unused Turnstile token issued by a widget rendered with this
    `action` ('login' / 'register') - so a token from one form can't be
    replayed against the other."""
    if not settings.TURNSTILE_ENABLED:
        return

    if not token:
        raise serializers.ValidationError(
            {TOKEN_FIELD: 'Please complete the verification challenge.'}
        )

    payload = {'secret': settings.TURNSTILE_SECRET_KEY, 'response': token}
    ip = _client_ip(request)
    if ip:
        payload['remoteip'] = ip

    try:
        verify_request = urllib.request.Request(
            SITEVERIFY_URL,
            data=urllib.parse.urlencode(payload).encode('utf-8'),
            headers={'User-Agent': 'gradpace-backend'},
        )
        with urllib.request.urlopen(verify_request, timeout=5) as response:
            result = json.load(response)
    except urllib.error.URLError, TimeoutError, OSError, ValueError:
        raise serializers.ValidationError(
            {TOKEN_FIELD: 'Could not verify the challenge right now. Please try again.'}
        ) from None

    # Cloudflare's testing keys (dev/e2e - see config/settings/dev.py) always
    # pass but never return an action, so the action check only applies to
    # real tokens. prod.py refuses to start with a testing secret.
    is_test_result = result.get('metadata', {}).get('result_with_testing_key', False)
    if not result.get('success') or (not is_test_result and result.get('action') != action):
        raise serializers.ValidationError({TOKEN_FIELD: 'Verification failed. Please try again.'})
