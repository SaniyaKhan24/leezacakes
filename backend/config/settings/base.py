import os
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ImproperlyConfigured

from config.environment import BASE_DIR, VERIFY, config, csv, required

SECRET_KEY = config("DJANGO_SECRET_KEY", default="")
DEBUG = False
ALLOWED_HOSTS = csv("DJANGO_ALLOWED_HOSTS")
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    *[
        f"apps.{name}"
        for name in (
            "accounts",
            "cart",
            "catalog",
            "common",
            "customization",
            "notifications",
            "orders",
            "payments",
            "search",
            "enquiries",
        )
    ],
]
AUTH_USER_MODEL = "accounts.User"
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.CorrelationIdMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
# DEV_USE_SQLITE is honoured only by config.settings.development (see that module).
# Every other settings module keeps PostgreSQL mandatory with no silent fallback.
DEV_USE_SQLITE = os.environ.get(
    "DJANGO_SETTINGS_MODULE"
) == "config.settings.development" and config("DEV_USE_SQLITE", default=False, cast=bool)
if DEV_USE_SQLITE:
    DATABASES = {}  # Defined by config.settings.development.
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": required("DB_NAME"),
            "USER": required("DB_USER"),
            "PASSWORD": required("DB_PASSWORD"),
            "HOST": required("DB_HOST"),
            "PORT": config("DB_PORT", default=5432, cast=int),
            "OPTIONS": {"sslmode": config("DB_SSLMODE", default="require"), "connect_timeout": 5},
            "CONN_MAX_AGE": 0,
            "DISABLE_SERVER_SIDE_CURSORS": True,
        }
    }
    if DATABASES["default"]["OPTIONS"]["sslmode"] not in {"require", "verify-ca", "verify-full"}:
        raise ImproperlyConfigured(
            "DB_SSLMODE must preserve TLS: require, verify-ca or verify-full."
        )
    if not 1 <= DATABASES["default"]["PORT"] <= 65535:
        raise ImproperlyConfigured("DB_PORT must be between 1 and 65535.")
if VERIFY and os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings.production_check":
    DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
    DATABASE_ROUTERS = ["config.verification.NoDatabaseRouter"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{name}"}
    for name in (
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    )
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = csv("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = config("CORS_ALLOW_CREDENTIALS", default=False, cast=bool)
CSRF_TRUSTED_ORIGINS = csv("CSRF_TRUSTED_ORIGINS")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "apps.common.openapi.AppTagAutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "120/min"},
}
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].update(
    {
        "register": "5/hour",
        "login": "10/min",
        "refresh": "20/min",
        "password_change": "5/hour",  # nosec B105 - throttle rate, not a credential
        "password_reset": "5/hour",  # nosec B105 - throttle rate, not a credential
        "password_reset_confirm": "10/hour",  # nosec B105 - throttle rate, not a credential
        "verification_request": "5/hour",
        "verification_confirm": "10/hour",
        "enquiry": "10/hour",
    }
)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": __import__("datetime").timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": __import__("datetime").timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
}
API_DOCS_ENABLED = config("API_DOCS_ENABLED", default=False, cast=bool)
SMS_PROVIDER_ENABLED = config("SMS_PROVIDER_ENABLED", default=False, cast=bool)

# --- Notifications --------------------------------------------------------------------
# Email goes through Django's EMAIL_BACKEND; nothing is sent until this is True.
EMAIL_PROVIDER_ENABLED = config("EMAIL_PROVIDER_ENABLED", default=False, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="Leeza Cakes <orders@localhost>")
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_TIMEOUT = config("EMAIL_TIMEOUT", default=10, cast=int)
# Public origin of this backend, used for Django admin links in staff alerts.
BACKEND_PUBLIC_URL = config("BACKEND_PUBLIC_URL", default="").strip().rstrip("/")
# Background delivery (apps/notifications/worker.py, `manage.py run_notification_worker`).
NOTIFICATION_MAX_ATTEMPTS = config("NOTIFICATION_MAX_ATTEMPTS", default=5, cast=int)
NOTIFICATION_RETRY_DELAYS = [
    int(value) for value in csv("NOTIFICATION_RETRY_DELAYS", "60,300,1800,7200")
]
NOTIFICATION_LEASE_SECONDS = config("NOTIFICATION_LEASE_SECONDS", default=120, cast=int)
NOTIFICATION_WORKER_INTERVAL = config("NOTIFICATION_WORKER_INTERVAL", default=2.0, cast=float)
NOTIFICATION_WORKER_BATCH_SIZE = config("NOTIFICATION_WORKER_BATCH_SIZE", default=20, cast=int)
if NOTIFICATION_MAX_ATTEMPTS < 1 or not NOTIFICATION_RETRY_DELAYS:
    raise ImproperlyConfigured(
        "NOTIFICATION_MAX_ATTEMPTS must be at least 1 and NOTIFICATION_RETRY_DELAYS non-empty."
    )
if NOTIFICATION_LEASE_SECONDS < 30:
    raise ImproperlyConfigured("NOTIFICATION_LEASE_SECONDS must be at least 30.")
# WhatsApp (Meta Cloud API) settings, staff alert recipients and the storefront chat
# number are edited in Django admin (apps.notifications.WhatsAppSettings), not here.
# Secrets stored there are encrypted with FIELD_ENCRYPTION_KEY (comma-separated Fernet
# keys; the first one encrypts). Development and tests derive a fixed local key.
FIELD_ENCRYPTION_KEY = config("FIELD_ENCRYPTION_KEY", default="").strip()
PAYMENT_EVIDENCE_STORAGE_ROOT = config("PAYMENT_EVIDENCE_STORAGE_ROOT", default="")
PAYMENT_EVIDENCE_MAX_SIZE = config("PAYMENT_EVIDENCE_MAX_SIZE", default=5 * 1024 * 1024, cast=int)

# Frontend origin used to build links in transactional emails (verify, password reset).
FRONTEND_URL = config("FRONTEND_URL", default="").strip().rstrip("/")

# Order tax policy. ORDER_TAX_RATE is a percentage (e.g. 5 or 18). Checkout stays
# unavailable until it is explicitly configured; there is no implicit default rate.
_order_tax_rate = config("ORDER_TAX_RATE", default="").strip()
ORDER_TAX_POLICY_CONFIGURED = bool(_order_tax_rate)
ORDER_TAX_RATE = None
if ORDER_TAX_POLICY_CONFIGURED:
    try:
        ORDER_TAX_RATE = Decimal(_order_tax_rate)
    except InvalidOperation:
        raise ImproperlyConfigured("ORDER_TAX_RATE must be a decimal percentage.") from None
    if not Decimal("0") <= ORDER_TAX_RATE <= Decimal("100"):
        raise ImproperlyConfigured("ORDER_TAX_RATE must be between 0 and 100.")
# True when catalogue prices already include tax (GST-inclusive pricing).
ORDER_PRICES_INCLUDE_TAX = config("ORDER_PRICES_INCLUDE_TAX", default=False, cast=bool)

# Manual UPI payment instructions. Unset PAYMENT_UPI_ID means no instructions are shown.
PAYMENT_UPI_ID = config("PAYMENT_UPI_ID", default="").strip()
PAYMENT_UPI_PAYEE_NAME = config("PAYMENT_UPI_PAYEE_NAME", default="").strip()
PAYMENT_UPI_IS_SAMPLE = config("PAYMENT_UPI_IS_SAMPLE", default=False, cast=bool)

# Pickup slot grid, in TIME_ZONE local time.
PICKUP_OPEN_HOUR = config("PICKUP_OPEN_HOUR", default=10, cast=int)
PICKUP_CLOSE_HOUR = config("PICKUP_CLOSE_HOUR", default=20, cast=int)
PICKUP_SLOT_MINUTES = config("PICKUP_SLOT_MINUTES", default=60, cast=int)
PICKUP_DAYS_AHEAD = config("PICKUP_DAYS_AHEAD", default=14, cast=int)
PICKUP_MIN_LEAD_MINUTES = config("PICKUP_MIN_LEAD_MINUTES", default=240, cast=int)
if not 0 <= PICKUP_OPEN_HOUR < PICKUP_CLOSE_HOUR <= 24:
    raise ImproperlyConfigured("PICKUP_OPEN_HOUR must be before PICKUP_CLOSE_HOUR (0-24).")
if PICKUP_SLOT_MINUTES <= 0 or PICKUP_DAYS_AHEAD <= 0 or PICKUP_MIN_LEAD_MINUTES < 0:
    raise ImproperlyConfigured("Pickup slot settings must be positive.")


def _optional(name):
    value = config(name, default="").strip()
    return value or None


# Public business contact details served by /api/v1/site/. Unset values are null.
SITE_BUSINESS_NAME = config("SITE_BUSINESS_NAME", default="Leeza Cakes").strip() or None
SITE_CONTACT_PHONE = _optional("SITE_CONTACT_PHONE")
SITE_CONTACT_EMAIL = _optional("SITE_CONTACT_EMAIL")
SITE_INSTAGRAM = _optional("SITE_INSTAGRAM")
SITE_ADDRESS = _optional("SITE_ADDRESS")
SITE_PICKUP_HOURS_LABEL = _optional("SITE_PICKUP_HOURS_LABEL")
SITE_CONTENT_IS_SAMPLE = config("SITE_CONTENT_IS_SAMPLE", default=False, cast=bool)

SPECTACULAR_SETTINGS = {
    "TITLE": "Leeza Cakes API",
    "VERSION": "1.0.0",
    "DESCRIPTION": (
        "Leeza Cakes backend API for accounts, catalog, customization, cart, orders, "
        "payments, notifications, and product search."
    ),
    "TAGS": [
        {"name": "Common", "description": "Health and readiness endpoints."},
        {
            "name": "Accounts",
            "description": "Registration, authentication, profiles, and addresses.",
        },
        {"name": "Catalog", "description": "Public catalog browsing and staff catalog management."},
        {"name": "Customization", "description": "Product customization options and validation."},
        {"name": "Cart", "description": "Guest and authenticated cart operations."},
        {
            "name": "Orders",
            "description": (
                "Pickup checkout, customer orders, and staff order lifecycle management."
            ),
        },
        {
            "name": "Payments",
            "description": "UPI payment evidence submission and staff verification.",
        },
        {
            "name": "Notifications",
            "description": "Transactional notification preferences and delivery events.",
        },
        {"name": "Search", "description": "Unified public product search and filtering."},
        {"name": "Enquiries", "description": "Contact and custom-cake enquiries."},
        {"name": "Site", "description": "Public business and contact configuration."},
    ],
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_AUTHENTICATION": [],
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SWAGGER_UI_DIST": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.31.0",
    "SWAGGER_UI_FAVICON_HREF": None,
    "ENUM_NAME_OVERRIDES": {
        "ToStatusEnum": (
            ("pending_payment_verification", "Pending payment verification"),
            ("confirmed", "Confirmed"),
            ("preparing", "Preparing"),
            ("ready_for_pickup", "Ready for pickup"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ),
        "StatusEnum": (
            ("awaiting_payment", "Awaiting payment"),
            ("pending_verification", "Pending verification"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
        ),
        "StatusFa9Enum": (
            ("pending_review", "Pending review"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ),
    },
}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"safe": {"()": "core.logging.SafeJSONFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "safe"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
