"""Settings for the test suite (PIPELINE=test)."""

from .base import *

DEBUG = False
SECRET_KEY = 'django-insecure-test-key-not-a-secret'
ALLOWED_HOSTS = ['*']

# In-memory database - fast, discarded after the run.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Fast, insecure hashing - fine for tests only.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# accounts.validators.PwnedPasswordValidator - never make the suite depend on
# network access / a third-party API's availability.
PWNED_PASSWORDS_CHECK_ENABLED = False

# Same reason - accounts/tests/test_turnstile.py turns it back on per test
# with Cloudflare's siteverify response mocked.
TURNSTILE_ENABLED = False

# In-memory mailer - sent messages land in django.core.mail.outbox for asserts.
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
    },
}

FRONTEND_URL = 'http://localhost:3000'
