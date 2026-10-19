import re
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from config.environment import config, required

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS

DEBUG = False
SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be a strong random key of at least 50 characters."
    )
if not ALLOWED_HOSTS or any(
    not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", h) for h in ALLOWED_HOSTS
):
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must contain explicit hostnames.")
for name, origins in (
    ("CORS_ALLOWED_ORIGINS", CORS_ALLOWED_ORIGINS),
    ("CSRF_TRUSTED_ORIGINS", CSRF_TRUSTED_ORIGINS),
):
    if not origins:
        raise ImproperlyConfigured(f"{name} requires explicit HTTPS origins.")
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or "*" in origin
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
        ):
            raise ImproperlyConfigured(f"{name} requires explicit HTTPS origins without paths.")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("HSTS_INCLUDE_SUBDOMAINS", default=False, cast=bool)
SECURE_HSTS_PRELOAD = config("HSTS_PRELOAD", default=False, cast=bool)
SECURE_REFERRER_POLICY = "same-origin"
# Only behind a proxy that strips client-supplied forwarding headers.
if config("TRUST_PROXY_SSL_HEADER", default=False, cast=bool):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
