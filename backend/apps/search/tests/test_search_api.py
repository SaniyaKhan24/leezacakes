import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product


@pytest.fixture
def products(db):
    active = Category.objects.create(name="Cakes", slug="cakes")
    hidden = Category.objects.create(name="Hidden", slug="hidden", is_active=False)
    visible = Product.objects.create(
        name="Chocolate Cake",
        slug="chocolate-cake",
        description="Rich chocolate birthday cake",
        category=active,
        status=Product.PUBLISHED,
        base_price="900.00",
    )
    Product.objects.create(
        name="Hidden Cake",
        slug="hidden-cake",
        description="secret",
        category=hidden,
        status=Product.PUBLISHED,
        base_price="100.00",
    )
    return visible


def test_search_filters_visibility_and_price(products):
    response = APIClient().get("/api/v1/search/?q=chocolate&min_price=500")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["slug"] == "chocolate-cake"


def test_search_rejects_unsupported_structured_filter(products):
    response = APIClient().get("/api/v1/search/?color=pink")
    assert response.status_code == 400
