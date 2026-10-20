from .base import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

DEBUG = False
API_DOCS_ENABLED = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
