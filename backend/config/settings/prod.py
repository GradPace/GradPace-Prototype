"""Production settings. Everything comes from the environment."""

from django.core.exceptions import ImproperlyConfigured

from config.settings import get_secret

from .base import *

SECRET_KEY = get_secret('SECRET_KEY')

DEBUG = False

# Cloudflare Turnstile on login/register (accounts/turnstile.py). Refuse to
# start rather than serve with it misconfigured: a missing secret would fail
# every login, and one of Cloudflare's testing secrets (1x.../2x.../3x...
# followed by zeros, see dev.py) would let every bot through.
TURNSTILE_ENABLED = True
TURNSTILE_SECRET_KEY = get_secret('TURNSTILE_SECRET_KEY')
if not TURNSTILE_SECRET_KEY:
    raise ImproperlyConfigured('TURNSTILE_SECRET_KEY is not set.')
if TURNSTILE_SECRET_KEY[1:].startswith('x00000000'):
    raise ImproperlyConfigured('TURNSTILE_SECRET_KEY is a Cloudflare testing key.')

raw_hosts = get_secret('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(',') if host.strip()]

# Originally for docker-compose.prod.yml's internal healthcheck (now
# removed - k8s/backend-deployment.yaml's readiness/liveness probes
# override the Host header instead of relying on this, see its comments).
# Left in since 'localhost' is only ever reachable from inside the pod
# itself anyway, so it doesn't widen what's actually exposed either way.
ALLOWED_HOSTS.append('localhost')


# Static files - serve the staff-only Django admin's assets straight from
# gunicorn via WhiteNoise (compressed + hashed). The API itself serves none.
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
    'whitenoise.middleware.WhiteNoiseMiddleware',
)

# Compress API responses. Must be near the top, per Django docs - it needs to
# run last on the way out (closest to the client) so it compresses the final
# response body after every other middleware has already touched it. Prod
# only: no real benefit in dev/test, and keeps it out of base.py.
MIDDLEWARE.insert(0, 'django.middleware.gzip.GZipMiddleware')

# JSON only - no browsable API in prod. DRF's default renderers include
# BrowsableAPIRenderer, which serves a full HTML page to any browser and lets
# anyone click through the whole API. Dev keeps it for poking around locally.
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = ['rest_framework.renderers.JSONRenderer']

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}


# Database - GradPace gets its own dedicated Postgres, not a shared one.
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': f'django.db.backends.{get_secret("DATABASE_ENGINE", "postgresql")}',
        'NAME': get_secret('DATABASE_NAME', 'gradpace_db'),
        'USER': get_secret('DATABASE_USERNAME', 'gradpace'),
        'PASSWORD': get_secret('DATABASE_PASSWORD', ''),
        'HOST': get_secret('DATABASE_HOST', 'db'),
        'PORT': get_secret('DATABASE_PORT', 5432),
        # Reuse connections across requests instead of opening a new one each
        # time. Each Gunicorn thread holds its own (Django's DB connection is
        # thread-local) - with up to 6 backend replicas (k8s/backend-hpa.yaml)
        # x 4 threads, that's at most 24 concurrent connections, well under
        # Postgres's default
        # max_connections (100). 5 minutes keeps connections warm across the
        # idle gaps between requests at this traffic level; CONN_HEALTH_CHECKS
        # guards against a connection going stale during that window (e.g. a
        # Postgres restart or network blip) by validating it before reuse.
        'CONN_MAX_AGE': int(get_secret('DATABASE_CONN_MAX_AGE', 300)),
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'client_encoding': 'UTF8',
        },
    }
}


# Security - behind an HTTPS-terminating reverse proxy.

SECURE_SSL_REDIRECT = True
# k8s/backend-deployment.yaml's readiness/liveness probes hit this path
# over plain HTTP from inside the pod, where nothing terminates TLS -
# without this it 301s to https, which then fails to connect, so k8s sees
# it as unhealthy even though the app is fine.
SECURE_REDIRECT_EXEMPT = [r'^core/healthcheck/$']
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

csrf_origins = str(
    get_secret('CSRF_TRUSTED_ORIGINS', 'https://gradpace.steyaert.xyz')
    or 'https://gradpace.steyaert.xyz'
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_origins.split(',') if o.strip()]

# Unlike dev.py, this was never set here - django-cors-headers defaults
# CORS_ALLOWED_ORIGINS to an empty list, so every cross-origin request from
# the production frontend was silently rejected by the browser.
cors_origins = str(
    get_secret('CORS_ALLOWED_ORIGINS', 'https://gradpace.steyaert.xyz')
    or 'https://gradpace.steyaert.xyz'
)
CORS_ALLOWED_ORIGINS = [o.strip() for o in cors_origins.split(',') if o.strip()]


MAILERS = {
    'default': {
        'BACKEND': get_secret('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'),
        'OPTIONS': {
            'host': get_secret('EMAIL_HOST', 'mail'),
            'port': int(get_secret('EMAIL_PORT', 25)),
            'username': get_secret('EMAIL_HOST_USER', ''),
            'password': get_secret('EMAIL_HOST_PASSWORD', ''),
            'use_tls': get_secret('EMAIL_USE_TLS', '') == '1',
            # Seconds. Without one, a hung mail server blocks the sending
            # thread forever (see accounts/mail.py).
            'timeout': 10,
        },
    },
}
DEFAULT_FROM_EMAIL = get_secret('DEFAULT_FROM_EMAIL', 'noreply@gradpace.steyaert.xyz')

# Where accounts.views.PasswordResetRequestView points the reset link.
FRONTEND_URL = get_secret('FRONTEND_URL', 'https://gradpace.steyaert.xyz')


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'ERROR'},
    },
}
