from django.urls import path

from .views import (
    CartCheckoutValidateView,
    CartConfirmPricesView,
    CartItemCustomizationView,
    CartItemDetailView,
    CartItemListCreateView,
    CartMergeView,
    CartValidateView,
    CartView,
)

app_name = "cart"
urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/", CartItemListCreateView.as_view(), name="cart-items"),
    path("items/<uuid:item_id>/", CartItemDetailView.as_view(), name="cart-item"),
    path(
        "items/<uuid:item_id>/customizations/",
        CartItemCustomizationView.as_view(),
        name="cart-item-customizations",
    ),
    path("validate/", CartValidateView.as_view(), name="cart-validate"),
    path("confirm-prices/", CartConfirmPricesView.as_view(), name="cart-confirm-prices"),
    path("merge/", CartMergeView.as_view(), name="cart-merge"),
    path("checkout/validate/", CartCheckoutValidateView.as_view(), name="cart-checkout-validate"),
]
