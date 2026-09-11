import pytest
from django.contrib.auth import get_user_model

from .factories import UserFactory

User = get_user_model()

PASSWORD = "correct-horse-battery-staple"


@pytest.mark.django_db
def test_register_creates_a_user_and_returns_tokens(client):
    response = client.post(
        "/api/auth/register/",
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": PASSWORD,
            "password_confirm": PASSWORD,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert "access" in body
    assert "refresh" in body

    user = User.objects.get(username="newuser")
    assert user.check_password(PASSWORD)


@pytest.mark.django_db
def test_register_rejects_duplicate_username(client):
    UserFactory(username="taken")

    response = client.post(
        "/api/auth/register/",
        {
            "username": "taken",
            "email": "someone-else@example.com",
            "password": PASSWORD,
            "password_confirm": PASSWORD,
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "username" in response.json()


@pytest.mark.django_db
def test_register_rejects_mismatched_passwords(client):
    response = client.post(
        "/api/auth/register/",
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": PASSWORD,
            "password_confirm": "something-else",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "password_confirm" in response.json()


@pytest.mark.django_db
def test_register_rejects_a_weak_password(client):
    response = client.post(
        "/api/auth/register/",
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "12345678",
            "password_confirm": "12345678",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "password" in response.json()


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
