import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.validators import to_e164_digits

from .channels import CHANNELS, DeliveryResult
from .models import DeliveryAttempt, Notification, NotificationPreference, WhatsAppSettings

logger = logging.getLogger(__name__)


# Payloads -----------------------------------------------------------------------------------


def order_payload(order, **extra):
    """Common payload for order events. Copy is rendered later from these fields."""
    payload = {
        "order_id": str(order.pk),
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "grand_total": None if order.grand_total is None else str(order.grand_total),
        "pickup": order.pickup_slot_start.isoformat() if order.pickup_slot_start else None,
        "status": order.status,
        "items": [
            {
                "name": item.product_name_snapshot,
                "variant": item.variant_name_snapshot,
                "quantity": item.quantity,
            }
            for item in order.items.all()
        ],
    }
    payload.update(extra)
    return payload


# Emitting -----------------------------------------------------------------------------------


def emit_event(event_key, *, user=None, payload=None, deduplication_key=None):
    """Record a customer notification and queue its deliveries for the worker."""
    if event_key not in Notification.CUSTOMER_EVENT_KEYS:
        raise ValueError("Unsupported notification event.")
    key = deduplication_key or f"{event_key}:{user.pk if user else 'system'}"
    notification, created = Notification.objects.get_or_create(
        deduplication_key=key,
        defaults={
            "event_key": event_key,
            "user": user,
            "audience": Notification.CUSTOMER,
            "payload": payload or {},
        },
    )
    if created:
        enqueue_deliveries(notification)
    return notification


def staff_recipients():
    return get_user_model().objects.filter(is_active=True, is_staff=True).order_by("date_joined")


def emit_staff_event(event_key, payload, deduplication_key):
    """Alert the shop: one in-app row per active staff user (each with its own read
    state) plus one broadcast row (no user) that carries the email/WhatsApp deliveries
    to the staff alert emails and numbers set in admin (WhatsApp & alert settings)."""
    if event_key not in Notification.STAFF_EVENT_KEYS:
        raise ValueError("Unsupported staff notification event.")
    payload = payload or {}
    created_rows = []
    for user in staff_recipients():
        notification, _ = Notification.objects.get_or_create(
            deduplication_key=f"{deduplication_key}:user:{user.pk}",
            defaults={
                "event_key": event_key,
                "user": user,
                "audience": Notification.STAFF,
                "payload": payload,
            },
        )
        created_rows.append(notification)
    broadcast, created = Notification.objects.get_or_create(
        deduplication_key=f"{deduplication_key}:broadcast",
        defaults={
            "event_key": event_key,
            "user": None,
            "audience": Notification.STAFF,
            "payload": payload,
        },
    )
    if created:
        enqueue_deliveries(broadcast)
    return created_rows


# Dispatching --------------------------------------------------------------------------------


def _customer_targets(notification):
    """[(channel, recipient)] for a customer notification; order contact details win."""
    user = notification.user
    if user is None:
        return []
    from apps.orders.models import Order

    order = None
    order_id = (notification.payload or {}).get("order_id")
    if order_id:
        order = Order.objects.filter(pk=order_id, user=user).first()
    email = (order.customer_email if order else "") or user.email
    phone = (order.customer_phone if order else "") or user.phone_number
    return [("email", email or ""), ("whatsapp", to_e164_digits(phone) or "")]


def _staff_targets():
    config = WhatsAppSettings.load()
    emails, numbers = config.staff_emails, config.staff_numbers
    targets = [("email", address) for address in emails]
    targets += [
        ("whatsapp", to_e164_digits(number) or f"invalid:{number}"[:254]) for number in numbers
    ]
    if not emails:
        targets.append(("email", ""))
    if not numbers:
        targets.append(("whatsapp", ""))
    return targets


def delivery_targets(notification):
    if notification.audience == Notification.STAFF:
        # Per-user staff rows are in-app only; the broadcast row fans out externally,
        # except for in-app-only events (incoming WhatsApp messages).
        if notification.user_id or notification.event_key in Notification.IN_APP_ONLY_EVENT_KEYS:
            return []
        return _staff_targets()
    return _customer_targets(notification)


def _deliver(channel, message, recipient):
    module = CHANNELS[channel]
    if not module.is_enabled():
        return DeliveryResult.skipped(f"{channel} provider is not configured.")
    if recipient.startswith("invalid:"):
        return DeliveryResult.skipped(f"'{recipient[8:]}' is not a valid WhatsApp number.")
    if not recipient:
        if channel == "email":
            reason = "No email address" + (
                " (add staff alert emails in admin)." if message["audience"] == "staff" else "."
            )
        else:
            reason = "No phone number" + (
                " (add staff WhatsApp numbers in admin)." if message["audience"] == "staff" else "."
            )
        return DeliveryResult.skipped(reason)
    try:
        return module.send(message, recipient)
    except Exception as exc:  # a broken channel must never break the others
        logger.exception("Notification channel %s failed", channel)
        return DeliveryResult.failed(f"{type(exc).__name__}: {exc}")


def enqueue_deliveries(notification):
    """Queue one delivery per (channel, recipient). Runs inside the caller's
    transaction, so a rolled-back checkout never sends anything (outbox pattern).
    The worker (`manage.py run_notification_worker`) does the actual sending."""
    now = timezone.now()
    attempts = []
    for channel, recipient in delivery_targets(notification):
        attempt, _ = DeliveryAttempt.objects.get_or_create(
            notification=notification,
            channel=channel,
            recipient=recipient,
            defaults={"status": DeliveryAttempt.PENDING, "next_attempt_at": now},
        )
        attempts.append(attempt)
    return attempts


def retry_delay(attempt_count):
    """Seconds to wait after the Nth failed attempt (1m, 5m, 30m, 2h by default)."""
    delays = settings.NOTIFICATION_RETRY_DELAYS
    return delays[min(attempt_count, len(delays)) - 1]


def deliver_attempt(attempt):
    """Send one queued delivery and record the outcome. Transient failures are
    rescheduled with backoff until NOTIFICATION_MAX_ATTEMPTS; everything else ends
    with next_attempt_at = NULL."""
    message = attempt.notification.rendered
    result = _deliver(attempt.channel, message, attempt.recipient)
    now = timezone.now()
    attempt.attempt_count += 1
    attempt.status = result.status
    attempt.provider_message_id = result.provider_message_id
    attempt.error_message = result.error[:500]
    attempt.last_attempt_at = now
    attempt.locked_until = None
    retry = (
        result.status == DeliveryAttempt.FAILED
        and result.retryable
        and attempt.attempt_count < settings.NOTIFICATION_MAX_ATTEMPTS
    )
    attempt.next_attempt_at = (
        now + timedelta(seconds=retry_delay(attempt.attempt_count)) if retry else None
    )
    attempt.save(
        update_fields=(
            "attempt_count",
            "status",
            "provider_message_id",
            "error_message",
            "last_attempt_at",
            "locked_until",
            "next_attempt_at",
            "updated_at",
        )
    )
    return attempt


def dispatch_notification(notification_id):
    """Send a notification's deliveries right now (admin "send now", tests).
    Idempotent per (notification, channel, recipient): SENT attempts are never repeated."""
    notification = Notification.objects.select_related("user").get(pk=notification_id)
    enqueue_deliveries(notification)
    for attempt in notification.attempts.select_related("notification__user"):
        if attempt.status != DeliveryAttempt.SENT:
            deliver_attempt(attempt)


# Inbox --------------------------------------------------------------------------------------


def inbox_queryset(user, audience=None):
    """A user's own in-app notifications; staff rows only while the user is staff."""
    queryset = Notification.objects.filter(user=user)
    if not user.is_staff:
        queryset = queryset.filter(audience=Notification.CUSTOMER)
    if audience in {Notification.CUSTOMER, Notification.STAFF}:
        queryset = queryset.filter(audience=audience)
    return queryset


def unread_count(user, audience=None):
    return inbox_queryset(user, audience).filter(read_at__isnull=True).count()


def mark_read(user, ids=None, mark_all=False):
    queryset = inbox_queryset(user).filter(read_at__isnull=True)
    if not mark_all:
        queryset = queryset.filter(pk__in=ids or [])
    queryset.update(read_at=timezone.now())
    return unread_count(user)


def get_preferences(user):
    preference, _ = NotificationPreference.objects.get_or_create(user=user)
    return preference
