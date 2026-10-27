import io
import json
import urllib.error
from unittest import mock

import pytest
from django.core.cache import cache

from accounts.factories import UserFactory
from accounts.tests.helpers import login

SUGGESTIONS = {
    'suggestions': [
        {'event': 'Fall Career Fair', 'reason': 'Meet recruiters hiring interns.'},
        {'event': 'Hackathon', 'reason': 'Build a project to show employers.'},
    ]
}


def auth_header(client):
    tokens = login(client, UserFactory())
    return {'HTTP_AUTHORIZATION': f'Bearer {tokens["access"]}'}


def model_replies(content):
    """Patches intelligence.llm's urlopen to answer like llama-server, with
    `content` as the assistant message - returns the mock, so tests can
    inspect what was sent."""
    completion = {'choices': [{'message': {'role': 'assistant', 'content': content}}]}
    return mock.patch(
        'intelligence.llm.urllib.request.urlopen',
        return_value=io.BytesIO(json.dumps(completion).encode()),
    )


def sent_body(urlopen_mock):
    request = urlopen_mock.call_args.args[0]
    return json.loads(request.data)


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    # The llm throttle counts live in the cache, which outlives each test.
    cache.clear()


@pytest.mark.django_db
def test_sample_requires_authentication(client):
    response = client.get('/api/intelligence/events/sample/')

    assert response.status_code == 401


@pytest.mark.django_db
def test_sample_returns_the_models_suggestions(client):
    with model_replies(json.dumps(SUGGESTIONS)):
        response = client.get('/api/intelligence/events/sample/', **auth_header(client))

    assert response.status_code == 200
    assert response.json() == SUGGESTIONS


@pytest.mark.django_db
def test_sample_asks_for_schema_constrained_json_with_thinking_off(client, settings):
    settings.LLAMA_CPP_BASE_URL = 'http://llama.test:8080'

    with model_replies(json.dumps(SUGGESTIONS)) as urlopen:
        client.get('/api/intelligence/events/sample/', **auth_header(client))

    request = urlopen.call_args.args[0]
    assert request.full_url == 'http://llama.test:8080/v1/chat/completions'
    body = sent_body(urlopen)
    assert body['chat_template_kwargs'] == {'enable_thinking': False}
    assert body['response_format']['type'] == 'json_schema'


@pytest.mark.django_db
def test_sample_is_503_when_the_model_is_unreachable(client):
    with mock.patch(
        'intelligence.llm.urllib.request.urlopen',
        side_effect=urllib.error.URLError('connection refused'),
    ):
        response = client.get('/api/intelligence/events/sample/', **auth_header(client))

    assert response.status_code == 503


@pytest.mark.django_db
def test_sample_is_503_when_the_reply_is_not_json(client):
    with model_replies('Sure! Here are three events...'):
        response = client.get('/api/intelligence/events/sample/', **auth_header(client))

    assert response.status_code == 503


@pytest.mark.django_db
def test_sample_is_503_when_the_reply_has_the_wrong_shape(client):
    with model_replies(json.dumps({'events': ['Hackathon']})):
        response = client.get('/api/intelligence/events/sample/', **auth_header(client))

    assert response.status_code == 503
