from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.utils import timezone

from apps.accounts.models import User
from apps.orders.models import Order, OrderItem, OrderItemCustomization


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="studio@example.com", password="Studio-pass-123!")


@pytest.fixture
def confirmed_order(db):
    customer = User.objects.create_user(email="cust@example.com")
    order = Order.objects.create(
        order_number="LZ-ADMIN-1",
        user=customer,
        status=Order.CONFIRMED,
        payment_status=Order.PAYMENT_VERIFIED,
        customer_name="Aanya",
        customer_phone="+91 90000 00001",
        pickup_slot_start=timezone.now(),
        pickup_slot_end=timezone.now(),
        subtotal=Decimal("850.00"),
        tax_total=Decimal("0.00"),
        grand_total=Decimal("850.00"),
        idempotency_key="admin-1",
        request_fingerprint="f",
    )
    item = OrderItem.objects.create(
        order=order,
        product_name_snapshot="Red Velvet",
        variant_name_snapshot="1 kg",
        quantity=1,
        unit_base_price=Decimal("850.00"),
        unit_customization_total=Decimal("80.00"),
        unit_price=Decimal("930.00"),
        line_total=Decimal("930.00"),
    )
    OrderItemCustomization.objects.create(
        order_item=item,
        option_name_snapshot="Egg preference",
        choice_name_snapshot="Eggless",
        price_adjustment=Decimal("80.00"),
    )
    OrderItemCustomization.objects.create(
        order_item=item, option_name_snapshot="Message", value_snapshot="Happy 30th"
    )
    return order


def act(client, action, order):
    response = client.post(
        "/admin/orders/order/",
        {"action": action, "_selected_action": [str(order.id)]},
        follow=True,
    )
    assert response.status_code == 200
    return [str(message) for message in get_messages(response.wsgi_request)]


def test_order_admin_pages_render(confirmed_order, superuser, client):
    client.force_login(superuser)
    listing = client.get("/admin/orders/order/")
    assert listing.status_code == 200
    body = listing.content.decode()
    assert "LZ-ADMIN-1" in body and "Leeza Cakes Studio" in body
    detail = client.get(f"/admin/orders/order/{confirmed_order.id}/change/")
    assert detail.status_code == 200
    page = detail.content.decode()
    assert "Eggless" in page and "Happy 30th" in page


def test_order_admin_actions_walk_the_lifecycle(confirmed_order, superuser, client):
    client.force_login(superuser)
    assert any("moved to preparing" in m for m in act(client, "start_preparing", confirmed_order))
    assert any("ready for pickup" in m for m in act(client, "mark_ready", confirmed_order))
    assert any("completed" in m for m in act(client, "mark_completed", confirmed_order))
    order = Order.objects.get(pk=confirmed_order.pk)
    assert order.status == Order.COMPLETED
    assert order.completed_at is not None
    history = list(order.status_history.values_list("to_status", "changed_by"))
    assert history == [
        (Order.PREPARING, superuser.pk),
        (Order.READY, superuser.pk),
        (Order.COMPLETED, superuser.pk),
    ]
    # Invalid transitions are reported, not raised.
    errors = act(client, "cancel_orders", confirmed_order)
    assert any("LZ-ADMIN-1: This order transition is not allowed." in m for m in errors)


def test_order_admin_cancel_sets_timestamp(confirmed_order, superuser, client):
    client.force_login(superuser)
    act(client, "cancel_orders", confirmed_order)
    order = Order.objects.get(pk=confirmed_order.pk)
    assert order.status == Order.CANCELLED
    assert order.cancelled_at is not None


def test_pending_order_cannot_skip_to_preparing(confirmed_order, superuser, client):
    Order.objects.filter(pk=confirmed_order.pk).update(status=Order.PENDING_PAYMENT)
    client.force_login(superuser)
    errors = act(client, "start_preparing", confirmed_order)
    assert any("not allowed" in m for m in errors)
    assert Order.objects.get(pk=confirmed_order.pk).status == Order.PENDING_PAYMENT
