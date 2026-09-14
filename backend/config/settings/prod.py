"""Production settings. Everything comes from the environment."""

from config.settings import get_secret

from .base import *

SECRET_KEY = get_secret('SECRET_KEY')

DEBUG = False

raw_hosts = get_secret('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(',') if host.strip()]

# docker-compose.prod.yml's healthcheck hits localhost:8000 from inside the
# container - only reachable there, never from the internet, so allowing it
# unconditionally doesn't widen what's actually exposed.
ALLOWED_HOSTS.append('localhost')


# Static files - serve the staff-only Django admin's assets straight from
# gunicorn via WhiteNoise (compressed + hashed). The API itself serves none.
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
    'whitenoise.middleware.WhiteNoiseMiddleware',
)

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
        'OPTIONS': {
            'client_encoding': 'UTF8',
        },
    }
}


# Security - behind an HTTPS-terminating reverse proxy.

SECURE_SSL_REDIRECT = True
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
