import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import DeliveryAttempt, Notification
from apps.notifications.services import (
    dispatch_notification,
    emit_event,
    emit_staff_event,
)
from apps.notifications.tasks import deliver_notification
from apps.notifications.tests.helpers import configure_whatsapp


def test_transactional_event_is_deduplicated_and_unconfigured_channels_skipped(db, settings):
    settings.EMAIL_PROVIDER_ENABLED = False
    user = User.objects.create_user(email="notify@example.com", phone_number="+919876543210")
    first = emit_event("order_created", user=user, deduplication_key="order:1:created")
    second = emit_event("order_created", user=user, deduplication_key="order:1:created")
    assert first.pk == second.pk
    assert Notification.objects.count() == 1
    assert first.audience == Notification.CUSTOMER
    dispatch_notification(first.pk)
    attempts = {a.channel: a for a in DeliveryAttempt.objects.all()}
    assert set(attempts) == {"email", "whatsapp"}
    assert all(a.status == DeliveryAttempt.SKIPPED for a in attempts.values())
    assert attempts["email"].error_message == "email provider is not configured."
    assert attempts["whatsapp"].recipient == "919876543210"


def test_unknown_event_is_rejected():
    with pytest.raises(ValueError):
        emit_event("arbitrary", deduplication_key="arbitrary:1")
    with pytest.raises(ValueError):
        emit_event("staff_order_created", deduplication_key="arbitrary:2")
    with pytest.raises(ValueError):
        emit_staff_event("order_created", {}, "arbitrary:3")


def test_preferences_are_user_scoped(db):
    user = User.objects.create_user(email="preferences@example.com")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/notifications/preferences/")
    assert response.status_code == 200
    response = client.patch(
        "/api/v1/notifications/preferences/", {"marketing_sms_enabled": True}, format="json"
    )
    assert response.status_code == 200
    user.notification_preferences.refresh_from_db()
    assert user.notification_preferences.marketing_consent_recorded_at is not None
    assert user.notification_preferences.marketing_consent_source == "account_settings"


def test_notification_task_dispatches(db, settings):
    notification = Notification.objects.create(
        event_key="order_created", deduplication_key="task:1"
    )
    deliver_notification(notification.pk)
    assert not notification.attempts.exists()


def test_configured_email_marks_delivery_sent_once(db, settings, mailoutbox):
    settings.EMAIL_PROVIDER_ENABLED = True
    user = User.objects.create_user(email="provider@example.com")
    notification = emit_event("order_created", user=user, deduplication_key="provider:1")
    dispatch_notification(notification.pk)
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="email")
    assert attempt.status == DeliveryAttempt.SENT
    assert attempt.attempt_count == 1
    assert attempt.recipient == "provider@example.com"
    assert len(mailoutbox) == 1
    whatsapp = notification.attempts.get(channel="whatsapp")
    assert whatsapp.status == DeliveryAttempt.SKIPPED


def test_staff_event_creates_one_row_per_active_staff_user_and_a_broadcast(db):
    owner = User.objects.create_superuser(email="owner@example.com", password="Owner-pass-123!")
    helper = User.objects.create_user(email="helper@example.com", is_staff=True)
    User.objects.create_user(email="former@example.com", is_staff=True, is_active=False)
    User.objects.create_user(email="customer@example.com")
    rows = emit_staff_event("staff_order_created", {"order_number": "LZ-1"}, "order:x:staff")
    again = emit_staff_event("staff_order_created", {"order_number": "LZ-1"}, "order:x:staff")
    assert [row.pk for row in rows] == [row.pk for row in again]
    staff_rows = Notification.objects.filter(audience=Notification.STAFF)
    assert {row.user for row in staff_rows if row.user} == {owner, helper}
    assert staff_rows.filter(user__isnull=True).count() == 1
    assert staff_rows.get(user=owner).deduplication_key == f"order:x:staff:user:{owner.pk}"


def test_per_user_staff_rows_are_in_app_only(db, settings, mailoutbox):
    configure_whatsapp(staff_alert_emails=["owner@leezacakes.test"])
    staff = User.objects.create_user(email="staff@example.com", is_staff=True)
    emit_staff_event("staff_order_created", {"order_number": "LZ-2"}, "order:y:staff")
    dispatch_notification(Notification.objects.get(user=staff).pk)
    broadcast = Notification.objects.get(user__isnull=True)
    # Only the broadcast row carries external deliveries; per-user rows are in-app only.
    assert set(DeliveryAttempt.objects.values_list("notification_id", flat=True)) == {broadcast.pk}
    dispatch_notification(broadcast.pk)
    assert [m.to for m in mailoutbox] == [["owner@leezacakes.test"]]
    assert broadcast.attempts.get(channel="whatsapp").error_message == (
        "whatsapp provider is not configured."
    )


def test_missing_staff_recipients_are_recorded_as_skipped(db, settings):
    emit_staff_event("staff_payment_submitted", {}, "submission:z:staff")
    broadcast = Notification.objects.get(user__isnull=True)
    dispatch_notification(broadcast.pk)
    email = broadcast.attempts.get(channel="email")
    assert email.status == DeliveryAttempt.SKIPPED
    assert email.error_message == "No email address (add staff alert emails in admin)."


def test_channel_exception_is_recorded_and_other_channels_continue(db, settings, monkeypatch):
    from apps.notifications import channels

    def explode(message, recipient):
        raise RuntimeError("boom")

    monkeypatch.setattr(channels.email, "send", explode)
    user = User.objects.create_user(email="explode@example.com", phone_number="9876543210")
    notification = emit_event("order_created", user=user, deduplication_key="explode:1")
    dispatch_notification(notification.pk)
    email = notification.attempts.get(channel="email")
    assert email.status == DeliveryAttempt.FAILED
    assert email.error_message == "RuntimeError: boom"
    assert notification.attempts.get(channel="whatsapp").status == DeliveryAttempt.SKIPPED
