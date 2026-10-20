from django.urls import path

from .views import (
    AdminCategoryDeactivateView,
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminImageCreateView,
    AdminImageDetailView,
    AdminProductArchiveView,
    AdminProductDetailView,
    AdminProductListCreateView,
    AdminProductPublishView,
    AdminVariantCreateView,
    AdminVariantDeactivateView,
    AdminVariantDetailView,
    CategoryDetailView,
    CategoryListView,
    ProductDetailView,
    ProductListView,
    ProductVariantListView,
)

app_name = "catalog"
urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<slug:slug>/", CategoryDetailView.as_view(), name="category-detail"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("products/<slug:slug>/variants/", ProductVariantListView.as_view(), name="variant-list"),
    path("admin/categories/", AdminCategoryListCreateView.as_view(), name="admin-category-list"),
    path(
        "admin/categories/<uuid:category_id>/",
        AdminCategoryDetailView.as_view(),
        name="admin-category-detail",
    ),
    path(
        "admin/categories/<uuid:category_id>/deactivate/",
        AdminCategoryDeactivateView.as_view(),
        name="admin-category-deactivate",
    ),
    path("admin/products/", AdminProductListCreateView.as_view(), name="admin-product-list"),
    path(
        "admin/products/<uuid:product_id>/",
        AdminProductDetailView.as_view(),
        name="admin-product-detail",
    ),
    path(
        "admin/products/<uuid:product_id>/publish/",
        AdminProductPublishView.as_view(),
        name="admin-product-publish",
    ),
    path(
        "admin/products/<uuid:product_id>/archive/",
        AdminProductArchiveView.as_view(),
        name="admin-product-archive",
    ),
    path(
        "admin/products/<uuid:product_id>/images/",
        AdminImageCreateView.as_view(),
        name="admin-image-create",
    ),
    path(
        "admin/products/<uuid:product_id>/images/<uuid:image_id>/",
        AdminImageDetailView.as_view(),
        name="admin-image-detail",
    ),
    path(
        "admin/products/<uuid:product_id>/variants/",
        AdminVariantCreateView.as_view(),
        name="admin-variant-create",
    ),
    path(
        "admin/products/<uuid:product_id>/variants/<uuid:variant_id>/",
        AdminVariantDetailView.as_view(),
        name="admin-variant-detail",
    ),
    path(
        "admin/products/<uuid:product_id>/variants/<uuid:variant_id>/deactivate/",
        AdminVariantDeactivateView.as_view(),
        name="admin-variant-deactivate",
    ),
]
