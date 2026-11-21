"""GET /api/intelligence/places/ - the location autocomplete."""

import pytest

from accounts.factories import UserFactory
from accounts.tests.helpers import login

URL = '/api/intelligence/places/'


@pytest.fixture
def headers(client, db):
    return {'HTTP_AUTHORIZATION': f'Bearer {login(client, UserFactory())["access"]}'}


def test_requires_authentication(client):
    assert client.get(URL, {'q': 'nor'}).status_code == 401


def test_returns_matching_places_with_a_label_to_save(client, headers):
    response = client.get(URL, {'q': 'norfolk'}, **headers)

    assert response.status_code == 200
    assert {'label': 'Norfolk, VA', 'name': 'Norfolk', 'state': 'VA'} in response.json()


def test_a_comma_narrows_by_state(client, headers):
    response = client.get(URL, {'q': 'norfolk, v'}, **headers)

    assert [p['label'] for p in response.json()] == ['Norfolk, VA']


def test_is_capped_at_eight_results(client, headers):
    assert len(client.get(URL, {'q': 'sa'}, **headers).json()) == 8


@pytest.mark.parametrize('query', ['', 'n', 'zzzzqq'])
def test_short_or_unmatched_queries_return_an_empty_list(client, headers, query):
    response = client.get(URL, {'q': query}, **headers)

    assert response.status_code == 200
    assert response.json() == []


def test_a_missing_q_is_just_empty(client, headers):
    assert client.get(URL, **headers).json() == []


def test_a_huge_query_is_cut_not_crashed_on(client, headers):
    assert client.get(URL, {'q': 'a' * 5000}, **headers).status_code == 200
