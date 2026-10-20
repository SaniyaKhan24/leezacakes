import importlib

from django.apps import apps
from django.conf import settings
from django.urls import resolve


def test_apps_and_settings_are_registered():
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
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert "JWTAuthentication" in settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"][0]


def test_health_routes_and_security_headers(client):
    response = client.get("/health/live/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert resolve("/health/ready/").url_name == "health-ready"
    assert response["X-Correlation-ID"]
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"


def test_schema_contains_accounts_and_health(client):
    response = client.get("/api/schema/?format=json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health/live/" in paths
    assert "/health/ready/" in paths
    assert "/api/v1/accounts/register/" in paths
    assert "/api/v1/accounts/addresses/{address_id}/" in paths


def test_docs_are_available_in_development(client):
    for url in ("/api/docs/swagger/", "/api/docs/scalar/"):
        assert client.get(url).status_code == 200


def test_invalid_correlation_id_is_replaced(client):
    response = client.get("/health/live/", HTTP_X_CORRELATION_ID="bad value")
    assert response.status_code == 200
    assert response["X-Correlation-ID"] != "bad value"
