import secrets

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or secrets.token_urlsafe(64)  # noqa: F405
ALLOWED_HOSTS = csv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")  # noqa: F405
API_DOCS_ENABLED = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
