import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product, ProductVariant
from apps.catalog.services import archive_product, publish_product, validate_variant_for_product


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


def test_catalog_category_and_price_filters(catalog_data):
    category, product, _ = catalog_data
    Product.objects.create(
        name="Premium Cake",
        slug="premium-cake",
        description="Rich cake",
        category=category,
        status=Product.PUBLISHED,
        base_price="1500.00",
    )
    response = APIClient().get(
        "/api/v1/catalog/products/?category=cakes&min_price=1000&max_price=1200"
    )
    assert response.status_code == 200
    assert [item["slug"] for item in response.data["results"]] == [product.slug]


def test_staff_catalog_management(catalog_data):
    category, _, _ = catalog_data
    from apps.accounts.models import User

    staff = User.objects.create_user(email="catalog-staff@example.com", is_staff=True)
    client = APIClient()
    client.force_authenticate(user=staff)
    created = client.post(
        "/api/v1/catalog/admin/categories/", {"name": "Wedding", "slug": "wedding"}, format="json"
    )
    assert created.status_code == 201
    product = client.post(
        "/api/v1/catalog/admin/products/",
        {
            "name": "New Cake",
            "slug": "new-cake",
            "description": "Cake",
            "category": str(category.id),
            "base_price": "700.00",
        },
        format="json",
    )
    assert product.status_code == 201
    product_id = product.data["id"]
    assert client.post(f"/api/v1/catalog/admin/products/{product_id}/publish/").status_code == 200
    assert client.post(f"/api/v1/catalog/admin/products/{product_id}/archive/").status_code == 200


def test_catalog_detail_and_variant_management(catalog_data):
    category, product, _ = catalog_data
    from apps.accounts.models import User

    public = APIClient()
    assert public.get(f"/api/v1/catalog/categories/{category.slug}/").status_code == 200
    assert public.get(f"/api/v1/catalog/products/{product.slug}/").status_code == 200
    assert public.get(f"/api/v1/catalog/products/{product.slug}/variants/").status_code == 200
    staff = User.objects.create_user(email="variant-staff@example.com", is_staff=True)
    public.force_authenticate(user=staff)
    created = public.post(
        f"/api/v1/catalog/admin/products/{product.id}/variants/",
        {"name": "2 kg", "price": "1800.00"},
        format="json",
    )
    assert created.status_code == 201
    variant_id = created.data["id"]
    assert (
        public.patch(
            f"/api/v1/catalog/admin/products/{product.id}/variants/{variant_id}/",
            {"price": "1900.00"},
            format="json",
        ).status_code
        == 200
    )
    assert (
        public.post(
            f"/api/v1/catalog/admin/products/{product.id}/variants/{variant_id}/deactivate/"
        ).status_code
        == 200
    )
    assert (
        public.post(f"/api/v1/catalog/admin/categories/{category.id}/deactivate/").status_code
        == 200
    )
    assert (
        public.patch(
            f"/api/v1/catalog/admin/products/{product.id}/",
            {"description": "Updated cake"},
            format="json",
        ).status_code
        == 200
    )


def test_catalog_services_validate_and_archive(catalog_data):
    category, product, _ = catalog_data
    assert validate_variant_for_product(product, product.variants.first().id)
    assert validate_variant_for_product(product, "00000000-0000-0000-0000-000000000000") is None
    assert archive_product(product).status == Product.ARCHIVED
    product.status = Product.DRAFT
    product.save(update_fields=["status"])
    assert publish_product(product).status == Product.PUBLISHED
