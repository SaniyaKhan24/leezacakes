import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import DeliveryAttempt, Notification
from apps.notifications.services import dispatch_notification, emit_event
from apps.notifications.tasks import deliver_notification


def test_transactional_event_is_deduplicated_and_unconfigured_channels_skipped(db, settings):
    settings.WHATSAPP_PROVIDER_ENABLED = False
    settings.SMS_PROVIDER_ENABLED = False
    settings.EMAIL_PROVIDER_ENABLED = False
    user = User.objects.create_user(email="notify@example.com", phone_number="+919876543210")
    first = emit_event("order_created", user=user, deduplication_key="order:1:created")
    second = emit_event("order_created", user=user, deduplication_key="order:1:created")
    assert first.pk == second.pk
    assert Notification.objects.count() == 1
    dispatch_notification(first.pk)
    assert DeliveryAttempt.objects.filter(status=DeliveryAttempt.SKIPPED).count() == 3


def test_unknown_event_is_rejected():
    with pytest.raises(ValueError):
        emit_event("arbitrary", deduplication_key="arbitrary:1")


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
