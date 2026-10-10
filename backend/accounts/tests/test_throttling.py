from unittest.mock import patch

import pytest

from ..factories import UserFactory
from .helpers import PASSWORD

LOGIN_LIMIT = 10  # DEFAULT_THROTTLE_RATES['login']


def post_login(client, user, **extra):
    return client.post(
        '/api/auth/login/',
        {'email': user.email, 'password': PASSWORD},
        content_type='application/json',
        **extra,
    )


@pytest.mark.django_db
def test_login_is_throttled_after_the_limit(client):
    user = UserFactory()

    for _ in range(LOGIN_LIMIT):
        assert post_login(client, user).status_code == 200

    response = post_login(client, user)
    assert response.status_code == 429
    assert 'Retry-After' in response


@pytest.mark.django_db
def test_throttle_counts_each_cloudflare_client_ip_separately(client):
    """Behind Cloudflare + Traefik every request has the same REMOTE_ADDR -
    the throttle must key on CF-Connecting-IP, or one client locks out all."""
    user = UserFactory()

    for _ in range(LOGIN_LIMIT):
        post_login(client, user, HTTP_CF_CONNECTING_IP='203.0.113.1')

    assert post_login(client, user, HTTP_CF_CONNECTING_IP='203.0.113.1').status_code == 429
    assert post_login(client, user, HTTP_CF_CONNECTING_IP='203.0.113.2').status_code == 200


@pytest.mark.django_db
def test_throttle_fails_open_when_the_cache_is_down(client):
    user = UserFactory()

    with patch('django.core.cache.cache.get', side_effect=ConnectionError('redis down')):
        for _ in range(LOGIN_LIMIT + 1):
            assert post_login(client, user).status_code == 200
