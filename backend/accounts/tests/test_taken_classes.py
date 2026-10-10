import pytest

from ..factories import StudentProfileFactory, TakenClassFactory, UserFactory
from ..models import TakenClass
from .helpers import login


def make_class_payload(**overrides):
    payload = {
        'course_code': 'CS411',
        'course_name': 'Software Engineering',
        'semester': 'fall',
        'year': 2025,
        'grade': 'A',
        'credits': 3,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_list_requires_authentication(client):
    response = client.get('/api/auth/profile/classes/')

    assert response.status_code == 401


@pytest.mark.django_db
def test_create_requires_authentication(client):
    response = client.post(
        '/api/auth/profile/classes/',
        make_class_payload(),
        content_type='application/json',
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_create_requires_a_profile(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        '/api/auth/profile/classes/',
        make_class_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_create_succeeds_and_is_scoped_to_the_caller(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = client.post(
        '/api/auth/profile/classes/',
        make_class_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 201
    body = response.json()
    assert body['course_code'] == 'CS411'
    assert body['course_name'] == 'Software Engineering'
    assert body['semester'] == 'fall'
    assert body['year'] == 2025
    assert body['grade'] == 'A'
    assert body['credits'] == 3

    taken_class = TakenClass.objects.get(id=body['id'])
    assert taken_class.student == profile


@pytest.mark.django_db
def test_list_only_returns_the_callers_own_classes(client):
    profile = StudentProfileFactory()
    other_profile = StudentProfileFactory()
    TakenClassFactory(student=profile, course_code='CS101')
    TakenClassFactory(student=other_profile, course_code='CS999')
    tokens = login(client, profile.user)

    response = client.get(
        '/api/auth/profile/classes/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    course_codes = [entry['course_code'] for entry in response.json()['results']]
    assert course_codes == ['CS101']


@pytest.mark.django_db
def test_retrieve_another_users_class_is_404(client):
    profile = StudentProfileFactory()
    other_class = TakenClassFactory()
    tokens = login(client, profile.user)

    response = client.get(
        f'/api/auth/profile/classes/{other_class.id}/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_update_only_changes_given_fields(client):
    profile = StudentProfileFactory()
    taken_class = TakenClassFactory(student=profile, grade='B')
    tokens = login(client, profile.user)

    response = client.patch(
        f'/api/auth/profile/classes/{taken_class.id}/',
        {'grade': 'A'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    body = response.json()
    assert body['grade'] == 'A'
    assert body['course_code'] == taken_class.course_code


@pytest.mark.django_db
def test_update_another_users_class_is_404(client):
    profile = StudentProfileFactory()
    other_class = TakenClassFactory()
    tokens = login(client, profile.user)

    response = client.patch(
        f'/api/auth/profile/classes/{other_class.id}/',
        {'grade': 'A'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_removes_the_class(client):
    profile = StudentProfileFactory()
    taken_class = TakenClassFactory(student=profile)
    tokens = login(client, profile.user)

    response = client.delete(
        f'/api/auth/profile/classes/{taken_class.id}/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 204
    assert not TakenClass.objects.filter(id=taken_class.id).exists()


@pytest.mark.django_db
def test_delete_another_users_class_is_404(client):
    profile = StudentProfileFactory()
    other_class = TakenClassFactory()
    tokens = login(client, profile.user)

    response = client.delete(
        f'/api/auth/profile/classes/{other_class.id}/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404
    assert TakenClass.objects.filter(id=other_class.id).exists()
