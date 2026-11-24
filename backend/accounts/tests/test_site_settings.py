import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError, transaction

from ..factories import AdminUserFactory, AlumniUserFactory, UserFactory
from ..models import SiteSettings
from .helpers import login, wait_for_emails
from .test_email_verification import register

User = get_user_model()

URL = '/api/auth/admin/settings/'


def auth(user, client):
    return {'HTTP_AUTHORIZATION': f'Bearer {login(client, user)["access"]}'}


def get_settings(client, user):
    return client.get(URL, **auth(user, client))


def patch_settings(client, user, data):
    return client.patch(URL, data, content_type='application/json', **auth(user, client))


def switch_off():
    SiteSettings.objects.update_or_create(
        pk=SiteSettings.SINGLETON_PK, defaults={'require_email_verification': False}
    )


# Who can use it
@pytest.mark.django_db
def test_get_requires_authentication(client):
    assert client.get(URL).status_code == 401


@pytest.mark.django_db
def test_patch_requires_authentication(client):
    response = client.patch(
        URL, {'require_email_verification': False}, content_type='application/json'
    )

    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize('factory', [UserFactory, AlumniUserFactory])
def test_non_admins_cannot_read(client, factory):
    assert get_settings(client, factory()).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize('factory', [UserFactory, AlumniUserFactory])
def test_non_admins_cannot_change(client, factory):
    response = patch_settings(client, factory(), {'require_email_verification': False})

    assert response.status_code == 403
    assert SiteSettings.load().require_email_verification is True


# Reading and changing
@pytest.mark.django_db
def test_defaults_on_a_fresh_database(client):
    assert not SiteSettings.objects.exists()

    response = get_settings(client, AdminUserFactory())

    assert response.status_code == 200
    body = response.json()
    assert body['require_email_verification'] is True
    assert body['updated_by'] is None
    assert SiteSettings.objects.count() == 1


@pytest.mark.django_db
def test_patch_flips_the_switch_and_records_who(client):
    admin = AdminUserFactory(email='admin@example.com')

    response = patch_settings(client, admin, {'require_email_verification': False})

    assert response.status_code == 200
    assert response.json()['require_email_verification'] is False
    assert response.json()['updated_by'] == 'admin@example.com'
    site_settings = SiteSettings.load()
    assert site_settings.require_email_verification is False
    assert site_settings.updated_by == admin

    response = patch_settings(client, admin, {'require_email_verification': True})

    assert response.json()['require_email_verification'] is True


@pytest.mark.django_db
def test_other_fields_are_ignored(client):
    admin = AdminUserFactory()
    someone_else = UserFactory()

    response = patch_settings(
        client,
        admin,
        {
            'require_email_verification': False,
            'updated_by': someone_else.email,
            'updated_at': '2000-01-01T00:00:00Z',
            'id': 7,
        },
    )

    assert response.status_code == 200
    site_settings = SiteSettings.load()
    assert site_settings.pk == SiteSettings.SINGLETON_PK
    assert site_settings.updated_by == admin
    assert site_settings.updated_at.year != 2000
    assert SiteSettings.objects.count() == 1


@pytest.mark.django_db
def test_put_is_not_allowed(client):
    response = client.put(
        URL,
        {'require_email_verification': False},
        content_type='application/json',
        **auth(AdminUserFactory(), client),
    )

    assert response.status_code == 405


# One row only
@pytest.mark.django_db
def test_load_always_returns_the_same_row():
    assert SiteSettings.load().pk == SiteSettings.load().pk == SiteSettings.SINGLETON_PK
    assert SiteSettings.objects.count() == 1


@pytest.mark.django_db
def test_database_rejects_a_second_row():
    SiteSettings.load()

    with pytest.raises(IntegrityError), transaction.atomic():
        SiteSettings.objects.create(pk=2)


# /me
@pytest.mark.django_db
def test_me_reports_the_switch(client):
    user = UserFactory()
    headers = auth(user, client)

    assert client.get('/api/auth/me/', **headers).json()['email_verification_required'] is True

    switch_off()

    assert client.get('/api/auth/me/', **headers).json()['email_verification_required'] is False


# Turning it off changes nothing else
@pytest.mark.django_db
def test_signup_still_sends_the_verification_email_when_off(client):
    switch_off()

    response = register(client, email='new.user@example.com')

    assert response.status_code == 201
    wait_for_emails()
    assert len(mail.outbox) == 1
    assert '/verify-email?token=' in mail.outbox[0].body
    assert User.objects.get(email='new.user@example.com').email_verified is False


@pytest.mark.django_db
@pytest.mark.parametrize('verified', [False, True])
def test_switching_never_changes_email_verified(client, verified):
    user = UserFactory(email_verified=verified)
    admin = AdminUserFactory()

    patch_settings(client, admin, {'require_email_verification': False})
    patch_settings(client, admin, {'require_email_verification': True})

    user.refresh_from_db()
    assert user.email_verified is verified
