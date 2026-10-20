import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product, ProductVariant


@pytest.fixture
def catalog_data(db):
    category = Category.objects.create(name="Cakes", slug="cakes")
    product = Product.objects.create(
        name="Chocolate Cake",
        slug="chocolate-cake",
        description="Rich cake",
        category=category,
        status=Product.PUBLISHED,
        base_price="650.00",
        is_available=True,
    )
    ProductVariant.objects.create(product=product, name="1 kg", price="1100.00")
    draft = Product.objects.create(
        name="Draft",
        slug="draft",
        description="Draft",
        category=category,
        status=Product.DRAFT,
        base_price="10.00",
    )
    return category, product, draft


def test_public_catalog_hides_drafts_and_returns_decimal_price(catalog_data):
    _, product, draft = catalog_data
    client = APIClient()
    response = client.get("/api/v1/catalog/products/")
    assert response.status_code == 200
    assert response.data["results"][0]["slug"] == product.slug
    assert all(item["slug"] != draft.slug for item in response.data["results"])
    assert response.data["results"][0]["effective_price"] == "1100.00"


def test_unavailable_product_and_inactive_category_are_hidden(catalog_data):
    category, product, _ = catalog_data
    product.is_available = False
    product.save(update_fields=["is_available"])
    category.is_active = False
    category.save(update_fields=["is_active"])
    client = APIClient()
    assert client.get("/api/v1/catalog/products/").data["results"] == []
    assert client.get("/api/v1/catalog/categories/").data["results"] == []


def test_catalog_admin_requires_staff(catalog_data):
    client = APIClient()
    assert (
        client.post(
            "/api/v1/catalog/admin/categories/", {"name": "New", "slug": "new"}, format="json"
        ).status_code
        == 401
    )
