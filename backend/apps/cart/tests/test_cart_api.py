import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cart.permissions import CartAccessPermission
from apps.cart.selectors import owned_cart
from apps.cart.services.cart_service import get_or_create_cart
from apps.catalog.models import Category, Product, ProductVariant


@pytest.fixture
def product(db):
    category = Category.objects.create(name="Cakes", slug="cakes")
    product = Product.objects.create(
        name="Cake",
        slug="cake",
        description="Cake",
        category=category,
        status=Product.PUBLISHED,
        base_price="500.00",
    )
    ProductVariant.objects.create(product=product, name="1 kg", price="900.00")
    return product


def test_guest_cart_add_merge_and_server_price(product):
    client = APIClient()
    response = client.post(
        "/api/v1/cart/items/", {"product_id": product.id, "quantity": 1}, format="json"
    )
    assert response.status_code == 201
    assert response.data["subtotal"] == "500.00"
    response = client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "quantity": 2, "price": "0.01"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["items"][0]["quantity"] == 3
    user = User.objects.create_user(
        email="buyer@example.com", password="Strong-password-123!", is_email_verified=True
    )
    client.force_authenticate(user=user)
    merged = client.post("/api/v1/cart/merge/", {}, format="json")
    assert merged.status_code == 200
    assert merged.data["cart"]["items"][0]["quantity"] == 3


def test_cart_variant_lines_are_separate_and_ownership_isolated(product):
    user = User.objects.create_user(
        email="owner@example.com", password="Strong-password-123!", is_email_verified=True
    )
    other = User.objects.create_user(
        email="other@example.com", password="Strong-password-123!", is_email_verified=True
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/v1/cart/items/", {"product_id": product.id, "quantity": 1}, format="json"
    )
    assert response.status_code == 201
    response = client.post(
        "/api/v1/cart/items/",
        {"product_id": product.id, "variant_id": product.variants.first().id, "quantity": 1},
        format="json",
    )
    assert response.data["subtotal"] == "1400.00"
    item_id = response.data["items"][0]["id"]
    client.force_authenticate(user=other)
    assert (
        client.patch(f"/api/v1/cart/items/{item_id}/", {"quantity": 3}, format="json").status_code
        == 404
    )


def test_price_change_requires_confirmation(product):
    client = APIClient()
    added = client.post(
        "/api/v1/cart/items/", {"product_id": product.id, "quantity": 1}, format="json"
    )
    assert added.status_code == 201
    product.base_price = "600.00"
    product.save(update_fields=["base_price"])
    result = client.post("/api/v1/cart/validate/", {}, format="json")
    assert result.data["price_confirmation_required"] is True
    assert client.post("/api/v1/cart/confirm-prices/", {}, format="json").status_code == 200


def test_cart_item_update_remove_clear_and_validate(product):
    client = APIClient()
    added = client.post(
        "/api/v1/cart/items/", {"product_id": product.id, "quantity": 1}, format="json"
    )
    item_id = added.data["items"][0]["id"]
    assert client.get("/api/v1/cart/").status_code == 200
    assert (
        client.patch(f"/api/v1/cart/items/{item_id}/", {"quantity": 2}, format="json").status_code
        == 200
    )
    assert client.post("/api/v1/cart/checkout/validate/", {}, format="json").status_code == 200
    assert client.delete(f"/api/v1/cart/items/{item_id}/").status_code == 204
    assert client.delete("/api/v1/cart/items/").status_code == 204


def test_cart_selector_returns_only_current_cart(product):
    user = User.objects.create_user(email="selector@example.com")
    client = APIClient()
    client.force_authenticate(user=user)
    request = type("Request", (), {"user": user, "session": client.session})()
    cart = get_or_create_cart(request)
    assert owned_cart(request) == cart
    guest_client = APIClient()
    guest_request = type(
        "Request",
        (),
        {"user": type("Anon", (), {"is_authenticated": False})(), "session": guest_client.session},
    )()
    guest_cart = get_or_create_cart(guest_request)
    assert owned_cart(guest_request) == guest_cart
    assert CartAccessPermission().has_permission(guest_request, None)
