def test_healthcheck_ok(client):
    """Liveness only - no DB hit, so this needs no @pytest.mark.django_db."""
    response = client.get("/core/healthcheck/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
