"""Local development settings."""

from dotenv import load_dotenv

from .base import *  # noqa: F401,F403

load_dotenv(BASE_DIR / "config" / "settings" / ".env.dev")

DEBUG = True
ALLOWED_HOSTS = ["*"]
SECRET_KEY = "django-insecure-29g0%p31*!h%*7izn$yyh_4uk03r$mg3ez0_1i*hbh+u47x#hp"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}

# CORS_ALLOW_ALL_ORIGINS = True
