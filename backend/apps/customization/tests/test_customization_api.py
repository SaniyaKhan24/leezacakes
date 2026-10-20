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
