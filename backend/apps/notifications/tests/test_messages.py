import re
import uuid
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from apps.accounts.validators import to_e164_digits
from apps.notifications.messages import (
    PLACEHOLDER,
    REGISTRY,
    WHATSAPP_TEMPLATE_DEFS,
    absolute_link,
    email_text,
    fill_template,
    format_inr,
    format_pickup,
    placeholder_count,
    render,
)
from apps.notifications.models import Notification, WhatsAppSettings
from apps.notifications.tests.helpers import configure_whatsapp

ORDER_ID = str(uuid.uuid4())
PAYMENT_ID = str(uuid.uuid4())
PICKUP = datetime(2026, 11, 5, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata")).isoformat()
FULL = {
    "order_id": ORDER_ID,
    "order_number": "LZ-20261104-ABC123",
    "customer_name": "Aarav Mehta",
    "grand_total": "2340.00",
    "pickup": PICKUP,
    "status": "pending_payment_verification",
    "items": [{"name": "Pistachio Rose", "variant": "1 kg", "quantity": 1}],
    "payment_id": PAYMENT_ID,
    "reason": "Amount does not match.",
}
KEYS = {
    "title",
    "body",
    "link",
    "audience",
    "email_subject",
    "email_body",
    "event_key",
    "whatsapp_params",
}


def test_registry_covers_every_event_key():
    assert set(REGISTRY) == set(Notification.EVENT_KEYS)


@pytest.mark.parametrize("event_key", Notification.EVENT_KEYS)
@pytest.mark.parametrize("payload", [{}, None, FULL], ids=["empty", "none", "full"])
def test_every_event_renders(event_key, payload):
    message = render(event_key, payload)
    assert set(message) == KEYS
    assert message["title"]
    assert message["link"].startswith("/")
    expected = "staff" if event_key.startswith("staff_") else "customer"
    assert message["audience"] == expected
    for param in message["whatsapp_params"]:
        assert isinstance(param, str) and param and "\n" not in param
    if message["email_subject"]:
        assert message["email_body"]


def test_customer_order_created_copy():
    message = render("order_created", FULL)
    assert message["title"] == "Order LZ-20261104-ABC123 received"
    assert message["body"] == (
        "Pay by UPI on your order page and upload the screenshot — we'll confirm it by hand."
    )
    assert message["link"] == f"/orders/{ORDER_ID}"
    assert message["event_key"] == "order_created"
    assert message["whatsapp_params"] == [
        "Aarav",
        "LZ-20261104-ABC123",
        "₹2,340",
        "Thu 5 Nov, 12 pm",
    ]
    assert render("payment_submitted", FULL)["title"] == "We've got your payment screenshot"


def test_staff_copy_and_admin_links():
    message = render("staff_order_created", FULL)
    assert message["title"] == "New order LZ-20261104-ABC123 · ₹2,340"
    assert message["body"] == "Aarav Mehta · Pistachio Rose ×1 · pickup Thu 5 Nov, 12 pm"
    assert message["link"] == f"/admin/orders/order/{ORDER_ID}/change/"
    payment = render("staff_payment_submitted", FULL)
    assert payment["link"] == f"/admin/payments/payment/{PAYMENT_ID}/change/"
    assert payment["whatsapp_params"] == ["LZ-20261104-ABC123", "Aarav Mehta", "₹2,340"]


def test_staff_items_are_summarised():
    payload = {**FULL, "items": [{"name": f"Cake {i}", "quantity": i} for i in range(1, 6)]}
    body = render("staff_order_created", payload)["body"]
    assert "Cake 1 ×1, Cake 2 ×2, Cake 3 ×3, +2 more" in body


def test_whatsapp_templates_follow_admin_settings(db):
    config = configure_whatsapp()
    assert config.template_for("order_created").template_name == "order_received"
    assert config.template_for("preparing") is None  # disabled by default
    assert config.template_for("payment_verified") is None  # no template at all
    template = config.templates.get(event_key="order_created")
    template.template_name = "custom_received"
    template.save()
    config = WhatsAppSettings.load()
    assert config.template_for("order_created").template_name == "custom_received"
    config.templates.filter(event_key="ready").update(enabled=False)
    WhatsAppSettings.invalidate()
    assert WhatsAppSettings.load().template_for("ready") is None


def test_unknown_event_renders_a_fallback():
    assert render("legacy_event", {})["title"] == "Update from Leeza Cakes"


def test_email_text_uses_frontend_for_customers_and_backend_for_staff(settings):
    settings.FRONTEND_URL = "https://leezacakes.example"
    settings.BACKEND_PUBLIC_URL = "https://api.leezacakes.example"
    customer = email_text(render("ready", FULL))
    assert f"View your order: https://leezacakes.example/orders/{ORDER_ID}" in customer
    assert customer.rstrip().endswith("Leeza Cakes")
    staff = email_text(render("staff_order_created", FULL))
    assert (
        f"Open in the studio: https://api.leezacakes.example/admin/orders/order/{ORDER_ID}/change/"
        in staff
    )
    settings.FRONTEND_URL = ""
    assert absolute_link("/orders/x", "customer") == ""
    assert absolute_link("", "staff") == ""


def test_payment_rejected_includes_studio_note():
    body = render("payment_rejected", FULL)["email_body"]
    assert "Note from the studio: Amount does not match." in body


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2340.00", "₹2,340"),
        (Decimal("123456.5"), "₹1,23,456.50"),
        ("99", "₹99"),
        ("12345678", "₹1,23,45,678"),
        ("-50", "-₹50"),
        (None, ""),
        ("abc", ""),
    ],
)
def test_format_inr(value, expected):
    assert format_inr(value) == expected


def test_format_pickup():
    assert format_pickup(PICKUP) == "Thu 5 Nov, 12 pm"
    evening = datetime(2026, 11, 5, 17, 30, tzinfo=ZoneInfo("Asia/Kolkata")).isoformat()
    assert format_pickup(evening) == "Thu 5 Nov, 5:30 pm"
    assert format_pickup("2026-11-05T04:00:00") == "Thu 5 Nov, 4 am"
    assert format_pickup("not a date") == ""
    assert format_pickup(None) == ""


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("+91 90000 00000", "919000000000"),
        ("+91-98765-43210", "919876543210"),
        ("9876543210", "919876543210"),
        ("09876543210", "919876543210"),
        ("0044 20 7946 0958", "442079460958"),
        ("+1 (415) 555-0100", "14155550100"),
        ("", None),
        (None, None),
        ("12345", None),
    ],
)
def test_to_e164_digits(value, expected):
    assert to_e164_digits(value) == expected


@pytest.mark.parametrize("event_key", list(WHATSAPP_TEMPLATE_DEFS))
def test_template_bodies_match_params(event_key):
    """Body variables, sample values and rendered params can never drift apart."""
    definition = WHATSAPP_TEMPLATE_DEFS[event_key]
    count = placeholder_count(definition["body"])
    assert count == len(render(event_key, FULL)["whatsapp_params"])
    assert count == len(definition["samples"])
    assert sorted(set(PLACEHOLDER.findall(definition["body"])), key=int) == [
        str(n) for n in range(1, count + 1)
    ]
    assert not definition["body"].startswith("{{") and not definition["body"].endswith("}}")
    assert re.fullmatch(r"[a-z0-9_]+", definition["name"])


def test_fill_template():
    body = WHATSAPP_TEMPLATE_DEFS["completed"]["body"]
    assert fill_template(body, ["Aanya", "LZ-1"]).startswith(
        "Hi Aanya, thank you for picking up order LZ-1."
    )
    assert fill_template("{{1}} and {{2}}", ["a"]) == "a and {{2}}"
