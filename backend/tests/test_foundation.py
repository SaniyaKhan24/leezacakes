import importlib
import json
import logging

import pytest
from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import clear_url_caches, resolve, reverse
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from core.logging import SafeJSONFormatter


def test_health_has_no_database_dependency(client):
    response = client.get(reverse("common:health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert resolve("/api/v1/health/").url_name == "health"
    assert client.post("/api/v1/health/").status_code == 405
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"


def test_app_registration_and_auth_defaults():
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
    ):
        assert apps.get_app_config(name).name == f"apps.{name}"
        importlib.import_module(f"apps.{name}.models")
    assert settings.AUTH_USER_MODEL == "auth.User"
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.dummy"

    class PrivateView(APIView):
        def get(self, request):
            return Response({"private": True})

    response = PrivateView.as_view()(APIRequestFactory().get("/"))
    assert response.status_code == 403
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == [
        "rest_framework.authentication.SessionAuthentication"
    ]


def test_schema_and_documentation(client):
    response = client.get("/api/schema/?format=json")
    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/health/" in schema["paths"]
    assert not schema["paths"]["/api/v1/health/"]["get"].get("security")
    assert not schema.get("security")
    for url in ("/api/docs/swagger/", "/api/docs/scalar/"):
        response = client.get(url)
        assert response.status_code == 200
        assert b"/api/schema/" in response.content


def test_docs_disabled():
    import config.urls

    try:
        with override_settings(API_DOCS_ENABLED=False):
            importlib.reload(config.urls)
            clear_url_caches()
            for url in ("/api/schema/", "/api/docs/swagger/", "/api/docs/scalar/"):
                assert Client().get(url).status_code == 404
    finally:
        importlib.reload(config.urls)
        clear_url_caches()


def test_host_and_cors_rejection(client):
    assert client.get("/api/v1/health/", HTTP_HOST="untrusted.invalid").status_code == 400
    assert "Access-Control-Allow-Origin" not in client.get(
        "/api/v1/health/", HTTP_ORIGIN="https://untrusted.invalid"
    )
    with override_settings(CORS_ALLOWED_ORIGINS=["https://frontend.example.invalid"]):
        response = client.get("/api/v1/health/", HTTP_ORIGIN="https://frontend.example.invalid")
        assert response["Access-Control-Allow-Origin"] == "https://frontend.example.invalid"


def test_safe_logs():
    record = logging.LogRecord(
        "django.request", logging.ERROR, "", 1, "password=DO-NOT-LOG", (), None
    )
    record.request = {"secret": "DO-NOT-LOG"}
    rendered = SafeJSONFormatter().format(record)
    assert "DO-NOT-LOG" not in rendered
    assert json.loads(rendered)["level"] == "ERROR"
    try:
        raise ValueError("DO-NOT-LOG")
    except ValueError:
        import sys

        record.exc_info = sys.exc_info()
    assert json.loads(SafeJSONFormatter().format(record))["exception_type"] == "ValueError"


def test_throttling():
    class PublicView(APIView):
        permission_classes = []
        authentication_classes = []

        def get(self, request):
            return Response({})

    cache.clear()
    view = PublicView.as_view()
    factory = APIRequestFactory()
    for _ in range(60):
        assert view(factory.get("/", REMOTE_ADDR="192.0.2.1")).status_code == 200
    assert view(factory.get("/", REMOTE_ADDR="192.0.2.1")).status_code == 429
    cache.clear()


def test_session_csrf_enforced():
    from django.contrib.auth.models import User
    from rest_framework.authentication import SessionAuthentication
    from rest_framework.exceptions import PermissionDenied
    from rest_framework.request import Request

    request = APIRequestFactory(enforce_csrf_checks=True).post("/", {})
    request.user = User(username="unsaved")
    with pytest.raises(PermissionDenied):
        SessionAuthentication().authenticate(Request(request))


def test_entrypoints_and_development():
    assert importlib.import_module("config.asgi").application
    assert importlib.import_module("config.wsgi").application
    development = importlib.import_module("config.settings.development")
    assert development.DEBUG
    assert "*" not in development.ALLOWED_HOSTS
    from config.verification import NoDatabaseRouter

    assert NoDatabaseRouter().allow_migrate("default", "auth") is False


def test_required_configuration(monkeypatch):
    from django.core.exceptions import ImproperlyConfigured

    from config.environment import required

    monkeypatch.setenv("MISSING_TEST_SETTING", "")
    with pytest.raises(ImproperlyConfigured, match="MISSING_TEST_SETTING"):
        required("MISSING_TEST_SETTING")


@pytest.mark.parametrize(
    "variable,value",
    [
        ("DJANGO_SECRET_KEY", ""),
        ("DJANGO_SECRET_KEY", "short"),
        ("DJANGO_ALLOWED_HOSTS", "*"),
        ("DJANGO_ALLOWED_HOSTS", "<production-host>"),
        ("DJANGO_ALLOWED_HOSTS", "api.example.invalid:443"),
        ("DJANGO_ALLOWED_HOSTS", ""),
        ("CORS_ALLOWED_ORIGINS", ""),
        ("CORS_ALLOWED_ORIGINS", "http://frontend.example.invalid"),
        ("CSRF_TRUSTED_ORIGINS", "https://frontend.example.invalid/path"),
    ],
)
def test_production_rejects_bad_configuration(monkeypatch, variable, value):
    from django.core.exceptions import ImproperlyConfigured

    import config.settings.base as base

    monkeypatch.setenv(variable, value)
    setting = {"DJANGO_ALLOWED_HOSTS": "ALLOWED_HOSTS"}.get(variable, variable)
    if setting in {"ALLOWED_HOSTS", "CORS_ALLOWED_ORIGINS", "CSRF_TRUSTED_ORIGINS"}:
        monkeypatch.setattr(base, setting, [value] if value else [])
    import sys

    sys.modules.pop("config.settings.production", None)
    with pytest.raises(ImproperlyConfigured):
        importlib.import_module("config.settings.production")


def test_production_security(monkeypatch):
    import sys

    sys.modules.pop("config.settings.production", None)
    monkeypatch.setenv("TRUST_PROXY_SSL_HEADER", "True")
    production = importlib.import_module("config.settings.production")
    assert production.DEBUG is False
    assert production.SESSION_COOKIE_SECURE and production.CSRF_COOKIE_SECURE
    assert production.SECURE_SSL_REDIRECT
    assert production.SECURE_HSTS_SECONDS >= 31536000
    assert production.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert production.SECURE_HSTS_PRELOAD is True
    importlib.import_module("config.settings.production_check")
