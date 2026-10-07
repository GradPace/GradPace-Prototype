import pytest

from accounts.factories import UserFactory
from accounts.tests.helpers import login


def auth_header(client):
    tokens = login(client, UserFactory())
    return {'HTTP_AUTHORIZATION': f'Bearer {tokens["access"]}'}


@pytest.mark.django_db
def test_calculate_requires_authentication(client):
    response = client.post('/api/benchmark/calculate/', {}, content_type='application/json')

    assert response.status_code == 401


@pytest.mark.django_db
def test_calculate_returns_score_and_gaps(client):
    response = client.post(
        '/api/benchmark/calculate/',
        {
            'student_profile': {'skills': 80.0, 'experience': 70.0},
            'dynamic_weights': {'skills': 0.5, 'experience': 0.5},
        },
        content_type='application/json',
        **auth_header(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body['overall_readiness_score'] == 75.0
    assert body['gap_breakdown']['skills'] == {'current': 80.0, 'weight': 0.5, 'gap': 20.0}


@pytest.mark.django_db
def test_calculate_rejects_non_numeric_values(client):
    response = client.post(
        '/api/benchmark/calculate/',
        {'student_profile': {'skills': 'lots'}, 'dynamic_weights': {'skills': 1.0}},
        content_type='application/json',
        **auth_header(client),
    )

    assert response.status_code == 400
    assert 'student_profile' in response.json()


@pytest.mark.django_db
def test_calculate_rejects_get(client):
    response = client.get('/api/benchmark/calculate/', **auth_header(client))

    assert response.status_code == 405


@pytest.mark.django_db
def test_sample_returns_result(client):
    response = client.get('/api/benchmark/sample/', **auth_header(client))

    assert response.status_code == 200
    assert response.json()['overall_readiness_score'] == 70.0
