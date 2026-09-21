import pytest

from ..factories import CertificateFactory, StudentProfileFactory, UserFactory
from ..models import Certificate
from .helpers import login


def make_certificate_payload(**overrides):
    payload = {
        'name': 'AWS Certified Cloud Practitioner',
        'issuing_organization': 'Amazon Web Services',
        'date_earned': '2025-01-15',
        'credential_url': 'https://example.com/credential/123',
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_list_requires_authentication(client):
    response = client.get('/api/auth/profile/certificates/')

    assert response.status_code == 401


@pytest.mark.django_db
def test_create_requires_authentication(client):
    response = client.post(
        '/api/auth/profile/certificates/',
        make_certificate_payload(),
        content_type='application/json',
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_create_requires_a_profile(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        '/api/auth/profile/certificates/',
        make_certificate_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_create_succeeds_and_is_scoped_to_the_caller(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = client.post(
        '/api/auth/profile/certificates/',
        make_certificate_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 201
    body = response.json()
    assert body['name'] == 'AWS Certified Cloud Practitioner'
    assert body['issuing_organization'] == 'Amazon Web Services'
    assert body['date_earned'] == '2025-01-15'
    assert body['credential_url'] == 'https://example.com/credential/123'

    certificate = Certificate.objects.get(id=body['id'])
    assert certificate.student == profile


@pytest.mark.django_db
def test_list_only_returns_the_callers_own_certificates(client):
    profile = StudentProfileFactory()
    other_profile = StudentProfileFactory()
    CertificateFactory(student=profile, name='Mine')
    CertificateFactory(student=other_profile, name='Not mine')
    tokens = login(client, profile.user)

    response = client.get(
        '/api/auth/profile/certificates/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    names = [entry['name'] for entry in response.json()]
    assert names == ['Mine']


@pytest.mark.django_db
def test_retrieve_another_users_certificate_is_404(client):
    profile = StudentProfileFactory()
    other_certificate = CertificateFactory()
    tokens = login(client, profile.user)

    response = client.get(
        f'/api/auth/profile/certificates/{other_certificate.id}/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_update_only_changes_given_fields(client):
    profile = StudentProfileFactory()
    certificate = CertificateFactory(student=profile, name='Old name')
    tokens = login(client, profile.user)

    response = client.patch(
        f'/api/auth/profile/certificates/{certificate.id}/',
        {'name': 'New name'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    body = response.json()
    assert body['name'] == 'New name'
    assert body['issuing_organization'] == certificate.issuing_organization


@pytest.mark.django_db
def test_update_another_users_certificate_is_404(client):
    profile = StudentProfileFactory()
    other_certificate = CertificateFactory()
    tokens = login(client, profile.user)

    response = client.patch(
        f'/api/auth/profile/certificates/{other_certificate.id}/',
        {'name': 'New name'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_removes_the_certificate(client):
    profile = StudentProfileFactory()
    certificate = CertificateFactory(student=profile)
    tokens = login(client, profile.user)

    response = client.delete(
        f'/api/auth/profile/certificates/{certificate.id}/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 204
    assert not Certificate.objects.filter(id=certificate.id).exists()


@pytest.mark.django_db
def test_delete_another_users_certificate_is_404(client):
    profile = StudentProfileFactory()
    other_certificate = CertificateFactory()
    tokens = login(client, profile.user)

    response = client.delete(
        f'/api/auth/profile/certificates/{other_certificate.id}/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404
    assert Certificate.objects.filter(id=other_certificate.id).exists()
