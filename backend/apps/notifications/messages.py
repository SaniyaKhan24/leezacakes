"""Notification copy, rendered from the stored payload whenever it is shown or sent.

Each event key maps to a renderer that receives a :class:`Context` built from the payload
and returns the in-app, email and WhatsApp copy. Renderers must cope with partial
payloads (older rows, tests) and never raise.

WhatsApp ``whatsapp_params`` are positional ({{1}}, {{2}}, ...). The canonical template
bodies (submitted to Meta from the admin) live in ``WHATSAPP_TEMPLATE_DEFS`` below, next
to the renderers, and a test keeps the placeholder count equal to the params.
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

CUSTOMER = "customer"
STAFF = "staff"
SIGN_OFF = "With love,\nLeeza Cakes"


def format_inr(value):
    """Format an amount as Indian rupees with Indian digit grouping: ₹1,23,456.50."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    sign = "-" if amount < 0 else ""
    amount = abs(amount).quantize(Decimal("0.01"))
    whole, _, paise = f"{amount:.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join([*groups, tail])
    return f"{sign}₹{whole}" + ("" if paise == "00" else f".{paise}")


def format_pickup(value):
    """'Thu 5 Nov, 12 pm' in the shop's local time, or '' when unknown."""
    if not value:
        return ""
    try:
        moment = datetime.fromisoformat(str(value))
    except ValueError:
        return ""
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    local = timezone.localtime(moment)
    hour = local.hour % 12 or 12
    clock = f"{hour}:{local.minute:02d}" if local.minute else str(hour)
    meridiem = "am" if local.hour < 12 else "pm"
    return f"{local:%a} {local.day} {local:%b}, {clock} {meridiem}"


def _admin_path(name, object_id, fallback):
    try:
        if object_id:
            return reverse(name, args=[object_id])
    except NoReverseMatch:
        pass
    return fallback


class Context:
    """Read-only view of a payload with safe, formatted accessors."""

    def __init__(self, payload):
        self.payload = payload if isinstance(payload, dict) else {}

    def get(self, key, default=""):
        value = self.payload.get(key)
        return default if value in (None, "") else value

    @property
    def order_number(self):
        return str(self.get("order_number"))

    @property
    def order_label(self):
        return f"order {self.order_number}" if self.order_number else "your order"

    @property
    def customer_name(self):
        return str(self.get("customer_name", "a customer"))

    @property
    def first_name(self):
        name = str(self.get("customer_name")).split()
        return name[0] if name else "there"

    @property
    def total(self):
        return format_inr(self.get("grand_total", None))

    @property
    def pickup(self):
        return format_pickup(self.get("pickup"))

    @property
    def items(self):
        rows = self.payload.get("items") or []
        labels = [
            f"{row.get('name', 'Cake')} ×{row.get('quantity', 1)}"
            for row in rows
            if isinstance(row, dict)
        ]
        if len(labels) > 3:
            labels = [*labels[:3], f"+{len(labels) - 3} more"]
        return ", ".join(labels)

    @property
    def order_link(self):
        order_id = self.get("order_id")
        return f"/orders/{order_id}" if order_id else "/orders"

    @property
    def admin_order_link(self):
        return _admin_path(
            "admin:orders_order_change", self.get("order_id"), "/admin/orders/order/"
        )

    @property
    def admin_conversation_link(self):
        return _admin_path(
            "admin:notifications_whatsappconversation_change",
            self.get("conversation_id"),
            "/admin/notifications/whatsappconversation/",
        )

    @property
    def admin_payment_link(self):
        return _admin_path(
            "admin:payments_payment_change", self.get("payment_id"), "/admin/payments/payment/"
        )


def _join(*parts, sep=" · "):
    return sep.join(part for part in parts if part)


def _with(prefix, value):
    return f"{prefix}{value}" if value else ""


def _cap(text):
    return text[:1].upper() + text[1:]


# Customer events ---------------------------------------------------------------------------


def order_created(c):
    return {
        "title": _join("Order", c.order_number, "received", sep=" "),
        "body": (
            "Pay by UPI on your order page and upload the screenshot — we'll confirm it by hand."
        ),
        "link": c.order_link,
        "email_subject": f"We've received {c.order_label}",
        "email_body": (
            f"Hi {c.first_name},\n\n"
            f"Thank you for ordering from Leeza Cakes! We've received {c.order_label}"
            f"{_with(' for ', c.total)}{_with(', pickup ', c.pickup)}.\n\n"
            "Next step: pay by UPI on your order page and upload the payment screenshot. "
            "We check every payment by hand and will confirm your order as soon as it's "
            "verified."
        ),
        "whatsapp_params": [c.first_name, c.order_number, c.total, c.pickup],
    }


def payment_submitted(c):
    return {
        "title": "We've got your payment screenshot",
        "body": f"Thank you! We'll match it to our UPI account and confirm {c.order_label} soon.",
        "link": c.order_link,
        "email_subject": f"Payment screenshot received for {c.order_label}",
        "email_body": (
            f"Hi {c.first_name},\n\n"
            f"Thank you! We've received your payment screenshot for {c.order_label}. "
            "We'll match it against our UPI account and let you know as soon as your order "
            "is confirmed."
        ),
        "whatsapp_params": [c.first_name, c.order_number],
    }


def payment_verified(c):
    # The order_confirmed message that follows covers email and WhatsApp.
    return {
        "title": _join("Payment verified for", c.order_number, sep=" "),
        "body": f"We've received your payment{_with(' of ', c.total)} — thank you!",
        "link": c.order_link,
        "email_subject": None,
        "email_body": None,
        "whatsapp_params": [],
    }


def order_confirmed(c):
    return {
        "title": _join("Order", c.order_number, "is confirmed", sep=" "),
        "body": f"Payment verified — your cake is booked{_with(' for pickup on ', c.pickup)}.",
        "link": c.order_link,
        "email_subject": f"Your {c.order_label} is confirmed",
        "email_body": (
            f"Hi {c.first_name},\n\n"
            f"Your payment is verified and {c.order_label} is confirmed"
            f"{_with(' for pickup on ', c.pickup)}. We'll let you know when we start "
            "baking and again when it's ready."
        ),
        "whatsapp_params": [c.first_name, c.order_number, c.pickup],
    }


def preparing(c):
    return {
        "title": f"We're baking {c.order_label}",
        "body": "Your cake is in the oven and being finished by hand.",
        "link": c.order_link,
        "email_subject": f"We're baking {c.order_label}",
        "email_body": (
            f"Hi {c.first_name},\n\n"
            f"Good news: we've started on {c.order_label}. Your cake is in the oven and "
            "being finished by hand. We'll message you when it's ready for pickup."
        ),
        "whatsapp_params": [c.first_name, c.order_number],
    }


def ready(c):
    slot = f"in your pickup slot ({c.pickup})" if c.pickup else "during your pickup slot"
    return {
        "title": _join("Order", c.order_number, "is ready for pickup", sep=" "),
        "body": f"Come by {slot} and show your order number at the counter.",
        "link": c.order_link,
        "email_subject": f"{_cap(c.order_label)} is ready for pickup",
        "email_body": (
            f"Hi {c.first_name},\n\n"
            f"{_cap(c.order_label)} is ready! Come by {slot} and show your order number "
            "at the counter."
        ),
        "whatsapp_params": [c.first_name, c.order_number, c.pickup],
    }


def completed(c):
    return {
        "title": "Enjoy your cake!",
        "body": f"{_cap(c.order_label)} is collected. Thank you for celebrating with us.",
        "link": c.order_link,
        "email_subject": "Thank you for celebrating with Leeza Cakes",
        "email_body": (
            f"Hi {c.first_name},\n\n"
            f"Thank you for picking up {c.order_label}. We hope it made the day special — "
            "we'd love to bake for you again."
        ),
        "whatsapp_params": [c.first_name, c.order_number],
    }


def payment_rejected(c):
    reason = str(c.get("reason"))
    return {
        "title": "Please re-upload your payment screenshot",
        "body": f"We couldn't match the screenshot for {c.order_label} to a UPI payment. "
        "Upload a clear one that shows the amount and UTR.",
        "link": c.order_link,
        "email_subject": f"Action needed: payment screenshot for {c.order_label}",
        "email_body": (
            f"Hi {c.first_name},\n\n"
            f"We couldn't match the payment screenshot for {c.order_label} to a UPI payment "
            "we received."
            f"{_with(chr(10) * 2 + 'Note from the studio: ', reason)}\n\n"
            "Please upload a clear screenshot on your order page that shows the amount, the "
            "date and the UPI reference (UTR) number."
        ),
        "whatsapp_params": [c.first_name, c.order_number],
    }


# Staff events ------------------------------------------------------------------------------


def staff_order_created(c):
    title = _join(_join("New order", c.order_number, sep=" "), c.total)
    body = _join(c.customer_name, c.items, _with("pickup ", c.pickup))
    return {
        "title": title,
        "body": body,
        "link": c.admin_order_link,
        "email_subject": title,
        "email_body": (
            f"New order {c.order_number} has been placed.\n\n"
            f"Customer: {c.customer_name}\n"
            f"Items: {c.items or '-'}\n"
            f"Total: {c.total or '-'}\n"
            f"Pickup: {c.pickup or '-'}\n\n"
            "Payment is pending: the customer will upload a UPI screenshot for review."
        ),
        "whatsapp_params": [
            c.order_number,
            c.customer_name,
            c.total,
            c.items or "-",
            c.pickup or "-",
        ],
    }


def staff_payment_submitted(c):
    title = _join(_join("Payment screenshot for", c.order_number, sep=" "), c.total)
    return {
        "title": title,
        "body": _join(c.customer_name, "check it against the UPI account and verify"),
        "link": c.admin_payment_link,
        "email_subject": title,
        "email_body": (
            f"{c.customer_name} uploaded a UPI payment screenshot for order "
            f"{c.order_number}.\n\n"
            f"Amount due: {c.total or '-'}\n"
            f"Pickup: {c.pickup or '-'}\n\n"
            "Check it against the UPI account, then accept and verify it in the studio."
        ),
        "whatsapp_params": [c.order_number, c.customer_name, c.total],
    }


def staff_whatsapp_message(c):
    sender = str(c.get("contact_name") or c.get("customer_name"))
    if not sender:
        number = str(c.get("customer_number"))
        sender = f"+{number}" if number else "a customer"
    text = " ".join(str(c.get("text", "[message]")).split())
    body = text if len(text) <= 140 else f"{text[:139].rstrip()}…"
    return {
        "title": f"WhatsApp from {sender}",
        "body": body,
        "link": c.admin_conversation_link,
        # In-app only: replying on WhatsApp about a WhatsApp message would loop.
        "email_subject": None,
        "email_body": None,
        "whatsapp_params": [],
    }


REGISTRY = {
    "order_created": (CUSTOMER, order_created),
    "payment_submitted": (CUSTOMER, payment_submitted),
    "payment_verified": (CUSTOMER, payment_verified),
    "order_confirmed": (CUSTOMER, order_confirmed),
    "preparing": (CUSTOMER, preparing),
    "ready": (CUSTOMER, ready),
    "completed": (CUSTOMER, completed),
    "payment_rejected": (CUSTOMER, payment_rejected),
    "staff_order_created": (STAFF, staff_order_created),
    "staff_payment_submitted": (STAFF, staff_payment_submitted),
    "staff_whatsapp_message": (STAFF, staff_whatsapp_message),
}

# Canonical WhatsApp templates: default name, body submitted to Meta (category UTILITY)
# and sample values for Meta's review. Variables follow the renderer's whatsapp_params.
WHATSAPP_TEMPLATE_DEFS = {
    "order_created": {
        "name": "order_received",
        "enabled": True,
        "body": (
            "Hi {{1}}, thank you for ordering from Leeza Cakes! We've received order {{2}} "
            "for {{3}}, pickup {{4}}. Please pay by UPI on your order page and upload the "
            "screenshot, and we'll confirm your order by hand."
        ),
        "samples": ["Aanya", "LZ-20261104-A1B2C3", "₹2,340", "Thu 5 Nov, 12 pm"],
    },
    "payment_submitted": {
        "name": "payment_received",
        "enabled": True,
        "body": (
            "Hi {{1}}, we've received your payment screenshot for order {{2}}. We'll match "
            "it with our UPI account and confirm your order shortly."
        ),
        "samples": ["Aanya", "LZ-20261104-A1B2C3"],
    },
    "payment_rejected": {
        "name": "payment_rejected",
        "enabled": True,
        "body": (
            "Hi {{1}}, we couldn't match the payment screenshot for order {{2}} to a UPI "
            "payment. Please upload a clear screenshot on your order page showing the "
            "amount, date and UTR number."
        ),
        "samples": ["Aanya", "LZ-20261104-A1B2C3"],
    },
    "order_confirmed": {
        "name": "order_confirmed",
        "enabled": True,
        "body": (
            "Hi {{1}}, your payment is verified and order {{2}} is confirmed for pickup on "
            "{{3}}. We'll message you when it's ready."
        ),
        "samples": ["Aanya", "LZ-20261104-A1B2C3", "Thu 5 Nov, 12 pm"],
    },
    "preparing": {
        "name": "order_preparing",
        "enabled": False,
        "body": ("Hi {{1}}, we've started baking order {{2}}. We'll message you when it's ready."),
        "samples": ["Aanya", "LZ-20261104-A1B2C3"],
    },
    "ready": {
        "name": "order_ready",
        "enabled": True,
        "body": (
            "Hi {{1}}, order {{2}} is ready! Please come by for your pickup slot ({{3}}) and "
            "show your order number at the counter."
        ),
        "samples": ["Aanya", "LZ-20261104-A1B2C3", "Thu 5 Nov, 12 pm"],
    },
    "completed": {
        "name": "order_completed",
        "enabled": True,
        "body": (
            "Hi {{1}}, thank you for picking up order {{2}}. We hope it made your day "
            "special, and we'd love to bake for you again!"
        ),
        "samples": ["Aanya", "LZ-20261104-A1B2C3"],
    },
    "staff_order_created": {
        "name": "staff_new_order",
        "enabled": True,
        "body": (
            "New order {{1}} from {{2}} for {{3}}. Items: {{4}}. Pickup: {{5}}. Payment is "
            "pending verification in the studio."
        ),
        "samples": [
            "LZ-20261104-A1B2C3",
            "Aanya Rao",
            "₹2,340",
            "Pistachio Rose ×1",
            "Thu 5 Nov, 12 pm",
        ],
    },
    "staff_payment_submitted": {
        "name": "staff_payment_submitted",
        "enabled": True,
        "body": (
            "Payment screenshot uploaded for order {{1}} by {{2}} ({{3}}). Please check the "
            "UPI account and verify it in the studio."
        ),
        "samples": ["LZ-20261104-A1B2C3", "Aanya Rao", "₹2,340"],
    },
}

PLACEHOLDER = re.compile(r"\{\{(\d+)\}\}")


def placeholder_count(body):
    return len(set(PLACEHOLDER.findall(body)))


def fill_template(body, params):
    """The text a customer sees for a template body filled with params."""
    return PLACEHOLDER.sub(
        lambda match: (
            params[int(match.group(1)) - 1]
            if int(match.group(1)) <= len(params)
            else match.group(0)
        ),
        body,
    )


def _clean_param(value):
    """WhatsApp rejects parameters with newlines, tabs or 4+ consecutive spaces."""
    text = " ".join(str(value).split())
    return text or "-"


def render(event_key, payload):
    """Render the copy for an event.

    Returns ``event_key``, ``title``, ``body``, ``link`` (site-relative), ``audience``,
    ``email_subject``/``email_body`` (None when the event is not emailed) and
    ``whatsapp_params``. The WhatsApp template name comes from the admin settings
    (``WhatsAppSettings.template_for``) at send time.
    """
    audience, renderer = REGISTRY.get(event_key, (CUSTOMER, None))
    context = Context(payload)
    if renderer is None:
        message = {
            "title": "Update from Leeza Cakes",
            "body": "",
            "link": "",
            "email_subject": None,
            "email_body": None,
            "whatsapp_params": [],
        }
    else:
        message = renderer(context)
    message["event_key"] = event_key
    message["audience"] = audience
    message["whatsapp_params"] = [_clean_param(p) for p in message["whatsapp_params"]]
    return message


def absolute_link(link, audience):
    """Absolute URL for a rendered link: frontend for customers, backend for staff."""
    if not link:
        return ""
    base = settings.BACKEND_PUBLIC_URL if audience == STAFF else settings.FRONTEND_URL
    return f"{base}{link}" if base else ""


def email_text(message):
    """Plain-text email body with the absolute link and sign-off."""
    parts = [message["email_body"]]
    url = absolute_link(message["link"], message["audience"])
    if url:
        label = "Open in the studio" if message["audience"] == STAFF else "View your order"
        parts.append(f"{label}: {url}")
    if message["audience"] == CUSTOMER:
        parts.append(SIGN_OFF)
    return "\n\n".join(parts) + "\n"
