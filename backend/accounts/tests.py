import pytest
from django.contrib.auth import get_user_model

from .factories import UserFactory

User = get_user_model()

PASSWORD = "Zq7!fWbn2"  # satisfies AUTH_PASSWORD_VALIDATORS - see accounts/validators.py


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
@pytest.mark.parametrize(
    "password",
    [
        pytest.param("Ab1!ab1", id="too-short"),
        pytest.param("str0ng!pass", id="no-uppercase"),
        pytest.param("Strong!Pass", id="no-number"),
        pytest.param("Str0ngPass", id="no-special-character"),
        pytest.param("Password1!", id="dictionary-word"),
        pytest.param("Passsss1!", id="repeated-characters"),
        pytest.param("Abcd1234!", id="sequential-characters"),
        pytest.param("password123", id="common-password"),
    ],
)
def test_register_rejects_a_weak_password(client, password):
    response = client.post(
        "/api/auth/register/",
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": password,
            "password_confirm": password,
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


def _login(client, user):
    response = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": PASSWORD},
        content_type="application/json",
    )
    return response.json()


@pytest.mark.django_db
def test_logout_blacklists_the_refresh_token(client):
    user = UserFactory()
    tokens = _login(client, user)

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
    tokens = _login(client, user)

    response = client.post(
        "/api/auth/logout/",
        {"refresh": tokens["refresh"]},
        content_type="application/json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_logout_requires_a_refresh_token(client):
    user = UserFactory()
    tokens = _login(client, user)

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
    tokens = _login(client, user)

    response = client.post(
        "/api/auth/logout/",
        {"refresh": "not-a-real-token"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
    )

    assert response.status_code == 400
    assert "refresh" in response.json()
