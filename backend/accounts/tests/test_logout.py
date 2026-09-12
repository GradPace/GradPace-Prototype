import pytest

from ..factories import UserFactory
from .helpers import login


@pytest.mark.django_db
def test_logout_blacklists_the_refresh_token(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        "/api/auth/logout/",
        {"refresh": tokens["refresh"]},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
    )
    assert response.status_code == 205

    # The now-blacklisted refresh token can no longer mint a new access token.
    refresh_response = client.post(
        "/api/auth/refresh/",
        {"refresh": tokens["refresh"]},
        content_type="application/json",
    )
    assert refresh_response.status_code == 401


@pytest.mark.django_db
def test_logout_requires_authentication(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        "/api/auth/logout/",
        {"refresh": tokens["refresh"]},
        content_type="application/json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_logout_requires_a_refresh_token(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        "/api/auth/logout/",
        {},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
    )

    assert response.status_code == 400
    assert "refresh" in response.json()


@pytest.mark.django_db
def test_logout_rejects_an_invalid_refresh_token(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        "/api/auth/logout/",
        {"refresh": "not-a-real-token"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
    )

    assert response.status_code == 400
    assert "refresh" in response.json()
