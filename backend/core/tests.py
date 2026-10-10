from unittest.mock import patch

from django.core.cache import cache
from drf_spectacular.generators import SchemaGenerator


def test_healthcheck_ok(client):
    """Liveness only - no DB hit, so this needs no @pytest.mark.django_db."""
    response = client.get('/core/healthcheck/')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_schema_is_cached_per_accept_header(client):
    """config/urls.py caches /api/schema/ outside DEBUG - the test settings
    have DEBUG off, so this exercises the prod path."""
    cache.clear()
    with patch(
        'drf_spectacular.generators.SchemaGenerator.get_schema',
        side_effect=SchemaGenerator.get_schema,
        autospec=True,
    ) as get_schema:
        yaml_response = client.get('/api/schema/')
        client.get('/api/schema/')
        json_response = client.get('/api/schema/', HTTP_ACCEPT='application/vnd.oai.openapi+json')

    assert yaml_response.status_code == 200
    assert 'max-age=3600' in yaml_response['Cache-Control']
    assert yaml_response['Content-Type'].startswith('application/vnd.oai.openapi;')
    assert 'json' in json_response['Content-Type']
    # Generated once per Accept value; the repeat YAML request is a cache hit.
    assert get_schema.call_count == 2
