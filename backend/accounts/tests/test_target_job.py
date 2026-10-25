"""StudentProfile.target_job via /api/auth/profile/ - the job a student is
working toward, which the readiness score is measured against.

The intelligence app's migrations seed the 24 BLS jobs, so the test database
already has e.g. Software Developers (15-1252) and Data Scientists (15-2051).
"""

import pytest

from accounts.factories import StudentProfileFactory, UserFactory

from .helpers import login


def auth_header(client, user):
    tokens = login(client, user)
    return {'HTTP_AUTHORIZATION': f'Bearer {tokens["access"]}'}


@pytest.mark.django_db
def test_profile_shows_no_target_job_by_default(client):
    profile = StudentProfileFactory()
    body = client.get('/api/auth/profile/', **auth_header(client, profile.user)).json()

    assert body['target_job'] is None
    assert body['target_job_title'] is None


@pytest.mark.django_db
def test_target_job_can_be_set_on_create(client):
    user = UserFactory()

    response = client.post(
        '/api/auth/profile/',
        {'student_id': 'S7654321', 'major': 'CS', 'uni': 'ODU', 'target_job': '15-1252'},
        content_type='application/json',
        **auth_header(client, user),
    )

    assert response.status_code == 201
    assert response.json()['target_job'] == '15-1252'
    assert response.json()['target_job_title'] == 'Software Developers'


@pytest.mark.django_db
def test_target_job_can_be_changed_and_cleared_with_patch(client):
    profile = StudentProfileFactory()
    headers = auth_header(client, profile.user)

    set_it = client.patch(
        '/api/auth/profile/', {'target_job': '15-2051'}, content_type='application/json', **headers
    )
    assert set_it.status_code == 200
    assert set_it.json()['target_job_title'] == 'Data Scientists'

    clear_it = client.patch(
        '/api/auth/profile/', {'target_job': None}, content_type='application/json', **headers
    )
    assert clear_it.json()['target_job'] is None


@pytest.mark.django_db
def test_unknown_target_job_is_rejected(client):
    profile = StudentProfileFactory()
    response = client.patch(
        '/api/auth/profile/',
        {'target_job': '99-9999'},
        content_type='application/json',
        **auth_header(client, profile.user),
    )

    assert response.status_code == 400
    assert 'target_job' in response.json()
