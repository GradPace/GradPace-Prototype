import pytest

from .. import roles
from ..factories import AdminUserFactory, AlumniUserFactory, UserFactory
from .helpers import login

LIST_URL = '/api/auth/admin/users/'


def detail_url(user):
    return f'{LIST_URL}{user.id}/'


def auth(tokens):
    return {'HTTP_AUTHORIZATION': f'Bearer {tokens["access"]}'}


def list_users(client, admin, **params):
    return client.get(LIST_URL, params, **auth(login(client, admin)))


def patch(client, admin, user, data):
    return client.patch(
        detail_url(user), data, content_type='application/json', **auth(login(client, admin))
    )


def emails(response):
    return [row['email'] for row in response.json()['results']]


# Who can use it
@pytest.mark.django_db
def test_list_requires_authentication(client):
    assert client.get(LIST_URL).status_code == 401


@pytest.mark.django_db
def test_update_requires_authentication(client):
    user = UserFactory()

    response = client.patch(detail_url(user), {'is_active': False}, content_type='application/json')

    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize('factory', [UserFactory, AlumniUserFactory])
def test_non_admins_cannot_list(client, factory):
    response = list_users(client, factory())

    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize('factory', [UserFactory, AlumniUserFactory])
def test_non_admins_cannot_update(client, factory):
    other = UserFactory()

    response = patch(client, factory(), other, {'is_active': False})

    assert response.status_code == 403
    other.refresh_from_db()
    assert other.is_active


# Listing
@pytest.mark.django_db
def test_admin_lists_users(client):
    admin = AdminUserFactory(email='admin@example.com')
    student = UserFactory(email='ada@example.com', first_name='Ada', last_name='Lovelace')

    response = list_users(client, admin)

    assert response.status_code == 200
    body = response.json()
    assert body['count'] == 2
    row = next(row for row in body['results'] if row['email'] == 'ada@example.com')
    assert row == {
        'id': str(student.id),
        'first_name': 'Ada',
        'last_name': 'Lovelace',
        'email': 'ada@example.com',
        'role': roles.STUDENT,
        'date_joined': row['date_joined'],
        'is_active': True,
    }
    assert row['date_joined']


@pytest.mark.django_db
def test_search_is_partial_and_case_insensitive(client):
    admin = AdminUserFactory(email='admin@example.com')
    UserFactory(email='ada.l@example.com')
    UserFactory(email='grace@example.com')

    response = list_users(client, admin, search='ADA')

    assert emails(response) == ['ada.l@example.com']


@pytest.mark.django_db
def test_search_with_no_match_is_empty(client):
    admin = AdminUserFactory()

    response = list_users(client, admin, search='nobody')

    assert response.json()['count'] == 0
    assert emails(response) == []


# Deactivating and reactivating
@pytest.mark.django_db
def test_admin_deactivates_and_reactivates(client):
    admin = AdminUserFactory()
    user = UserFactory()

    response = patch(client, admin, user, {'is_active': False})

    assert response.status_code == 200
    assert response.json()['is_active'] is False
    user.refresh_from_db()
    assert not user.is_active

    response = patch(client, admin, user, {'is_active': True})

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_active


@pytest.mark.django_db
def test_admin_cannot_deactivate_self(client):
    admin = AdminUserFactory()

    response = patch(client, admin, admin, {'is_active': False})

    assert response.status_code == 400
    assert response.json() == {'is_active': ["You can't deactivate your own account."]}
    admin.refresh_from_db()
    assert admin.is_active


@pytest.mark.django_db
def test_other_fields_are_ignored(client):
    admin = AdminUserFactory()
    user = UserFactory(email='ada@example.com', first_name='Ada')

    response = patch(
        client,
        admin,
        user,
        {
            'email': 'changed@example.com',
            'first_name': 'Changed',
            'role': roles.ADMIN,
            'is_staff': True,
        },
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == 'ada@example.com'
    assert user.first_name == 'Ada'
    assert user.role.role_name == roles.STUDENT
    assert not user.is_staff


@pytest.mark.django_db
def test_unknown_user_is_404(client):
    admin = AdminUserFactory()
    gone = UserFactory()
    url = detail_url(gone)
    gone.delete()

    response = client.patch(
        url, {'is_active': False}, content_type='application/json', **auth(login(client, admin))
    )

    assert response.status_code == 404


# A deactivated user's tokens
@pytest.mark.django_db
def test_deactivation_stops_existing_tokens(client):
    admin = AdminUserFactory()
    user = UserFactory()
    tokens = login(client, user)

    patch(client, admin, user, {'is_active': False})

    assert client.get('/api/auth/me/', **auth(tokens)).status_code == 401
    response = client.post(
        '/api/auth/refresh/', {'refresh': tokens['refresh']}, content_type='application/json'
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_reactivation_does_not_revive_old_refresh_token(client):
    admin = AdminUserFactory()
    user = UserFactory()
    tokens = login(client, user)

    patch(client, admin, user, {'is_active': False})
    patch(client, admin, user, {'is_active': True})

    response = client.post(
        '/api/auth/refresh/', {'refresh': tokens['refresh']}, content_type='application/json'
    )
    assert response.status_code == 401
    assert login(client, user)['access']
