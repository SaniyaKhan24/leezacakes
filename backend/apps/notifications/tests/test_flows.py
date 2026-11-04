"""Real order/payment flows emit the expected notifications with complete payloads."""

from datetime import datetime
from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.notifications.models import DeliveryAttempt, Notification
from apps.notifications.tests.helpers import configure_whatsapp
from apps.notifications.worker import process_due
from apps.orders.models import Order
from apps.orders.services.transitions import transition_order
from apps.orders.tests.test_orders_api import checkout_payload, checkout_user  # noqa: F401
from apps.payments.models import Payment
from apps.payments.services import review_submission, submit_evidence, verify_payment
from apps.payments.tests.test_models import image_upload, order  # noqa: F401

ORDER_FIELDS = {"order_id", "order_number", "customer_name", "grand_total", "pickup", "items"}


@pytest.fixture
def staff_team(db):
    owner = User.objects.create_superuser(email="owner@example.com", password="Owner-pass-123!")
    baker = User.objects.create_user(email="baker@example.com", is_staff=True)
    return owner, baker


def test_checkout_notifies_customer_and_every_staff_user(
    checkout_user,  # noqa: F811
    staff_team,
    settings,
    mailoutbox,
):
    configure_whatsapp(staff_alert_emails=["owner@leezacakes.test"])
    user, client = checkout_user
    response = client.post(
        "/api/v1/orders/",
        checkout_payload(customer_name="Aarav Mehta", customer_email="aarav@example.com"),
        format="json",
        HTTP_IDEMPOTENCY_KEY="notify-1",
    )
    assert response.status_code == 201
    # Nothing is sent during the request; deliveries wait in the outbox for the worker.
    assert mailoutbox == []
    queued = DeliveryAttempt.objects.filter(status=DeliveryAttempt.PENDING)
    assert queued.filter(channel="email").count() == 2
    assert all(attempt.next_attempt_at for attempt in queued)
    process_due()
    placed = Order.objects.get(pk=response.data["id"])
    customer = Notification.objects.get(event_key="order_created")
    assert customer.user == user
    assert customer.audience == Notification.CUSTOMER
    assert ORDER_FIELDS <= set(customer.payload)
    assert customer.payload["order_id"] == str(placed.id)
    assert customer.payload["grand_total"] == "500.00"
    assert datetime.fromisoformat(customer.payload["pickup"]) == placed.pickup_slot_start
    assert customer.payload["items"] == [{"name": "Cake", "variant": "", "quantity": 1}]
    assert customer.rendered["title"] == f"Order {placed.order_number} received"
    assert customer.rendered["link"] == f"/orders/{placed.id}"

    staff_rows = Notification.objects.filter(event_key="staff_order_created")
    assert {row.user for row in staff_rows if row.user} == set(staff_team)
    assert staff_rows.filter(user__isnull=True).count() == 1
    staff_row = staff_rows.get(user=staff_team[0])
    assert staff_row.rendered["title"] == f"New order {placed.order_number} · ₹500"
    assert staff_row.rendered["body"].startswith("Aarav Mehta · Cake ×1 · pickup ")
    assert staff_row.rendered["link"] == f"/admin/orders/order/{placed.id}/change/"

    by_recipient = {mail.to[0]: mail for mail in mailoutbox}
    assert set(by_recipient) == {"aarav@example.com", "owner@leezacakes.test"}
    assert (
        by_recipient["aarav@example.com"].subject == f"We've received order {placed.order_number}"
    )
    assert f"http://frontend.test/orders/{placed.id}" in by_recipient["aarav@example.com"].body
    assert by_recipient["owner@leezacakes.test"].subject.startswith("New order")
    assert (
        f"http://backend.test/admin/orders/order/{placed.id}/change/"
        in by_recipient["owner@leezacakes.test"].body
    )

    # The idempotent retry does not notify again.
    retry = client.post(
        "/api/v1/orders/",
        checkout_payload(customer_name="Aarav Mehta", customer_email="aarav@example.com"),
        format="json",
        HTTP_IDEMPOTENCY_KEY="notify-1",
    )
    assert retry.status_code in {200, 400}
    assert Notification.objects.filter(event_key="order_created").count() == 1
    assert process_due()["claimed"] == 0


def test_checkout_survives_a_broken_notification_channel(
    checkout_user,  # noqa: F811
    monkeypatch,
):
    from apps.notifications import services

    def broken(channel, message, recipient):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(services, "_deliver", broken)
    user, client = checkout_user
    response = client.post(
        "/api/v1/orders/", checkout_payload(), format="json", HTTP_IDEMPOTENCY_KEY="safe-1"
    )
    assert response.status_code == 201
    assert Notification.objects.filter(event_key="order_created").exists()
    # The worker logs the crash and leaves the rows leased for a later retry.
    assert process_due()["claimed"] >= 1


def test_evidence_upload_notifies_customer_and_staff(order, staff_team):  # noqa: F811
    payment = Payment.objects.create(order=order, user=order.user, amount_due=order.grand_total)
    submission = submit_evidence(payment, order.user, image_upload())
    customer = Notification.objects.get(event_key="payment_submitted")
    assert customer.user == order.user
    assert customer.deduplication_key == f"submission:{submission.id}:payment_submitted"
    assert ORDER_FIELDS <= set(customer.payload)
    assert customer.payload["payment_id"] == str(payment.id)
    assert customer.rendered["title"] == "We've got your payment screenshot"
    staff = Notification.objects.filter(event_key="staff_payment_submitted")
    assert staff.count() == 3  # two staff users plus the broadcast row
    row = staff.get(user=staff_team[1])
    assert row.rendered["title"] == "Payment screenshot for LZ-TEST-1 · ₹100"
    assert row.rendered["link"] == f"/admin/payments/payment/{payment.id}/change/"


def test_review_verify_and_lifecycle_events(order, staff_team):  # noqa: F811
    reviewer = staff_team[0]
    payment = Payment.objects.create(order=order, user=order.user, amount_due=order.grand_total)
    first = submit_evidence(payment, order.user, image_upload())
    review_submission(payment, first, reviewer, "reject", "Unreadable")
    rejected = Notification.objects.get(event_key="payment_rejected")
    assert rejected.payload["reason"] == "Unreadable"
    assert ORDER_FIELDS <= set(rejected.payload)

    second = submit_evidence(payment, order.user, image_upload())
    review_submission(payment, second, reviewer, "accept")
    verify_payment(payment, second, reviewer, Decimal("100.00"))
    for status in (Order.PREPARING, Order.READY, Order.COMPLETED):
        transition_order(Order.objects.get(pk=order.pk), status, actor=reviewer)

    customer_events = set(
        Notification.objects.filter(user=order.user).values_list("event_key", flat=True)
    )
    assert customer_events == {
        "payment_submitted",
        "payment_rejected",
        "payment_verified",
        "order_confirmed",
        "preparing",
        "ready",
        "completed",
    }
    for notification in Notification.objects.filter(user=order.user):
        assert notification.payload["order_id"] == str(order.id)
        assert notification.payload["order_number"] == "LZ-TEST-1"
        assert notification.rendered["link"] == f"/orders/{order.id}"
    ready = Notification.objects.get(event_key="ready")
    assert ready.payload["status"] == Order.READY
    assert ready.rendered["title"] == "Order LZ-TEST-1 is ready for pickup"
    assert Notification.objects.filter(event_key="staff_payment_submitted").count() == 6
    # Deliveries are queued with the events but nothing has been sent yet: that is
    # the worker's job, outside the request.
    assert DeliveryAttempt.objects.exists()
    assert not DeliveryAttempt.objects.exclude(status=DeliveryAttempt.PENDING).exists()
    assert not DeliveryAttempt.objects.filter(attempt_count__gt=0).exists()
