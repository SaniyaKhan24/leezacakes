import importlib

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import clear_url_caches, resolve


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


def test_schema_groups_operations_by_app_and_describes_each_tag(client):
    schema = client.get("/api/schema/?format=json").json()
    tags = {tag["name"]: tag["description"] for tag in schema["tags"]}
    expected = {
        "Accounts",
        "Catalog",
        "Customization",
        "Cart",
        "Orders",
        "Payments",
        "Notifications",
        "Search",
        "Common",
    }
    assert set(tags) == expected
    assert tags["Accounts"]
    assert "Accounts" in schema["paths"]["/api/v1/accounts/register/"]["post"]["tags"]
    assert "Catalog" in schema["paths"]["/api/v1/catalog/products/"]["get"]["tags"]


def test_docs_are_available_in_development(client):
    for url in ("/api/docs/swagger/", "/api/docs/scalar/"):
        assert client.get(url).status_code == 200


@override_settings(DEBUG=True)
def test_admin_email_login_and_static_assets_work(client, db):
    import config.urls as root_urls

    clear_url_caches()
    importlib.reload(root_urls)
    user = get_user_model().objects.create_superuser(
        email="admin@example.com", password="Admin-password-123!"
    )
    response = client.post(
        "/admin/login/",
        {"username": user.email, "password": "Admin-password-123!", "next": "/admin/"},
    )
    assert response.status_code == 302
    assert response.url.endswith("/admin/")

    stylesheet = client.get("/static/admin/css/base.css")
    assert stylesheet.status_code == 200
    assert stylesheet["Content-Type"].startswith("text/css")
    body = b"".join(stylesheet.streaming_content)
    assert b"DJANGO Admin" in body


def test_invalid_correlation_id_is_replaced(client):
    response = client.get("/health/live/", HTTP_X_CORRELATION_ID="bad value")
    assert response.status_code == 200
    assert response["X-Correlation-ID"] != "bad value"
