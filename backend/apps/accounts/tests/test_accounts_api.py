import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.accounts.models import AccountVerificationToken, Address
from apps.accounts.selectors import owned_address, user_addresses

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="aisha@example.com",
        password="Strong-password-123!",
        first_name="Aisha",
        last_name="Khan",
        is_email_verified=True,
    )


def auth(client, user):
    client.force_authenticate(user=user)


def valid_address(**overrides):
    data = {
        "label": "Home",
        "recipient_name": "Aisha Khan",
        "phone_number": "+919876543210",
        "address_line_1": "1 Example Street",
        "address_line_2": "",
        "locality": "Area",
        "city": "Pune",
        "state": "Maharashtra",
        "postal_code": "411001",
        "country_code": "IN",
        "is_default": True,
    }
    data.update(overrides)
    return data


def test_registration_hashes_password_and_does_not_return_secrets(api_client, db):
    response = api_client.post(
        "/api/v1/accounts/register/",
        {
            "email": " New@example.com ",
            "password": "Strong-password-123!",
            "password_confirm": "Strong-password-123!",
            "first_name": "New",
            "last_name": "User",
        },
        format="json",
    )
    assert response.status_code == 201
    created = User.objects.get(email="new@example.com")
    assert created.check_password("Strong-password-123!")
    assert response.data["data"]["is_email_verified"] is False
    assert "password" not in response.data["data"]
    assert AccountVerificationToken.objects.filter(user=created).exists()


def test_registration_rejects_duplicate_and_admin_fields(api_client, user):
    response = api_client.post(
        "/api/v1/accounts/register/",
        {
            "email": user.email,
            "password": "Strong-password-123!",
            "password_confirm": "Strong-password-123!",
            "first_name": "X",
            "last_name": "Y",
            "is_staff": True,
        },
        format="json",
    )
    assert response.status_code == 400
    assert not User.objects.get(pk=user.pk).is_staff


def test_login_returns_jwt_and_rejects_unverified(api_client, user):
    response = api_client.post(
        "/api/v1/accounts/login/",
        {"email": user.email, "password": "Strong-password-123!"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["data"]["access"] and response.data["data"]["refresh"]
    user.is_email_verified = False
    user.save(update_fields=["is_email_verified"])
    assert (
        api_client.post(
            "/api/v1/accounts/login/",
            {"email": user.email, "password": "Strong-password-123!"},
            format="json",
        ).status_code
        == 401
    )


def test_logout_ignores_invalid_refresh_token_without_server_error(api_client, user):
    auth(api_client, user)
    response = api_client.post(
        "/api/v1/accounts/logout/", {"refresh": "malformed-token"}, format="json"
    )
    assert response.status_code == 204


def test_profile_requires_authentication_and_has_explicit_fields(api_client, user):
    assert api_client.get("/api/v1/accounts/me/").status_code == 401
    auth(api_client, user)
    response = api_client.get("/api/v1/accounts/me/")
    assert response.status_code == 200
    assert response.data["data"]["email"] == user.email
    assert "is_staff" not in response.data["data"]
    response = api_client.patch(
        "/api/v1/accounts/me/", {"first_name": "Updated", "is_staff": True}, format="json"
    )
    assert response.status_code == 200
    assert response.data["data"]["first_name"] == "Updated"
    assert not User.objects.get(pk=user.pk).is_staff


def test_password_change_and_reset(api_client, user):
    auth(api_client, user)
    response = api_client.post(
        "/api/v1/accounts/password/change/",
        {
            "current_password": "wrong",
            "new_password": "Another-strong-123!",
            "new_password_confirm": "Another-strong-123!",
        },
        format="json",
    )
    assert response.status_code == 400
    response = api_client.post(
        "/api/v1/accounts/password/change/",
        {
            "current_password": "Strong-password-123!",
            "new_password": "Another-strong-123!",
            "new_password_confirm": "Another-strong-123!",
        },
        format="json",
    )
    assert response.status_code == 200
    api_client.post(
        "/api/v1/accounts/password/reset/", {"email": "missing@example.com"}, format="json"
    )
    assert len(mail.outbox) == 0
    with TestCase.captureOnCommitCallbacks(execute=True):
        api_client.post("/api/v1/accounts/password/reset/", {"email": user.email}, format="json")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    response = api_client.post(
        "/api/v1/accounts/password/reset/confirm/",
        {
            "uid": uid,
            "token": token,
            "new_password": "Reset-strong-123!",
            "new_password_confirm": "Reset-strong-123!",
        },
        format="json",
    )
    assert response.status_code == 200
    assert User.objects.get(pk=user.pk).check_password("Reset-strong-123!")


def test_email_verification_is_single_use(api_client, db):
    user = User.objects.create_user(email="verify@example.com", password="Strong-password-123!")
    with TestCase.captureOnCommitCallbacks(execute=True):
        response = api_client.post(
            "/api/v1/accounts/email/verification/request/", {"email": user.email}, format="json"
        )
    assert response.status_code == 200
    raw = mail.outbox[-1].body.split(": ", 1)[1]
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    response = api_client.post(
        "/api/v1/accounts/email/verification/confirm/", {"uid": uid, "token": raw}, format="json"
    )
    assert response.status_code == 200
    assert User.objects.get(pk=user.pk).is_email_verified
    assert (
        api_client.post(
            "/api/v1/accounts/email/verification/confirm/",
            {"uid": uid, "token": raw},
            format="json",
        ).status_code
        == 400
    )


def test_addresses_are_owned_and_single_default(api_client, user, db):
    other = User.objects.create_user(
        email="other@example.com", password="Strong-password-123!", is_email_verified=True
    )
    auth(api_client, user)
    first = api_client.post("/api/v1/accounts/addresses/", valid_address(), format="json")
    second = api_client.post(
        "/api/v1/accounts/addresses/", valid_address(label="Work", is_default=True), format="json"
    )
    assert first.status_code == second.status_code == 201
    assert Address.objects.filter(user=user, is_default=True).count() == 1
    address_id = first.data["data"]["id"]
    auth(api_client, other)
    assert api_client.get(f"/api/v1/accounts/addresses/{address_id}/").status_code == 404
    auth(api_client, user)
    assert api_client.delete(f"/api/v1/accounts/addresses/{address_id}/").status_code == 204
    assert Address.objects.filter(user=user).count() == 1


def test_user_manager_normalizes_email_and_rejects_invalid_superuser(db):
    user = User.objects.create_user("  Mixed@Example.com ", password="Strong-password-123!")
    assert user.email == "mixed@example.com"
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            "bad@example.com", password="Strong-password-123!", is_staff=False
        )


def test_address_selectors_are_user_scoped(user, db):
    address = Address.objects.create(user=user, **valid_address())
    assert list(user_addresses(user)) == [address]
    assert owned_address(user, address.id) == address
