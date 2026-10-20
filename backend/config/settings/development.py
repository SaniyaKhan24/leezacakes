import secrets

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = SECRET_KEY or secrets.token_urlsafe(64)  # noqa: F405
ALLOWED_HOSTS = csv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")  # noqa: F405
API_DOCS_ENABLED = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CORS_ALLOWED_ORIGINS = csv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = csv(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)
# Local development commonly repeats registration while testing verification and
# duplicate-account handling. Keep throttling enabled, but avoid locking the
# whole developer IP after five attempts. Production keeps the base 5/hour rate.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].update(
    {
        "register": config("DEV_REGISTER_THROTTLE_RATE", "20/hour"),
        "login": config("DEV_LOGIN_THROTTLE_RATE", "20/min"),
    }
)
