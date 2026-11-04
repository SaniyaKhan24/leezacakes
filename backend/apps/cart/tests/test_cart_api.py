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


def test_guest_cart_merge_keeps_text_and_multiple_choice_customizations(product):
    from apps.customization.models import (
        CustomizationChoice,
        CustomizationOption,
        ProductCustomization,
        ProductCustomizationChoice,
    )

    message = CustomizationOption.objects.create(name="Message", slug="message", input_type="text")
    toppings = CustomizationOption.objects.create(
        name="Toppings", slug="toppings", input_type="multiple_choice"
    )
    ProductCustomization.objects.create(product=product, option=message)
    config = ProductCustomization.objects.create(product=product, option=toppings, max_selections=3)
    choice_ids = []
    for slug, price in (("gold", "300.00"), ("flowers", "250.00")):
        choice = CustomizationChoice.objects.create(option=toppings, name=slug, slug=slug)
        ProductCustomizationChoice.objects.create(
            product_customization=config, choice=choice, price_adjustment=price
        )
        choice_ids.append(choice.id)
    client = APIClient()
    added = client.post(
        "/api/v1/cart/items/",
        {
            "product_id": product.id,
            "quantity": 1,
            "selections": [
                {"option_id": toppings.id, "choice_ids": choice_ids},
                {"option_id": message.id, "text_value": "Happy birthday"},
            ],
        },
        format="json",
    )
    assert added.status_code == 201
    assert added.data["subtotal"] == "1050.00"
    validated = client.post("/api/v1/cart/validate/", {}, format="json")
    assert validated.data["valid"] is True
    user = User.objects.create_user(
        email="merge@example.com", password="Strong-password-123!", is_email_verified=True
    )
    client.force_authenticate(user=user)
    merged = client.post("/api/v1/cart/merge/", {}, format="json")
    assert merged.status_code == 200
    assert merged.data["issues"] == []
    assert merged.data["merged"] is True
    assert merged.data["cart"]["subtotal"] == "1050.00"
    item = owned_cart(type("Request", (), {"user": user})()).items.get()
    assert item.customizations.count() == 3
    assert item.customizations.filter(text_value="Happy birthday").exists()
