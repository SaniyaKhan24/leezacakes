from django.urls import path

from .views import (
    AdminChoiceCreateView,
    AdminChoiceDetailView,
    AdminOptionDetailView,
    AdminOptionListCreateView,
    AdminProductChoiceCreateView,
    AdminProductChoiceDetailView,
    AdminProductCustomizationCreateView,
    AdminProductCustomizationDetailView,
    ProductChoicesView,
    ProductOptionsView,
    ValidateSelectionsView,
)

app_name = "customization"
urlpatterns = [
    path(
        "products/<slug:product_slug>/options/",
        ProductOptionsView.as_view(),
        name="product-options",
    ),
    path(
        "products/<slug:product_slug>/options/<int:option_id>/choices/",
        ProductChoicesView.as_view(),
        name="product-choices",
    ),
    path(
        "products/<slug:product_slug>/validate/", ValidateSelectionsView.as_view(), name="validate"
    ),
    path("admin/options/", AdminOptionListCreateView.as_view(), name="admin-options"),
    path(
        "admin/options/<int:option_id>/",
        AdminOptionDetailView.as_view(),
        name="admin-option-detail",
    ),
    path(
        "admin/options/<int:option_id>/choices/",
        AdminChoiceCreateView.as_view(),
        name="admin-choice-create",
    ),
    path(
        "admin/options/<int:option_id>/choices/<int:choice_id>/",
        AdminChoiceDetailView.as_view(),
        name="admin-choice-detail",
    ),
    path(
        "admin/products/<uuid:product_id>/options/",
        AdminProductCustomizationCreateView.as_view(),
        name="admin-product-option-create",
    ),
    path(
        "admin/products/<uuid:product_id>/options/<int:product_customization_id>/",
        AdminProductCustomizationDetailView.as_view(),
        name="admin-product-option-detail",
    ),
    path(
        "admin/products/<uuid:product_id>/options/<int:product_customization_id>/choices/",
        AdminProductChoiceCreateView.as_view(),
        name="admin-product-choice-create",
    ),
    path(
        "admin/products/<uuid:product_id>/options/<int:product_customization_id>/choices/<int:product_choice_id>/",
        AdminProductChoiceDetailView.as_view(),
        name="admin-product-choice-detail",
    ),
]
