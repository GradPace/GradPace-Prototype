"""Email verification at registration (accounts/email_verification.py)."""

import re
from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from ..factories import UserFactory
from .helpers import PASSWORD, login, wait_for_emails

User = get_user_model()

REGISTER = '/api/auth/register/'
VERIFY = '/api/auth/verify-email/'


def register(client, email='new.user@example.com', first_name='Ada'):
    return client.post(
        REGISTER,
        {
            'first_name': first_name,
            'last_name': 'Lovelace',
            'email': email,
            'password': PASSWORD,
            'password_confirm': PASSWORD,
        },
        content_type='application/json',
    )


def verify(client, token):
    return client.post(VERIFY, {'token': token}, content_type='application/json')


def emailed_token():
    wait_for_emails()
    match = re.search(r'/verify-email\?token=([^\s"<]+)', mail.outbox[0].body)
    assert match, mail.outbox[0].body
    return match.group(1)


@pytest.mark.django_db
def test_registering_emails_the_new_address_a_verification_link(client, settings):
    settings.FRONTEND_URL = 'https://gradpace.example'

    assert register(client).status_code == 201
    wait_for_emails()

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == ['new.user@example.com']
    assert sent.subject == 'Verify your GradPace email address'
    assert 'https://gradpace.example/verify-email?token=' in sent.body
    assert sent.body.startswith('Hi Ada,')
    html, mimetype = sent.alternatives[0]
    assert mimetype == 'text/html'
    assert 'https://gradpace.example/verify-email?token=' in html


@pytest.mark.django_db
def test_the_text_email_does_not_html_escape_the_name(client):
    register(client, first_name="D'Arcy")
    wait_for_emails()

    assert mail.outbox[0].body.startswith("Hi D'Arcy,")


@pytest.mark.django_db
def test_a_new_account_starts_unverified_and_the_link_verifies_it(client):
    register(client, email='new.user@example.com')
    user = User.objects.get(email='new.user@example.com')
    assert user.email_verified is False

    response = verify(client, emailed_token())

    assert response.status_code == 200
    assert response.json() == {'verified': True, 'already_verified': False}
    user.refresh_from_db()
    assert user.email_verified is True


@pytest.mark.django_db
def test_opening_the_link_again_is_harmless(client):
    register(client)
    token = emailed_token()
    verify(client, token)

    response = verify(client, token)

    assert response.status_code == 200
    assert response.json() == {'verified': True, 'already_verified': True}


@pytest.mark.django_db
def test_me_reports_whether_the_email_is_verified(client):
    register(client, email='new.user@example.com')
    user = User.objects.get(email='new.user@example.com')
    headers = {'HTTP_AUTHORIZATION': f'Bearer {login(client, user)["access"]}'}

    assert client.get('/api/auth/me/', **headers).json()['email_verified'] is False

    verify(client, emailed_token())

    assert client.get('/api/auth/me/', **headers).json()['email_verified'] is True


@pytest.mark.django_db
def test_an_unverified_account_can_still_log_in(client):
    user = UserFactory()
    assert user.email_verified is False

    assert login(client, user)['access']


@pytest.mark.django_db
@pytest.mark.parametrize('token', ['', 'not-a-token', 'abc:def:ghi'])
def test_a_bad_token_is_rejected(client, token):
    response = verify(client, token)

    assert response.status_code == 400


@pytest.mark.django_db
def test_a_tampered_token_is_rejected(client):
    register(client)
    token = emailed_token()
    tampered = token[:-1] + ('A' if token[-1] != 'A' else 'B')

    assert verify(client, tampered).status_code == 400
    assert User.objects.get(email='new.user@example.com').email_verified is False


@pytest.mark.django_db
def test_a_missing_token_is_rejected(client):
    response = client.post(VERIFY, {}, content_type='application/json')

    assert response.status_code == 400


@pytest.mark.django_db
def test_an_expired_link_is_rejected(client):
    register(client)
    token = emailed_token()

    with mock.patch('accounts.email_verification.MAX_AGE', timedelta(seconds=-1)):
        response = verify(client, token)

    assert response.status_code == 400
    assert response.json() == {'detail': 'This verification link is invalid or has expired.'}
    assert User.objects.get(email='new.user@example.com').email_verified is False


@pytest.mark.django_db
def test_a_link_stops_working_if_the_account_email_changed(client):
    register(client)
    token = emailed_token()
    User.objects.filter(email='new.user@example.com').update(email='different@example.com')

    assert verify(client, token).status_code == 400


@pytest.mark.django_db
def test_a_link_for_a_deleted_account_is_rejected(client):
    register(client)
    token = emailed_token()
    User.objects.all().delete()

    assert verify(client, token).status_code == 400


@pytest.mark.django_db
def test_registration_still_succeeds_when_the_email_cannot_be_sent(client):
    with mock.patch('django.core.mail.EmailMultiAlternatives.send', side_effect=OSError('down')):
        response = register(client)
        wait_for_emails()

    assert response.status_code == 201
    assert User.objects.filter(email='new.user@example.com').exists()


@pytest.mark.django_db
def test_a_superuser_made_from_the_command_line_is_verified():
    user = User.objects.create_superuser('root@example.com', PASSWORD)

    assert user.email_verified is True


# --- resending the link -----------------------------------------------------

RESEND = '/api/auth/verify-email/resend/'


def authed(client, user):
    return {'HTTP_AUTHORIZATION': f'Bearer {login(client, user)["access"]}'}


@pytest.mark.django_db
def test_resending_requires_a_login(client):
    assert client.post(RESEND).status_code == 401


@pytest.mark.django_db
def test_resending_emails_the_link_again_to_the_registered_address(client):
    register(client, email='new.user@example.com')
    wait_for_emails()
    mail.outbox.clear()
    user = User.objects.get(email='new.user@example.com')

    response = client.post(RESEND, **authed(client, user))
    wait_for_emails()

    assert response.status_code == 200
    assert response.json() == {'sent': True, 'already_verified': False}
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ['new.user@example.com']
    assert mail.outbox[0].subject == 'Verify your GradPace email address'


@pytest.mark.django_db
def test_the_resent_link_verifies_the_account(client):
    register(client, email='new.user@example.com')
    wait_for_emails()
    mail.outbox.clear()
    user = User.objects.get(email='new.user@example.com')
    client.post(RESEND, **authed(client, user))

    response = verify(client, emailed_token())

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email_verified is True


@pytest.mark.django_db
def test_resending_to_a_verified_account_sends_nothing(client):
    user = UserFactory(email_verified=True)

    response = client.post(RESEND, **authed(client, user))
    wait_for_emails()

    assert response.status_code == 200
    assert response.json() == {'sent': False, 'already_verified': True}
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_resending_is_limited_per_user(client):
    user = UserFactory()
    headers = authed(client, user)

    statuses = [client.post(RESEND, **headers).status_code for _ in range(6)]
    wait_for_emails()

    assert statuses == [200, 200, 200, 200, 200, 429]
