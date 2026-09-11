import pytest

from .factories import UserFactory

PASSWORD = "correct-horse-battery-staple"


@pytest.mark.django_db
def test_login_returns_access_and_refresh_tokens(client):
    user = UserFactory()

    response = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": PASSWORD},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert "access" in body
    assert "refresh" in body


@pytest.mark.django_db
def test_login_rejects_bad_password(client):
    user = UserFactory()

    response = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "wrong-password"},
        content_type="application/json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_me_requires_a_token(client):
    response = client.get("/api/auth/me/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_the_authenticated_user(client):
    user = UserFactory()
    login = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": PASSWORD},
        content_type="application/json",
    )
    access_token = login.json()["access"]

    response = client.get(
        "/api/auth/me/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 200
    assert response.json()["username"] == user.username


@pytest.mark.django_db
def test_refresh_issues_a_new_access_token(client):
    user = UserFactory()
    login = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": PASSWORD},
        content_type="application/json",
    )
    refresh_token = login.json()["refresh"]

    response = client.post(
        "/api/auth/refresh/",
        {"refresh": refresh_token},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "access" in response.json()
