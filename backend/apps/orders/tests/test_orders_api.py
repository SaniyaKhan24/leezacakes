from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cart.services.cart_service import add_item, get_or_create_cart
from apps.catalog.models import Category, Product
from apps.orders.models import Order


@pytest.fixture
def checkout_user(db):
    user = User.objects.create_user(
        email="order@example.com", password="Strong-password-123!", is_email_verified=True
    )
    category = Category.objects.create(name="Cakes", slug="cakes")
    product = Product.objects.create(
        name="Cake",
        slug="cake",
        description="Cake",
        category=category,
        status=Product.PUBLISHED,
        base_price="500.00",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    request = type("Request", (), {"user": user, "session": client.session})()
    cart = get_or_create_cart(request)
    add_item(cart, product.id, None, 1, [])
    return user, client


@override_settings(ORDER_TAX_POLICY_CONFIGURED=True, ORDER_TAX_RATE="0")
def test_checkout_is_idempotent_and_snapshots_catalog(checkout_user):
    user, client = checkout_user
    start = timezone.now() + timedelta(hours=1)
    payload = {
        "customer_name": "Buyer",
        "customer_phone": "+919876543210",
        "pickup_slot_start": start.isoformat(),
        "pickup_slot_end": (start + timedelta(minutes=15)).isoformat(),
    }
    response = client.post(
        "/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="checkout-1"
    )
    assert response.status_code == 201
    retry = client.post(
        "/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="checkout-1"
    )
    assert retry.status_code == 200
    assert Order.objects.count() == 1
    assert response.data["items"][0]["product_name_snapshot"] == "Cake"


def test_customer_cannot_checkout_without_authentication():
    assert APIClient().post("/api/v1/orders/", {}, format="json").status_code == 401


def test_staff_order_transitions_require_payment_and_follow_lifecycle(checkout_user):
    user, client = checkout_user
    start = timezone.now() + timedelta(hours=1)
    with override_settings(ORDER_TAX_POLICY_CONFIGURED=True, ORDER_TAX_RATE="0"):
        response = client.post(
            "/api/v1/orders/",
            {
                "customer_name": "Buyer",
                "customer_phone": "+919876543210",
                "pickup_slot_start": start.isoformat(),
                "pickup_slot_end": (start + timedelta(minutes=15)).isoformat(),
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="transition-1",
        )
    order = Order.objects.get(pk=response.data["id"])
    staff = User.objects.create_user(email="staff@example.com", is_staff=True)
    client.force_authenticate(user=staff)
    denied = client.post(
        f"/api/v1/orders/staff/{order.id}/transitions/",
        {"to_status": Order.CONFIRMED},
        format="json",
    )
    assert denied.status_code == 400
    # Staff views require staff; confirmation additionally requires verified payment.
    assert client.get(f"/api/v1/orders/staff/{order.id}/").status_code == 200


def test_customer_order_list_and_isolation(checkout_user):
    user, client = checkout_user
    start = timezone.now() + timedelta(hours=1)
    with override_settings(ORDER_TAX_POLICY_CONFIGURED=True, ORDER_TAX_RATE="0"):
        response = client.post(
            "/api/v1/orders/",
            {
                "customer_name": "Buyer",
                "customer_phone": "+919876543210",
                "pickup_slot_start": start.isoformat(),
                "pickup_slot_end": (start + timedelta(minutes=15)).isoformat(),
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="list-1",
        )
    order_id = response.data["id"]
    assert client.get("/api/v1/orders/").status_code == 200
    assert client.get(f"/api/v1/orders/{order_id}/").status_code == 200
    other = User.objects.create_user(email="order-other@example.com")
    client.force_authenticate(user=other)
    assert client.get(f"/api/v1/orders/{order_id}/").status_code == 404


def test_staff_order_list_requires_staff(checkout_user):
    _, client = checkout_user
    assert client.get("/api/v1/orders/staff/").status_code == 403
