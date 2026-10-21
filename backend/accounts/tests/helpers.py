"""Shared test constants/helpers - not a conftest.py since there's no
fixture here, just plain values and a request helper."""

import threading

from ..mail import THREAD_NAME

PASSWORD = 'Zq7!fWbn2'  # satisfies AUTH_PASSWORD_VALIDATORS - see accounts/validators.py
NEW_PASSWORD = 'Xk7!Qp2vLr'


def login(client, user):
    response = client.post(
        '/api/auth/login/',
        {'email': user.email, 'password': PASSWORD},
        content_type='application/json',
    )
    return response.json()


def wait_for_emails():
    """accounts.mail.send_in_background sends on its own thread - join those
    before asserting on mail.outbox."""
    for thread in threading.enumerate():
        if thread.name == THREAD_NAME:
            thread.join(timeout=5)
