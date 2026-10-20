from django.urls import path

from .views import (
    AddressDetailView,
    AddressListCreateView,
    AddressSetDefaultView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    TokenRefreshView,
    VerificationConfirmView,
    VerificationRequestView,
)

app_name = "accounts"
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"
    ),
    path(
        "email/verification/request/",
        VerificationRequestView.as_view(),
        name="verification-request",
    ),
    path(
        "email/verification/confirm/",
        VerificationConfirmView.as_view(),
        name="verification-confirm",
    ),
    path("addresses/", AddressListCreateView.as_view(), name="address-list"),
    path("addresses/<uuid:address_id>/", AddressDetailView.as_view(), name="address-detail"),
    path(
        "addresses/<uuid:address_id>/set-default/",
        AddressSetDefaultView.as_view(),
        name="address-set-default",
    ),
]
