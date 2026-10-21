from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from ..factories import UserFactory
from ..serializers import RegisterSerializer
from .helpers import PASSWORD

User = get_user_model()


@pytest.mark.django_db
def test_register_creates_a_user_and_returns_tokens(client):
    response = client.post(
        '/api/auth/register/',
        {
            'email': 'newuser@example.com',
            'password': PASSWORD,
            'password_confirm': PASSWORD,
        },
        content_type='application/json',
    )

    assert response.status_code == 201
    body = response.json()
    assert 'access' in body
    assert 'refresh' in body

    user = User.objects.get(email='newuser@example.com')
    assert user.check_password(PASSWORD)
    assert user.role.role_name == 'student'


@pytest.mark.django_db
def test_register_rejects_duplicate_email_regardless_of_case(client):
    UserFactory(email='Taken@Example.com')

    response = client.post(
        '/api/auth/register/',
        {
            'email': 'taken@example.com',
            'password': PASSWORD,
            'password_confirm': PASSWORD,
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    assert 'email' in response.json()


@pytest.mark.django_db
def test_database_rejects_emails_differing_only_by_case():
    UserFactory(email='Taken@Example.com')

    with pytest.raises(IntegrityError):
        UserFactory(email='taken@example.com')


@pytest.mark.django_db
def test_register_returns_400_when_it_loses_a_race_for_the_email(client):
    """Another request registers the same email between validate_email's
    check and the insert - the unique_email_ci constraint catches it."""
    UserFactory(email='Taken@Example.com')

    with patch.object(RegisterSerializer, 'validate_email', side_effect=lambda value: value):
        response = client.post(
            '/api/auth/register/',
            {
                'email': 'taken@example.com',
                'password': PASSWORD,
                'password_confirm': PASSWORD,
            },
            content_type='application/json',
        )

    assert response.status_code == 400
    assert 'email' in response.json()


@pytest.mark.django_db
def test_register_rejects_mismatched_passwords(client):
    response = client.post(
        '/api/auth/register/',
        {
            'email': 'newuser@example.com',
            'password': PASSWORD,
            'password_confirm': 'something-else',
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    assert 'password_confirm' in response.json()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'password',
    [
        pytest.param('Ab1!ab1', id='too-short'),
        pytest.param('str0ng!pass', id='no-uppercase'),
        pytest.param('Strong!Pass', id='no-number'),
        pytest.param('Str0ngPass', id='no-special-character'),
        pytest.param('Password1!', id='dictionary-word'),
        pytest.param('Passsss1!', id='repeated-characters'),
        pytest.param('Abcd1234!', id='sequential-characters'),
        pytest.param('password123', id='common-password'),
    ],
)
def test_register_rejects_a_weak_password(client, password):
    response = client.post(
        '/api/auth/register/',
        {
            'email': 'newuser@example.com',
            'password': password,
            'password_confirm': password,
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    assert 'password' in response.json()
