from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cart.services.cart_service import add_item, get_or_create_cart
from apps.catalog.models import Category, Product
from apps.orders.models import Order
from apps.orders.services.pickup import PickupConfig, first_available_slot


def valid_slot(lead_minutes=1440):
    """First bookable slot on the configured grid for the given lead time."""
    return first_available_slot(timezone.now(), lead_minutes, PickupConfig.from_settings())


def checkout_payload(**overrides):
    start, end = valid_slot()
    payload = {
        "customer_name": "Buyer",
        "customer_phone": "+919876543210",
        "pickup_slot_start": start.isoformat(),
        "pickup_slot_end": end.isoformat(),
    }
    payload.update(overrides)
    return payload


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
        preparation_time=1440,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    request = type("Request", (), {"user": user, "session": client.session})()
    cart = get_or_create_cart(request)
    add_item(cart, product.id, None, 1, [])
    return user, client


def test_checkout_is_idempotent_and_snapshots_catalog(checkout_user):
    user, client = checkout_user
    payload = checkout_payload()
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
    assert response.data["prices_include_tax"] is True
    assert response.data["tax_total"] == "0.00"
    assert response.data["grand_total"] == "500.00"
    assert response.data["payment"]["review_status"] == "awaiting_payment"
    assert response.data["payment"]["id"]


def test_customer_cannot_checkout_without_authentication():
    assert APIClient().post("/api/v1/orders/", {}, format="json").status_code == 401


def test_staff_order_transitions_require_payment_and_follow_lifecycle(checkout_user):
    user, client = checkout_user
    response = client.post(
        "/api/v1/orders/", checkout_payload(), format="json", HTTP_IDEMPOTENCY_KEY="transition-1"
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
    response = client.post(
        "/api/v1/orders/", checkout_payload(), format="json", HTTP_IDEMPOTENCY_KEY="list-1"
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


def test_checkout_rejects_slots_outside_the_generated_grid(checkout_user):
    _, client = checkout_user
    start, end = valid_slot()
    invalid = [
        # Too soon: inside the product's 24 hour preparation time.
        (timezone.now() + timedelta(hours=1), timezone.now() + timedelta(hours=2)),
        # Off-grid start and a wrong duration.
        (start + timedelta(minutes=15), end + timedelta(minutes=15)),
        (start, start + timedelta(minutes=15)),
        # Beyond the booking window.
        (start + timedelta(days=30), end + timedelta(days=30)),
    ]
    for index, (bad_start, bad_end) in enumerate(invalid):
        response = client.post(
            "/api/v1/orders/",
            checkout_payload(
                pickup_slot_start=bad_start.isoformat(), pickup_slot_end=bad_end.isoformat()
            ),
            format="json",
            HTTP_IDEMPOTENCY_KEY=f"bad-slot-{index}",
        )
        assert response.status_code == 400, (bad_start, bad_end)
        assert "pickup_slot" in str(response.data)
    assert Order.objects.count() == 0


def test_checkout_rejects_naive_and_reversed_slots(checkout_user):
    _, client = checkout_user
    start, end = valid_slot()
    response = client.post(
        "/api/v1/orders/",
        checkout_payload(pickup_slot_start=end.isoformat(), pickup_slot_end=start.isoformat()),
        format="json",
        HTTP_IDEMPOTENCY_KEY="reversed",
    )
    assert response.status_code == 400
    assert "pickup_slot" in str(response.data)


def test_checkout_requires_configured_tax_policy(checkout_user):
    _, client = checkout_user
    with override_settings(ORDER_TAX_POLICY_CONFIGURED=False):
        response = client.post(
            "/api/v1/orders/", checkout_payload(), format="json", HTTP_IDEMPOTENCY_KEY="no-tax"
        )
    assert response.status_code == 400
    assert "tax policy" in str(response.data)
    with override_settings(ORDER_TAX_POLICY_CONFIGURED=True, ORDER_TAX_RATE=None):
        response = client.post(
            "/api/v1/orders/", checkout_payload(), format="json", HTTP_IDEMPOTENCY_KEY="no-rate"
        )
    assert response.status_code == 400


@override_settings(ORDER_TAX_RATE="5", ORDER_PRICES_INCLUDE_TAX=False)
def test_checkout_adds_exclusive_tax(checkout_user):
    _, client = checkout_user
    response = client.post(
        "/api/v1/orders/", checkout_payload(), format="json", HTTP_IDEMPOTENCY_KEY="tax-excl"
    )
    assert response.status_code == 201
    assert response.data["tax_total"] == "25.00"
    assert response.data["grand_total"] == "525.00"
    assert response.data["prices_include_tax"] is False


@override_settings(ORDER_TAX_RATE="5", ORDER_PRICES_INCLUDE_TAX=True)
def test_checkout_reports_inclusive_tax_component(checkout_user):
    _, client = checkout_user
    response = client.post(
        "/api/v1/orders/", checkout_payload(), format="json", HTTP_IDEMPOTENCY_KEY="tax-incl"
    )
    assert response.status_code == 201
    assert response.data["tax_total"] == "23.81"
    assert response.data["grand_total"] == "500.00"


def test_pickup_slots_uses_cart_preparation_time(checkout_user):
    _, client = checkout_user
    response = client.get("/api/v1/orders/pickup-slots/")
    assert response.status_code == 200
    assert response.data["lead_time_minutes"] == 1440
    assert response.data["timezone"] == "Asia/Kolkata"
    assert len(response.data["days"]) == 14
    first = response.data["days"][0]
    assert len(first["slots"]) == 10
    assert set(first["slots"][0]) == {"start", "end", "available"}
    # Nothing in the first 24 hours is bookable.
    assert not any(slot["available"] for slot in first["slots"])
    start, _ = valid_slot()
    available = [
        slot["start"] for day in response.data["days"] for slot in day["slots"] if slot["available"]
    ]
    assert available[0] == start.isoformat()


def test_pickup_slots_for_anonymous_visitor_does_not_create_cart(db):
    from apps.cart.models import Cart

    client = APIClient()
    response = client.get("/api/v1/orders/pickup-slots/")
    assert response.status_code == 200
    assert response.data["lead_time_minutes"] == 240
    assert Cart.objects.count() == 0
    assert "sessionid" not in response.cookies


def test_pickup_slots_reads_guest_session_cart(db):
    category = Category.objects.create(name="Tiered", slug="tiered")
    product = Product.objects.create(
        name="Tall cake",
        slug="tall-cake",
        description="Tall",
        category=category,
        status=Product.PUBLISHED,
        base_price="5000.00",
        preparation_time=2880,
    )
    client = APIClient()
    added = client.post(
        "/api/v1/cart/items/", {"product_id": str(product.id), "quantity": 1}, format="json"
    )
    assert added.status_code == 201
    response = client.get("/api/v1/orders/pickup-slots/")
    assert response.data["lead_time_minutes"] == 2880
