import pytest

from ..factories import UserFactory
from ..models import StudentProfile
from .helpers import login


def make_profile_payload(**overrides):
    payload = {
        'student_id': 'S1234567',
        'first_name': 'Ada',
        'last_name': 'Lovelace',
        'major': 'Computer Science',
        'uni': 'State University',
        'location': 'Springfield',
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_profile_get_requires_authentication(client):
    response = client.get('/api/auth/profile/')

    assert response.status_code == 401


@pytest.mark.django_db
def test_profile_get_is_404_before_creation(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.get(
        '/api/auth/profile/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_profile_create_succeeds_and_sets_fields(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        '/api/auth/profile/',
        make_profile_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 201
    body = response.json()
    assert body['student_id'] == 'S1234567'
    assert body['first_name'] == 'Ada'
    assert body['last_name'] == 'Lovelace'
    assert body['major'] == 'Computer Science'
    assert body['uni'] == 'State University'
    assert body['location'] == 'Springfield'
    assert body['graduated'] is False
    assert body['readiness_score'] is None

    profile = StudentProfile.objects.get(user=user)
    assert profile.student_id == 'S1234567'
    user.refresh_from_db()
    assert user.first_name == 'Ada'
    assert user.last_name == 'Lovelace'


@pytest.mark.django_db
def test_profile_create_requires_authentication(client):
    response = client.post(
        '/api/auth/profile/',
        make_profile_payload(),
        content_type='application/json',
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_profile_create_rejects_a_second_profile_for_the_same_user(client):
    user = UserFactory()
    tokens = login(client, user)
    client.post(
        '/api/auth/profile/',
        make_profile_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    response = client.post(
        '/api/auth/profile/',
        make_profile_payload(student_id='S7654321'),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 400
    assert StudentProfile.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_profile_create_rejects_a_duplicate_student_id(client):
    other = UserFactory()
    StudentProfile.objects.create(
        user=other, student_id='S1234567', major='Biology', uni='Other University'
    )

    user = UserFactory()
    tokens = login(client, user)
    response = client.post(
        '/api/auth/profile/',
        make_profile_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 400
    assert 'student_id' in response.json()


@pytest.mark.django_db
def test_profile_get_returns_the_caller_profile_after_creation(client):
    user = UserFactory()
    tokens = login(client, user)
    client.post(
        '/api/auth/profile/',
        make_profile_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    response = client.get(
        '/api/auth/profile/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    assert response.json()['student_id'] == 'S1234567'


@pytest.mark.django_db
def test_profile_patch_updates_mutable_fields(client):
    user = UserFactory()
    tokens = login(client, user)
    client.post(
        '/api/auth/profile/',
        make_profile_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    response = client.patch(
        '/api/auth/profile/',
        {'major': 'Physics', 'graduated': True},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    body = response.json()
    assert body['major'] == 'Physics'
    assert body['graduated'] is True
    # Untouched fields survive a partial update.
    assert body['student_id'] == 'S1234567'
    assert body['uni'] == 'State University'


@pytest.mark.django_db
def test_profile_patch_ignores_student_id(client):
    user = UserFactory()
    tokens = login(client, user)
    client.post(
        '/api/auth/profile/',
        make_profile_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    response = client.patch(
        '/api/auth/profile/',
        {'student_id': 'S0000000'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    assert response.json()['student_id'] == 'S1234567'


@pytest.mark.django_db
def test_profile_patch_ignores_readiness_score(client):
    """readiness_score is computed, not self-reported - not accepted here."""
    user = UserFactory()
    tokens = login(client, user)
    client.post(
        '/api/auth/profile/',
        make_profile_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    response = client.patch(
        '/api/auth/profile/',
        {'readiness_score': 99.9},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    assert response.json()['readiness_score'] is None


@pytest.mark.django_db
def test_profile_patch_is_404_before_creation(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.patch(
        '/api/auth/profile/',
        {'major': 'Physics'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_profile_patch_requires_authentication(client):
    response = client.patch(
        '/api/auth/profile/',
        {'major': 'Physics'},
        content_type='application/json',
    )

    assert response.status_code == 401
