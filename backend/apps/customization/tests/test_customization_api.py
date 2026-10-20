import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product
from apps.customization.models import (
    CustomizationChoice,
    CustomizationOption,
    ProductCustomization,
    ProductCustomizationChoice,
)


@pytest.fixture
def configured_product(db):
    category = Category.objects.create(name="Cakes", slug="cakes")
    product = Product.objects.create(
        name="Cake",
        slug="cake",
        description="Cake",
        category=category,
        status=Product.PUBLISHED,
        base_price="500.00",
    )
    option = CustomizationOption.objects.create(
        name="Flavour", slug="flavour", input_type=CustomizationOption.SINGLE_CHOICE, is_active=True
    )
    choice = CustomizationChoice.objects.create(
        option=option, name="Vanilla", slug="vanilla", is_active=True
    )
    config = ProductCustomization.objects.create(
        product=product, option=option, is_required=True, is_active=True
    )
    product_choice = ProductCustomizationChoice.objects.create(
        product_customization=config, choice=choice, price_adjustment="100.00"
    )
    return product, option, choice, config, product_choice


def test_public_options_and_server_authoritative_validation(configured_product):
    product, option, choice, _, _ = configured_product
    client = APIClient()
    options = client.get(f"/api/v1/customization/products/{product.slug}/options/")
    assert options.status_code == 200
    assert options.data["options"][0]["option"]["slug"] == option.slug
    response = client.post(
        f"/api/v1/customization/products/{product.slug}/validate/",
        {
            "selections": [
                {"option_id": option.id, "choice_ids": [choice.id], "price_adjustment": "99999.00"}
            ]
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.data["customization_total"] == "100.00"


def test_required_and_wrong_choice_rejected(configured_product):
    product, option, choice, _, _ = configured_product
    other = CustomizationOption.objects.create(
        name="Other", slug="other", input_type=CustomizationOption.SINGLE_CHOICE
    )
    wrong = CustomizationChoice.objects.create(option=other, name="Wrong", slug="wrong")
    client = APIClient()
    missing = client.post(
        f"/api/v1/customization/products/{product.slug}/validate/",
        {"selections": []},
        format="json",
    )
    assert missing.status_code == 400
    invalid = client.post(
        f"/api/v1/customization/products/{product.slug}/validate/",
        {"selections": [{"option_id": option.id, "choice_ids": [wrong.id]}]},
        format="json",
    )
    assert invalid.status_code == 400


def test_staff_customization_management(configured_product):
    product, _, _, _, _ = configured_product
    from apps.accounts.models import User

    staff = User.objects.create_user(email="custom-staff@example.com", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=staff)
    option = client.post(
        "/api/v1/customization/admin/options/",
        {"name": "Colour", "slug": "colour", "input_type": "single_choice"},
        format="json",
    )
    assert option.status_code == 201
    choice = client.post(
        f"/api/v1/customization/admin/options/{option.data['id']}/choices/",
        {"name": "Pink", "slug": "pink"},
        format="json",
    )
    assert choice.status_code == 201
    config = client.post(
        f"/api/v1/customization/admin/products/{product.id}/options/",
        {"option": option.data["id"], "is_required": False},
        format="json",
    )
    assert config.status_code == 201


def test_customization_choices_and_admin_updates(configured_product):
    product, option, choice, config, product_choice = configured_product
    client = APIClient()
    assert (
        client.get(
            f"/api/v1/customization/products/{product.slug}/options/{option.id}/choices/"
        ).status_code
        == 200
    )
    staff = __import__("apps.accounts.models", fromlist=["User"]).User.objects.create_user(
        email="choice-staff@example.com", is_staff=True
    )
    client.force_authenticate(user=staff)
    assert (
        client.patch(
            f"/api/v1/customization/admin/options/{option.id}/",
            {"description": "Updated"},
            format="json",
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/customization/admin/options/{option.id}/choices/{choice.id}/",
            {"name": "Vanilla updated"},
            format="json",
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/customization/admin/products/{product.id}/options/{config.id}/",
            {"is_required": False},
            format="json",
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/customization/admin/products/{product.id}/options/{config.id}/choices/{product_choice.id}/",
            {"price_adjustment": "50.00"},
            format="json",
        ).status_code
        == 200
    )
