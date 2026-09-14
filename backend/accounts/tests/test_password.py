import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from ..factories import UserFactory
from .helpers import NEW_PASSWORD, PASSWORD, login


@pytest.mark.django_db
def test_password_change_succeeds_and_blacklists_old_sessions(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        '/api/auth/password/change/',
        {
            'old_password': PASSWORD,
            'new_password': NEW_PASSWORD,
            'new_password_confirm': NEW_PASSWORD,
        },
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )
    assert response.status_code == 204

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)

    # The refresh token from before the change no longer works.
    refresh_response = client.post(
        '/api/auth/refresh/',
        {'refresh': tokens['refresh']},
        content_type='application/json',
    )
    assert refresh_response.status_code == 401


@pytest.mark.django_db
def test_password_change_rejects_wrong_current_password(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        '/api/auth/password/change/',
        {
            'old_password': 'wrong-password',
            'new_password': NEW_PASSWORD,
            'new_password_confirm': NEW_PASSWORD,
        },
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 400
    assert 'old_password' in response.json()


@pytest.mark.django_db
def test_password_change_requires_authentication(client):
    response = client.post(
        '/api/auth/password/change/',
        {
            'old_password': PASSWORD,
            'new_password': NEW_PASSWORD,
            'new_password_confirm': NEW_PASSWORD,
        },
        content_type='application/json',
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_password_reset_request_emails_a_link_for_a_known_address(client):
    user = UserFactory()

    response = client.post(
        '/api/auth/password/reset/',
        {'email': user.email},
        content_type='application/json',
    )

    assert response.status_code == 200
    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == [user.email]
    assert 'reset-password' in sent.body
    # HTML alternative attached alongside the plain-text body.
    assert any(content_type == 'text/html' for _, content_type in sent.alternatives)


@pytest.mark.django_db
def test_password_reset_request_is_silent_for_an_unknown_address(client):
    response = client.post(
        '/api/auth/password/reset/',
        {'email': 'nobody@example.com'},
        content_type='application/json',
    )

    # Same 200 either way - can't be used to enumerate accounts.
    assert response.status_code == 200
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_confirm_succeeds_with_a_valid_token(client):
    user = UserFactory()
    tokens = login(client, user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    response = client.post(
        '/api/auth/password/reset/confirm/',
        {
            'uid': uid,
            'token': token,
            'new_password': NEW_PASSWORD,
            'new_password_confirm': NEW_PASSWORD,
        },
        content_type='application/json',
    )
    assert response.status_code == 200

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)

    # Sessions from before the reset no longer work either.
    refresh_response = client.post(
        '/api/auth/refresh/',
        {'refresh': tokens['refresh']},
        content_type='application/json',
    )
    assert refresh_response.status_code == 401


@pytest.mark.django_db
def test_password_reset_confirm_rejects_an_invalid_token(client):
    user = UserFactory()
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    response = client.post(
        '/api/auth/password/reset/confirm/',
        {
            'uid': uid,
            'token': 'not-a-real-token',
            'new_password': NEW_PASSWORD,
            'new_password_confirm': NEW_PASSWORD,
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    assert 'token' in response.json()


@pytest.mark.django_db
def test_password_reset_confirm_rejects_an_invalid_uid(client):
    response = client.post(
        '/api/auth/password/reset/confirm/',
        {
            'uid': 'not-a-real-uid',
            'token': 'irrelevant',
            'new_password': NEW_PASSWORD,
            'new_password_confirm': NEW_PASSWORD,
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    assert 'uid' in response.json()
