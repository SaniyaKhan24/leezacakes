import os

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
    raise ImproperlyConfigured("DB_SSLMODE must preserve TLS: require, verify-ca or verify-full.")
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
CORS_ALLOW_CREDENTIALS = False
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
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
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
        "password_change": "5/hour",
        "password_reset": "5/hour",
        "password_reset_confirm": "10/hour",
        "verification_request": "5/hour",
        "verification_confirm": "10/hour",
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
WHATSAPP_PROVIDER_ENABLED = config("WHATSAPP_PROVIDER_ENABLED", default=False, cast=bool)
SMS_PROVIDER_ENABLED = config("SMS_PROVIDER_ENABLED", default=False, cast=bool)
EMAIL_PROVIDER_ENABLED = config("EMAIL_PROVIDER_ENABLED", default=False, cast=bool)
PAYMENT_EVIDENCE_STORAGE_ROOT = config("PAYMENT_EVIDENCE_STORAGE_ROOT", default="")
PAYMENT_EVIDENCE_MAX_SIZE = config("PAYMENT_EVIDENCE_MAX_SIZE", default=5 * 1024 * 1024, cast=int)
SPECTACULAR_SETTINGS = {
    "TITLE": "Leeza Cakes API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_AUTHENTICATION": [],
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SWAGGER_UI_DIST": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.31.0",
    "SWAGGER_UI_FAVICON_HREF": None,
}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"safe": {"()": "core.logging.SafeJSONFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "safe"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
