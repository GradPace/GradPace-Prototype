import pytest

from ..factories import UserFactory
from .helpers import PASSWORD


@pytest.mark.django_db
def test_login_returns_access_and_refresh_tokens(client):
    user = UserFactory()

    response = client.post(
        '/api/auth/login/',
        {'email': user.email, 'password': PASSWORD},
        content_type='application/json',
    )

    assert response.status_code == 200
    body = response.json()
    assert 'access' in body
    assert 'refresh' in body


@pytest.mark.django_db
def test_login_rejects_bad_password(client):
    user = UserFactory()

    response = client.post(
        '/api/auth/login/',
        {'email': user.email, 'password': 'wrong-password'},
        content_type='application/json',
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_refresh_issues_a_new_access_token(client):
    user = UserFactory()
    login = client.post(
        '/api/auth/login/',
        {'email': user.email, 'password': PASSWORD},
        content_type='application/json',
    )
    refresh_token = login.json()['refresh']

    response = client.post(
        '/api/auth/refresh/',
        {'refresh': refresh_token},
        content_type='application/json',
    )

    assert response.status_code == 200
    assert 'access' in response.json()


@pytest.mark.django_db
def test_me_requires_a_token(client):
    response = client.get('/api/auth/me/')

    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_the_authenticated_user(client):
    user = UserFactory()
    login = client.post(
        '/api/auth/login/',
        {'email': user.email, 'password': PASSWORD},
        content_type='application/json',
    )
    access_token = login.json()['access']

    response = client.get(
        '/api/auth/me/',
        HTTP_AUTHORIZATION=f'Bearer {access_token}',
    )

    assert response.status_code == 200
    assert response.json()['email'] == user.email


def post_login(client, email, password=PASSWORD):
    return client.post(
        '/api/auth/login/',
        {'email': email, 'password': password},
        content_type='application/json',
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    'typed',
    ['ada.lovelace@example.com', 'ADA.LOVELACE@EXAMPLE.COM', 'Ada.Lovelace@Example.com'],
)
def test_login_ignores_capitals_in_the_email(client, typed):
    UserFactory(email='Ada.Lovelace@example.com')

    response = post_login(client, typed)

    assert response.status_code == 200
    assert 'access' in response.json()


@pytest.mark.django_db
def test_login_with_a_different_case_email_still_checks_the_password(client):
    UserFactory(email='Ada.Lovelace@example.com')

    response = post_login(client, 'ada.lovelace@example.com', 'wrong-password')

    assert response.status_code == 401


@pytest.mark.django_db
def test_login_rejects_an_email_with_no_account_in_any_case(client):
    UserFactory(email='Ada.Lovelace@example.com')

    assert post_login(client, 'someone.else@example.com').status_code == 401
    assert post_login(client, 'SOMEONE.ELSE@EXAMPLE.COM').status_code == 401


@pytest.mark.django_db
def test_a_new_user_can_log_in_with_any_capitalisation_of_the_email_they_registered(client):
    client.post(
        '/api/auth/register/',
        {
            'email': 'Grace.Hopper@Example.com',
            'password': PASSWORD,
            'password_confirm': PASSWORD,
        },
        content_type='application/json',
    )

    for typed in [
        'Grace.Hopper@Example.com',
        'grace.hopper@example.com',
        'GRACE.HOPPER@EXAMPLE.COM',
    ]:
        assert post_login(client, typed).status_code == 200, typed


@pytest.mark.django_db
def test_a_deactivated_account_cannot_log_in_whatever_the_case(client):
    UserFactory(email='Ada.Lovelace@example.com', is_active=False)

    assert post_login(client, 'ada.lovelace@example.com').status_code == 401
