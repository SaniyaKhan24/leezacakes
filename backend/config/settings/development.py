import secrets
from decimal import Decimal

from config.environment import BASE_DIR, config, csv

from .base import *  # noqa: F403
from .base import DEV_USE_SQLITE, ORDER_TAX_POLICY_CONFIGURED, REST_FRAMEWORK, SECRET_KEY

DEBUG = True
SECRET_KEY = SECRET_KEY or secrets.token_urlsafe(64)
ALLOWED_HOSTS = csv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
API_DOCS_ENABLED = True

# DEV_USE_SQLITE=True runs the stack against a local file database instead of
# Supabase PostgreSQL. It is read only here; other settings modules ignore it.
if DEV_USE_SQLITE:
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }

# Transactional emails (verification and reset links) are printed to the runserver console.
EMAIL_BACKEND = config(
    "DEV_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000").strip().rstrip("/")
CORS_ALLOWED_ORIGINS = csv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = csv("CSRF_TRUSTED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
# Local development commonly repeats registration while testing verification and
# duplicate-account handling. Keep throttling enabled, but avoid locking the
# whole developer IP after five attempts. Production keeps the base 5/hour rate.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].update(
    {
        "register": config("DEV_REGISTER_THROTTLE_RATE", "20/hour"),
        "login": config("DEV_LOGIN_THROTTLE_RATE", "20/min"),
    }
)

# Development tax default: catalogue prices are GST-inclusive, so no tax is added.
if not ORDER_TAX_POLICY_CONFIGURED:
    ORDER_TAX_POLICY_CONFIGURED = True
    ORDER_TAX_RATE = Decimal("0")
ORDER_PRICES_INCLUDE_TAX = config("ORDER_PRICES_INCLUDE_TAX", default=True, cast=bool)


def _env_or_sample(name, sample):
    """Use a configured value; an unset or blank variable falls back to the sample."""
    return config(name, default="").strip() or sample


# Sample UPI details. The default ID is deliberately not a real PSP handle.
_upi_from_env = bool(config("PAYMENT_UPI_ID", default="").strip())
PAYMENT_UPI_ID = _env_or_sample("PAYMENT_UPI_ID", "leezacakes.sample@example")
PAYMENT_UPI_PAYEE_NAME = _env_or_sample("PAYMENT_UPI_PAYEE_NAME", "Leeza Cakes")
PAYMENT_UPI_IS_SAMPLE = config("PAYMENT_UPI_IS_SAMPLE", default=not _upi_from_env, cast=bool)

# Clearly fake public contact details for local development. As soon as any real
# contact detail is configured, samples are not mixed in (unset values stay null).
_site_from_env = any(
    config(name, default="").strip()
    for name in (
        "SITE_CONTACT_PHONE",
        "SITE_CONTACT_EMAIL",
        "SITE_WHATSAPP",
        "SITE_INSTAGRAM",
        "SITE_ADDRESS",
        "SITE_PICKUP_HOURS_LABEL",
    )
)
if not _site_from_env:
    SITE_CONTACT_PHONE = "+91 90000 00000"
    SITE_CONTACT_EMAIL = "hello@leezacakes.example"
    SITE_WHATSAPP = "+91 90000 00000"
    SITE_ADDRESS = "Sample Studio Address, Bengaluru"
    SITE_PICKUP_HOURS_LABEL = "Pickup daily, 10 am to 8 pm (sample hours)"
SITE_CONTENT_IS_SAMPLE = config("SITE_CONTENT_IS_SAMPLE", default=not _site_from_env, cast=bool)
