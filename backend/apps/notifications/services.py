from django.conf import settings
from django.db import transaction

from .models import DeliveryAttempt, Notification, NotificationPreference


def emit_event(event_key, *, user=None, payload=None, deduplication_key=None):
    if event_key not in Notification.EVENT_KEYS:
        raise ValueError("Unsupported notification event.")
    key = deduplication_key or f"{event_key}:{user.pk if user else 'system'}"
    notification, created = Notification.objects.get_or_create(
        deduplication_key=key,
        defaults={"event_key": event_key, "user": user, "payload": payload or {}},
    )
    if created:
        transaction.on_commit(lambda: dispatch_notification(notification.pk))
    return notification


def dispatch_notification(notification_id):
    notification = Notification.objects.select_related("user").get(pk=notification_id)
    channels = []
    if notification.user:
        if notification.user.phone_number:
            channels.extend(("whatsapp", "sms"))
        if notification.user.email:
            channels.append("email")
    enabled = {
        "whatsapp": settings.WHATSAPP_PROVIDER_ENABLED,
        "sms": settings.SMS_PROVIDER_ENABLED,
        "email": settings.EMAIL_PROVIDER_ENABLED,
    }
    for channel in channels:
        attempt, created = DeliveryAttempt.objects.get_or_create(
            notification=notification, channel=channel
        )
        if not created and attempt.status == DeliveryAttempt.SENT:
            continue
        attempt.attempt_count += 1
        attempt.status = DeliveryAttempt.SENT if enabled[channel] else DeliveryAttempt.SKIPPED
        attempt.error_message = "" if enabled[channel] else f"{channel} provider is not configured."
        attempt.save(update_fields=("attempt_count", "status", "error_message", "updated_at"))


def get_preferences(user):
    preference, _ = NotificationPreference.objects.get_or_create(user=user)
    return preference
