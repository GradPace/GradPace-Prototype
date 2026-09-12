"""Shared test constants/helpers - not a conftest.py since there's no
fixture here, just plain values and a request helper."""

PASSWORD = "Zq7!fWbn2"  # satisfies AUTH_PASSWORD_VALIDATORS - see accounts/validators.py
NEW_PASSWORD = "Xk7!Qp2vLr"


def login(client, user):
    response = client.post(
        "/api/auth/login/",
        {"username": user.username, "password": PASSWORD},
        content_type="application/json",
    )
    return response.json()
