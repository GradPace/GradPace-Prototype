"""Production settings. Everything comes from the environment."""

from config.settings import get_secret

from .base import *

SECRET_KEY = get_secret('SECRET_KEY')

DEBUG = False

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
        # thread-local) - with 3 backend replicas x 4 threads, that's at most
        # 12 concurrent connections, well under Postgres's default
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
        'HOST': get_secret('EMAIL_HOST', 'mail'),
        'PORT': int(get_secret('EMAIL_PORT', 25)),
        'USERNAME': get_secret('EMAIL_HOST_USER', ''),
        'PASSWORD': get_secret('EMAIL_HOST_PASSWORD', ''),
        'USE_TLS': get_secret('EMAIL_USE_TLS', '') == '1',
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
