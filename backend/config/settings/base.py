"""
Shared settings for every environment.

The environment-specific modules (dev, prod, test) do ``from .base import *``
and override what they need. ``config/settings/__init__.py`` picks which one to
load based on the ``PIPELINE`` env var.
"""

from datetime import timedelta
from pathlib import Path

from config.settings import get_secret

# backend/config/settings/base.py -> backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# llama.cpp's llama-server (intelligence/llm.py). The default is the `llama`
# Service in k8s (k8s/llama-deployment.yaml) and the `llama` service in
# docker-compose.dev.yml - both resolve the same name on their own network.
LLAMA_CPP_BASE_URL = get_secret('LLAMA_CPP_BASE_URL', 'http://llama:8080').rstrip('/')
# Seconds. CPU inference: a short JSON answer takes a few seconds, but the
# single slot may already be busy with another request.
LLAMA_CPP_TIMEOUT = 30


# Application definition

INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'encrypted_fields',
    'core',
    'accounts',
    'benchmarks',
    'intelligence',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

PASSWORD_RESET_TIMEOUT = 60 * 10

# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'accounts.validators.UppercaseValidator'},
    {'NAME': 'accounts.validators.NumberValidator'},
    {'NAME': 'accounts.validators.SpecialCharacterValidator'},
    {'NAME': 'accounts.validators.NoDictionaryWordValidator'},
    {'NAME': 'accounts.validators.NoRepeatedOrSequentialValidator'},
    {'NAME': 'accounts.validators.PwnedPasswordValidator'},
]

# Have I Been Pwned check (accounts.validators.PwnedPasswordValidator) - off
# in config/settings/test.py so the test suite never depends on network access.
PWNED_PASSWORDS_CHECK_ENABLED = True


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_TZ = True


# Static files - the API serves none of its own, but the staff-only Django
# admin needs its CSS/JS. prod.py serves STATIC_ROOT via WhiteNoise.
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/6.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model - UUID pk, email login, no username.
# https://docs.djangoproject.com/en/6.1/topics/auth/customizing/#substituting-a-custom-user-model
AUTH_USER_MODEL = 'accounts.CustomUser'


# Django REST Framework

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # JSON request bodies only - no form-encoded/multipart parsing on every
    # endpoint. A view that takes a file upload opts back in per view with
    # `parser_classes = [MultiPartParser]`.
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Every list endpoint is paginated: {count, next, previous, results},
    # with ?limit=/?offset= to page through.
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
    # Per client IP, on the public auth endpoints (accounts/views.py,
    # accounts.throttling.AuthRateThrottle). Login/register/reset all hash a
    # password or send an email - cheap to request, expensive to serve.
    # `llm` is per user, on views that call the model (intelligence/views.py)
    # - it answers one request at a time on CPU.
    'DEFAULT_THROTTLE_RATES': {
        'login': '10/min',
        'register': '5/min',
        'refresh': '30/min',
        'password_reset': '5/hour',
        'llm': '10/min',
    },
}

# drf-spectacular - generates the OpenAPI schema from the views/serializers
# above (config/urls.py: /api/schema/ raw schema, /api/docs/ Swagger UI).
# https://drf-spectacular.readthedocs.io/en/latest/settings.html
SPECTACULAR_SETTINGS = {
    'TITLE': 'GradPace API',
    'DESCRIPTION': 'Backend API for GradPace - Team Copper.',
    'VERSION': '0.5.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# djangorestframework-simplejwt
# https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
