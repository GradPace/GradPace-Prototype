import io
import json
import urllib.error
import urllib.parse
from unittest import mock

import pytest
from django.contrib.auth import get_user_model

from ..factories import UserFactory
from .helpers import PASSWORD

User = get_user_model()


@pytest.fixture
def turnstile_on(settings):
    settings.TURNSTILE_ENABLED = True
    settings.TURNSTILE_SECRET_KEY = 'real-secret'


def siteverify_returns(**result):
    """Patches accounts.turnstile's urlopen to answer with `result` as
    Cloudflare's siteverify JSON - returns the mock, so tests can inspect
    what was sent."""
    return mock.patch(
        'accounts.turnstile.urllib.request.urlopen',
        return_value=io.BytesIO(json.dumps(result).encode()),
    )


def sent_payload(urlopen_mock):
    request = urlopen_mock.call_args.args[0]
    return dict(urllib.parse.parse_qsl(request.data.decode()))


def login(client, user, **extra):
    return client.post(
        '/api/auth/login/',
        {'email': user.email, 'password': PASSWORD, **extra},
        content_type='application/json',
    )


def register(client, **extra):
    return client.post(
        '/api/auth/register/',
        {
            'email': 'newuser@example.com',
            'password': PASSWORD,
            'password_confirm': PASSWORD,
            **extra,
        },
        content_type='application/json',
    )


@pytest.mark.django_db
def test_login_requires_a_token(client, turnstile_on):
    user = UserFactory()

    with siteverify_returns(success=True, action='login') as urlopen:
        response = login(client, user)

    assert response.status_code == 400
    assert 'cf_turnstile_response' in response.json()
    urlopen.assert_not_called()


@pytest.mark.django_db
def test_login_succeeds_with_a_valid_token(client, turnstile_on):
    user = UserFactory()

    with siteverify_returns(success=True, action='login') as urlopen:
        response = login(client, user, cf_turnstile_response='tok')

    assert response.status_code == 200
    assert 'access' in response.json()
    assert sent_payload(urlopen) == {'secret': 'real-secret', 'response': 'tok'}


@pytest.mark.django_db
def test_login_rejects_a_failed_token_before_checking_the_password(client, turnstile_on):
    user = UserFactory()

    with siteverify_returns(success=False, **{'error-codes': ['invalid-input-response']}):
        response = login(client, user, cf_turnstile_response='tok', password='wrong')

    # 400 from Turnstile, not simplejwt's 401 for a bad password.
    assert response.status_code == 400
    assert 'cf_turnstile_response' in response.json()


@pytest.mark.django_db
def test_login_rejects_a_token_issued_for_the_register_form(client, turnstile_on):
    user = UserFactory()

    with siteverify_returns(success=True, action='register'):
        response = login(client, user, cf_turnstile_response='tok')

    assert response.status_code == 400


@pytest.mark.django_db
def test_testing_key_results_skip_the_action_check(client, turnstile_on):
    """Cloudflare's testing secret (dev/e2e) passes without an action."""
    user = UserFactory()

    with siteverify_returns(success=True, metadata={'result_with_testing_key': True}):
        response = login(client, user, cf_turnstile_response='tok')

    assert response.status_code == 200


@pytest.mark.django_db
def test_fails_closed_when_cloudflare_is_unreachable(client, turnstile_on):
    user = UserFactory()

    with mock.patch(
        'accounts.turnstile.urllib.request.urlopen',
        side_effect=urllib.error.URLError('down'),
    ):
        response = login(client, user, cf_turnstile_response='tok')

    assert response.status_code == 400
    assert 'cf_turnstile_response' in response.json()


@pytest.mark.django_db
def test_forwards_the_cloudflare_client_ip(client, turnstile_on):
    user = UserFactory()

    with siteverify_returns(success=True, action='login') as urlopen:
        client.post(
            '/api/auth/login/',
            {'email': user.email, 'password': PASSWORD, 'cf_turnstile_response': 'tok'},
            content_type='application/json',
            HTTP_CF_CONNECTING_IP='203.0.113.7',
        )

    assert sent_payload(urlopen)['remoteip'] == '203.0.113.7'


@pytest.mark.django_db
def test_register_requires_a_valid_token(client, turnstile_on):
    with siteverify_returns(success=False):
        response = register(client, cf_turnstile_response='tok')

    assert response.status_code == 400
    assert 'cf_turnstile_response' in response.json()
    assert not User.objects.filter(email='newuser@example.com').exists()


@pytest.mark.django_db
def test_register_succeeds_with_a_valid_token(client, turnstile_on):
    with siteverify_returns(success=True, action='register'):
        response = register(client, cf_turnstile_response='tok')

    assert response.status_code == 201
    assert User.objects.filter(email='newuser@example.com').exists()
