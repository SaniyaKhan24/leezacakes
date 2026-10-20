import pytest

from apps.accounts.models import User
from apps.notifications.models import DeliveryAttempt, Notification
from apps.notifications.services import dispatch_notification, emit_event


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
