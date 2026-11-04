"""WhatsApp operations: webhook processing, customer conversations and replies, and the
admin tools (check connection, sync/submit templates, send a test message)."""

import hashlib
import hmac
import logging
import re
from datetime import UTC, datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.validators import to_e164_digits

from .channels.whatsapp import GraphError, get_provider
from .messages import WHATSAPP_TEMPLATE_DEFS, fill_template, render
from .models import (
    DeliveryAttempt,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppSettings,
    WhatsAppTemplate,
)

logger = logging.getLogger(__name__)
SERVICE_WINDOW = timedelta(hours=24)
DIGITS = re.compile(r"^[1-9]\d{7,14}$")


class WhatsAppError(Exception):
    """A problem to show to staff as-is (already redacted)."""


def _timestamp(value):
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return timezone.now()


def _digits(value):
    value = str(value or "")
    return value if DIGITS.match(value) else to_e164_digits(value)


# Webhook --------------------------------------------------------------------------------------


def verify_signature(raw_body, header, app_secret):
    """True when X-Hub-Signature-256 is the HMAC-SHA256 of the raw body with the app secret."""
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len("sha256=") :])


def process_webhook(payload):
    """Apply a (signature-checked) webhook payload. Malformed parts are logged and skipped."""
    counts = {"statuses": 0, "messages": 0}
    entries = payload.get("entry") if isinstance(payload, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        changes = entry.get("changes") if isinstance(entry, dict) else None
        for change in changes if isinstance(changes, list) else []:
            value = change.get("value") if isinstance(change, dict) else None
            if not isinstance(value, dict):
                continue
            for status in value.get("statuses") or []:
                try:
                    counts["statuses"] += apply_status(status)
                except Exception:  # never fail the whole delivery for one bad item
                    logger.exception("Skipping a malformed WhatsApp status")
            contacts = value.get("contacts") or []
            metadata = value.get("metadata") or {}
            for message in value.get("messages") or []:
                try:
                    if store_inbound(message, contacts, metadata):
                        counts["messages"] += 1
                except Exception:
                    logger.exception("Skipping a malformed WhatsApp message")
    return counts


def _status_error(status):
    errors = status.get("errors") or [{}]
    error = errors[0] if isinstance(errors[0], dict) else {}
    details = (error.get("error_data") or {}).get("details") or error.get("message") or ""
    text = f"WhatsApp error {error.get('code', '?')}: {error.get('title') or 'Delivery failed'}"
    return (f"{text} ({details})" if details and details not in text else text)[:500]


def apply_status(status):
    """Record a sent/delivered/read/failed receipt. Idempotent; unknown ids are ignored."""
    wa_id = str(status.get("id") or "")
    state = status.get("status")
    if not wa_id or state not in {"sent", "delivered", "read", "failed"}:
        return 0
    when = _timestamp(status.get("timestamp"))
    attempts = DeliveryAttempt.objects.filter(channel="whatsapp", provider_message_id=wa_id)
    messages = WhatsAppMessage.objects.filter(wa_message_id=wa_id)
    matched = attempts.count() + messages.count()
    if not matched:
        return 0
    if state in {"delivered", "read"}:
        for queryset in (attempts, messages):
            queryset.filter(delivered_at__isnull=True).update(delivered_at=when)
        messages.exclude(status__in=("read", "failed")).update(status=state)
    if state == "read":
        for queryset in (attempts, messages):
            queryset.filter(read_at__isnull=True).update(read_at=when)
    if state == "sent":
        messages.filter(status="").update(status="sent")
    if state == "failed":
        error = _status_error(status)
        attempts.update(status=DeliveryAttempt.FAILED, error_message=error, next_attempt_at=None)
        messages.update(status="failed", error_message=error)
    return 1


def describe(message):
    """Text shown for an inbound message; non-text types get a short label."""
    kind = message.get("type") or "unknown"
    content = message.get(kind) if isinstance(message.get(kind), dict) else {}
    if kind == "text":
        return str(content.get("body") or "")
    if kind == "button":
        return str(content.get("text") or "[button]")
    if kind == "interactive":
        reply = content.get("button_reply") or content.get("list_reply") or {}
        return str(reply.get("title") or "[interactive]")
    if kind == "reaction":
        return f"[reaction {content.get('emoji', '')}]".replace(" ]", "]")
    if kind == "location":
        label = content.get("name") or content.get("address") or ""
        return f"[location] {label}".strip()
    caption = content.get("caption") if isinstance(content, dict) else ""
    return f"[{kind}] {caption}".strip() if caption else f"[{kind}]"


def _phone_regex(digits):
    """Regex matching a stored phone whose last 6 digits are `digits`' (any formatting)."""
    return r"\D*".join(digits[-6:]) + r"\D*$"


def match_customer(digits):
    """(user, latest order) for a WhatsApp number, matched against order and account
    phones in any formatting."""
    from apps.accounts.models import User
    from apps.orders.models import Order

    pattern = _phone_regex(digits)
    orders = Order.objects.filter(customer_phone__regex=pattern).select_related("user")
    for order in orders.order_by("-created_at")[:200]:
        if to_e164_digits(order.customer_phone) == digits:
            return order.user, order
    for user in User.objects.filter(phone_number__regex=pattern)[:50]:
        if to_e164_digits(user.phone_number) == digits:
            return user, Order.objects.filter(user=user).order_by("-created_at").first()
    return None, None


def conversation_for(digits, contact_name=""):
    conversation, created = WhatsAppConversation.objects.get_or_create(
        customer_number=digits, defaults={"contact_name": contact_name[:160]}
    )
    if created or conversation.user_id is None:
        user, order = match_customer(digits)
        if user is not None:
            conversation.user, conversation.order = user, order
            conversation.save(update_fields=("user", "order"))
    return conversation


def store_inbound(message, contacts, metadata):
    """Store a customer's message and alert staff in-app. Returns the new row, or None
    for a duplicate (Meta retries deliveries)."""
    from .services import emit_staff_event

    wa_id = str(message.get("id") or "")
    sender = _digits(message.get("from"))
    if not wa_id or not sender:
        raise ValueError("Inbound message without id or sender.")
    if WhatsAppMessage.objects.filter(wa_message_id=wa_id).exists():
        return None
    contact_name = ""
    for contact in contacts:
        if isinstance(contact, dict) and _digits(contact.get("wa_id")) == sender:
            contact_name = str((contact.get("profile") or {}).get("name") or "")
    when = _timestamp(message.get("timestamp"))
    with transaction.atomic():
        conversation = conversation_for(sender, contact_name)
        try:
            with transaction.atomic():
                stored = WhatsAppMessage.objects.create(
                    conversation=conversation,
                    direction=WhatsAppMessage.INBOUND,
                    wa_message_id=wa_id,
                    from_number=sender,
                    to_number=_digits(metadata.get("display_phone_number")) or "",
                    contact_name=contact_name[:160],
                    message_type=str(message.get("type") or "unknown")[:30],
                    body=describe(message),
                    timestamp=when,
                )
        except IntegrityError:  # the same message arrived twice at once
            return None
        if contact_name:
            conversation.contact_name = contact_name[:160]
        conversation.last_inbound_at = max(filter(None, (conversation.last_inbound_at, when)))
        conversation.last_message_at = max(filter(None, (conversation.last_message_at, when)))
        conversation.save(update_fields=("contact_name", "last_inbound_at", "last_message_at"))
        customer_name = ""
        if conversation.order_id:
            customer_name = conversation.order.customer_name
        elif conversation.user_id:
            customer_name = conversation.user.get_full_name()
        emit_staff_event(
            "staff_whatsapp_message",
            {
                "conversation_id": conversation.pk,
                "message_id": stored.pk,
                "customer_number": sender,
                "contact_name": contact_name or customer_name,
                "customer_name": customer_name,
                "order_number": conversation.order.order_number if conversation.order_id else "",
                "text": stored.body,
            },
            f"whatsapp:{wa_id}",
        )
    return stored


# Conversations ------------------------------------------------------------------------------


def window_closes_at(conversation):
    if not conversation.last_inbound_at:
        return None
    return conversation.last_inbound_at + SERVICE_WINDOW


def within_service_window(conversation, now=None):
    closes = window_closes_at(conversation)
    return bool(closes and (now or timezone.now()) < closes)


def _configured_provider(config):
    provider = get_provider(config)
    if provider is None or not provider.is_configured():
        raise WhatsAppError(
            "Set the phone number ID and access token in WhatsApp & alert settings first."
        )
    return provider


def _record_outbound(conversation, result, *, body, message_type, user):
    now = timezone.now()
    config = WhatsAppSettings.load()
    message = WhatsAppMessage.objects.create(
        conversation=conversation,
        direction=WhatsAppMessage.OUTBOUND,
        wa_message_id=result.provider_message_id or None,
        from_number=config.business_number_digits or "",
        to_number=conversation.customer_number,
        message_type=message_type,
        body=body,
        timestamp=now,
        status="sent" if result.status == "sent" else "failed",
        error_message=result.error[:500],
        sent_by=user,
    )
    if result.status == "sent":
        WhatsAppConversation.objects.filter(pk=conversation.pk).update(last_message_at=now)
    return message


def send_reply(conversation, text, user):
    """Send free-form text; only allowed within 24 h of the customer's last message."""
    text = (text or "").strip()
    if not text:
        raise WhatsAppError("Write a message first.")
    if not within_service_window(conversation):
        closes = window_closes_at(conversation)
        when = (
            f"closed {timezone.localtime(closes):%d %b %Y, %H:%M}"
            if closes
            else "has not opened (the customer has not messaged you)"
        )
        raise WhatsAppError(
            f"The 24-hour window for free-form replies {when}. Send an approved template instead."
        )
    provider = _configured_provider(WhatsAppSettings.load())
    result = provider.send_text(conversation.customer_number, text[:4096])
    return _record_outbound(conversation, result, body=text, message_type="text", user=user)


def send_template_to_conversation(conversation, event_key, user):
    """Send an approved order template, filled from the conversation's linked order."""
    from .services import order_payload

    config = WhatsAppSettings.load()
    template = config.template_for(event_key)
    definition = WHATSAPP_TEMPLATE_DEFS.get(event_key)
    if template is None or definition is None:
        raise WhatsAppError("That template is not enabled in WhatsApp & alert settings.")
    if not conversation.order_id:
        raise WhatsAppError("Templates need the customer's order, and none is linked.")
    provider = _configured_provider(config)
    params = render(event_key, order_payload(conversation.order))["whatsapp_params"]
    result = provider.send_template(
        conversation.customer_number,
        template.template_name,
        config.template_language or "en",
        params,
    )
    body = fill_template(definition["body"], params)
    return _record_outbound(conversation, result, body=body, message_type="template", user=user)


# Admin tools --------------------------------------------------------------------------------


def check_connection(config):
    """Read the phone number's details from Meta and remember the outcome."""
    provider = _configured_provider(config)
    try:
        info = provider.phone_number_info()
    except GraphError as exc:
        ok, text = False, str(exc)
    else:
        parts = [
            info.get("display_phone_number"),
            info.get("verified_name"),
            info.get("quality_rating") and f"quality {info['quality_rating']}",
            info.get("platform_type") and f"platform {info['platform_type']}",
            info.get("code_verification_status")
            and f"verification {info['code_verification_status']}",
            (info.get("throughput") or {}).get("level")
            and f"throughput {info['throughput']['level']}",
        ]
        ok, text = True, "Connected: " + " · ".join(str(part) for part in parts if part)
    WhatsAppSettings.objects.filter(pk=config.pk).update(
        last_check_at=timezone.now(), last_check_result=text[:1000]
    )
    WhatsAppSettings.invalidate()
    return ok, text


def _require_waba(config):
    if not config.business_account_id:
        raise WhatsAppError("Set the WhatsApp Business Account ID first.")
    return _configured_provider(config)


def sync_templates(config):
    """Update each mapping's Meta status. Returns [(template, status)]."""
    provider = _require_waba(config)
    try:
        remote = provider.list_templates()
    except GraphError as exc:
        raise WhatsAppError(str(exc)) from None
    language = config.template_language or "en"
    by_key = {(t.get("name"), t.get("language")): t for t in remote if isinstance(t, dict)}
    now = timezone.now()
    results = []
    for template in WhatsAppTemplate.objects.filter(settings=config).order_by("id"):
        found = by_key.get((template.template_name, language))
        if found is None:
            template.meta_status, template.meta_rejected_reason = WhatsAppTemplate.MISSING, ""
        else:
            template.meta_status = str(found.get("status") or "")[:20]
            reason = str(found.get("rejected_reason") or "")
            template.meta_rejected_reason = "" if reason == "NONE" else reason[:255]
        template.last_synced_at = now
        template.save(update_fields=("meta_status", "meta_rejected_reason", "last_synced_at"))
        results.append((template, template.meta_status))
    return results


def submit_missing_templates(config):
    """Create every enabled template Meta does not have yet, using the canonical bodies.
    Returns [(template, ok, text)]."""
    provider = _require_waba(config)
    sync_templates(config)
    language = config.template_language or "en"
    results = []
    templates = WhatsAppTemplate.objects.filter(
        settings=config, enabled=True, meta_status=WhatsAppTemplate.MISSING
    ).exclude(template_name="")
    for template in templates.order_by("id"):
        definition = template.definition
        if definition is None:
            continue
        try:
            created = provider.create_template(
                template.template_name, language, definition["body"], definition["samples"]
            )
        except GraphError as exc:
            results.append((template, False, str(exc)))
            continue
        template.meta_status = str(created.get("status") or WhatsAppTemplate.PENDING)[:20]
        template.last_synced_at = timezone.now()
        template.save(update_fields=("meta_status", "last_synced_at"))
        results.append((template, True, f"submitted ({template.meta_status})"))
    return results


def send_test_message(config, number, event_key, user=None):
    """Send an event's template with sample values right away (not via the worker)."""
    digits = to_e164_digits(number)
    if not digits:
        raise WhatsAppError("Enter a valid WhatsApp number with country code.")
    definition = WHATSAPP_TEMPLATE_DEFS.get(event_key)
    template = WhatsAppTemplate.objects.filter(settings=config, event_key=event_key).first()
    if definition is None or template is None or not template.template_name:
        raise WhatsAppError("Choose an event that has a template name.")
    provider = _configured_provider(config)
    result = provider.send_template(
        digits, template.template_name, config.template_language or "en", definition["samples"]
    )
    conversation, _ = WhatsAppConversation.objects.get_or_create(customer_number=digits)
    _record_outbound(
        conversation,
        result,
        body=fill_template(definition["body"], definition["samples"]),
        message_type="template",
        user=user,
    )
    return result
