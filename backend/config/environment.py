"""Verification profiles never read local credentials."""

import os
import secrets
from pathlib import Path

from decouple import Config, RepositoryEnv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
VERIFY = os.environ.get("DJANGO_SETTINGS_MODULE") in {
    "config.settings.test",
    "config.settings.production_check",
}
config = Config(
    {
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
        "DJANGO_ALLOWED_HOSTS": "testserver,api.example.invalid",
        "CORS_ALLOWED_ORIGINS": "https://frontend.example.invalid",
        "CSRF_TRUSTED_ORIGINS": "https://frontend.example.invalid",
        "HSTS_INCLUDE_SUBDOMAINS": "True",
        "HSTS_PRELOAD": "True",
        "DB_NAME": "unused",
        "DB_USER": "unused",
        "DB_PASSWORD": secrets.token_urlsafe(32),
        "DB_HOST": "localhost",
    }
    if VERIFY
    else RepositoryEnv(str(BASE_DIR / ".env"))
    if (BASE_DIR / ".env").exists()
    else {}
)


def required(name):
    value = config(name, default="").strip()
    if not value or value.startswith("<"):
        raise ImproperlyConfigured(f"{name} must be configured.")
    return value


def csv(name, default=""):
    return [p.strip() for p in config(name, default=default).split(",") if p.strip()]
