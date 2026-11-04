"""The WhatsApp webhook, conversations in admin and replies within the 24-hour window."""

import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import (
    DeliveryAttempt,
    Notification,
    WhatsAppConversation,
    WhatsAppMessage,
)
from apps.notifications.services import emit_event, order_payload
from apps.notifications.tests.helpers import configure_whatsapp
from apps.notifications.whatsapp_services import describe, verify_signature
from apps.orders.models import Order

URL = "/api/v1/notifications/whatsapp/webhook/"
SECRET = "meta-app-secret"
TOKEN = "EAAG-token-xyz"


def sign(raw, secret=SECRET):
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def post(payload, secret=SECRET, signature=None):
    raw = json.dumps(payload).encode() if not isinstance(payload, bytes) else payload
    headers = {}
    if signature is not False:
        headers["HTTP_X_HUB_SIGNATURE_256"] = signature or sign(raw, secret)
    return Client().post(URL, raw, content_type="application/json", **headers)


def envelope(value):
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": value}]}]}


def inbound(wa_id="wamid.IN1", sender="919876543210", text="Hi! Is my cake ready?", **extra):
    message = {
        "from": sender,
        "id": wa_id,
        "timestamp": str(int(timezone.now().timestamp())),
        "type": "text",
        "text": {"body": text},
        **extra,
    }
    return envelope(
        {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "919000000000", "phone_number_id": "1"},
            "contacts": [{"profile": {"name": "Aanya Rao"}, "wa_id": sender}],
            "messages": [message],
        }
    )


@pytest.fixture
def webhook(db):
    return configure_whatsapp(app_secret=SECRET)


@pytest.fixture
def customer_order(db):
    user = User.objects.create_user(email="aanya@example.com", first_name="Aanya")
    return Order.objects.create(
        order_number="LZ-WA-1",
        user=user,
        customer_name="Aanya Rao",
        customer_phone="+91 98765-43210",
        pickup_slot_start=timezone.now(),
        pickup_slot_end=timezone.now(),
        subtotal=Decimal("2340.00"),
        tax_total=Decimal("0.00"),
        grand_total=Decimal("2340.00"),
        idempotency_key="wa-1",
        request_fingerprint="f",
    )


# Verification -------------------------------------------------------------------------------


def test_verification_handshake(webhook):
    client = Client()
    good = client.get(
        URL,
        {
            "hub.mode": "subscribe",
            "hub.verify_token": webhook.webhook_verify_token,
            "hub.challenge": "1158201444",
        },
    )
    assert good.status_code == 200
    assert good.content == b"1158201444"
    assert good["Content-Type"].startswith("text/plain")
    bad = client.get(
        URL, {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"}
    )
    assert bad.status_code == 403
    wrong_mode = {"hub.mode": "unsubscribe", "hub.verify_token": webhook.webhook_verify_token}
    assert client.get(URL, wrong_mode).status_code == 403


def test_signature_is_required(webhook):
    assert post(inbound(), signature=False).status_code == 403
    assert post(inbound(), signature="sha256=deadbeef").status_code == 403
    assert post(inbound(), secret="other-secret").status_code == 403
    assert post(inbound(), signature="md5=abc").status_code == 403
    assert not WhatsAppMessage.objects.exists()


def test_missing_app_secret_rejects_everything(db):
    configure_whatsapp(app_secret="")
    assert post(inbound(), secret="").status_code == 403
    assert not verify_signature(b"{}", sign(b"{}", "x"), "")


def test_signed_garbage_is_acknowledged(webhook):
    assert post(b"not json").status_code == 200
    assert post({"entry": "nope"}).status_code == 200
    assert post({"entry": [{"changes": [{"value": "x"}, "y"]}, 5]}).status_code == 200
    broken = envelope({"statuses": [{"id": None}, "bad"], "messages": [{"type": "text"}]})
    assert post(broken).status_code == 200


# Delivery receipts --------------------------------------------------------------------------


def _sent_attempt(user, wa_id):
    notification = emit_event("order_created", user=user, deduplication_key=f"n:{wa_id}")
    return DeliveryAttempt.objects.filter(notification=notification, channel="whatsapp").update(
        status=DeliveryAttempt.SENT, provider_message_id=wa_id, next_attempt_at=None
    )


def status(wa_id, state, ts=1767225600, **extra):
    return envelope({"statuses": [{"id": wa_id, "status": state, "timestamp": str(ts), **extra}]})


def test_statuses_update_delivery_attempts(webhook):
    user = User.objects.create_user(email="s@example.com", phone_number="9876543210")
    _sent_attempt(user, "wamid.OUT1")
    assert post(status("wamid.OUT1", "sent")).status_code == 200
    assert post(status("wamid.OUT1", "delivered", 1767225600)).status_code == 200
    attempt = DeliveryAttempt.objects.get(provider_message_id="wamid.OUT1")
    assert attempt.delivered_at.timestamp() == 1767225600 and attempt.read_at is None
    post(status("wamid.OUT1", "read", 1767225700))
    post(status("wamid.OUT1", "delivered", 1767225999))  # late duplicate: no change
    attempt.refresh_from_db()
    assert attempt.delivered_at.timestamp() == 1767225600
    assert attempt.read_at.timestamp() == 1767225700
    assert attempt.status == DeliveryAttempt.SENT
    assert post(status("wamid.UNKNOWN", "read")).status_code == 200  # ignored


def test_failed_status_marks_attempt_failed(webhook):
    user = User.objects.create_user(email="f@example.com", phone_number="9876543210")
    _sent_attempt(user, "wamid.OUT2")
    errors = [
        {
            "code": 131026,
            "title": "Message undeliverable",
            "error_data": {"details": "Receiver is incapable of receiving this message"},
        }
    ]
    post(status("wamid.OUT2", "failed", errors=errors))
    attempt = DeliveryAttempt.objects.get(provider_message_id="wamid.OUT2")
    assert attempt.status == DeliveryAttempt.FAILED
    assert attempt.error_message == (
        "WhatsApp error 131026: Message undeliverable "
        "(Receiver is incapable of receiving this message)"
    )
    assert attempt.next_attempt_at is None


def test_delivery_admin_shows_receipt_columns(webhook):
    user = User.objects.create_superuser(email="boss@example.com", password="Boss-pass-123!")
    _sent_attempt(user, "wamid.ADMIN")
    post(status("wamid.ADMIN", "read"))
    client = Client()
    client.force_login(user)
    html = client.get("/admin/notifications/deliveryattempt/").content.decode()
    assert "Delivered at" in html and "Read at" in html


# Customer messages --------------------------------------------------------------------------


def test_inbound_message_is_stored_linked_and_alerts_staff(webhook, customer_order):
    staff = User.objects.create_user(email="staff@example.com", is_staff=True)
    configure_whatsapp(staff_alert_emails=["owner@example.com"], app_secret=SECRET)
    assert post(inbound()).status_code == 200
    message = WhatsAppMessage.objects.get()
    assert message.direction == WhatsAppMessage.INBOUND
    assert message.from_number == "919876543210" and message.to_number == "919000000000"
    assert message.body == "Hi! Is my cake ready?" and message.contact_name == "Aanya Rao"
    conversation = message.conversation
    assert conversation.customer_number == "919876543210"
    assert conversation.user == customer_order.user
    assert conversation.order == customer_order
    assert conversation.last_inbound_at is not None

    alert = Notification.objects.get(user=staff, event_key="staff_whatsapp_message")
    assert alert.audience == Notification.STAFF
    assert alert.rendered["title"] == "WhatsApp from Aanya Rao"
    assert alert.rendered["body"] == "Hi! Is my cake ready?"
    assert alert.rendered["link"] == (
        f"/admin/notifications/whatsappconversation/{conversation.pk}/change/"
    )
    # In-app only: no staff email or WhatsApp for incoming messages (no loops).
    assert not DeliveryAttempt.objects.filter(notification__event_key="staff_whatsapp_message")

    assert post(inbound()).status_code == 200  # Meta retry: stored once
    assert WhatsAppMessage.objects.count() == 1
    assert Notification.objects.filter(event_key="staff_whatsapp_message").count() == 2


def test_inbound_from_unknown_number_and_long_text(webhook):
    text = "x" * 200
    post(inbound(wa_id="wamid.IN2", sender="14155550100", text=text))
    conversation = WhatsAppConversation.objects.get()
    assert conversation.user is None and conversation.order is None
    alert = Notification.objects.get(user__isnull=True, event_key="staff_whatsapp_message")
    assert alert.rendered["body"] == "x" * 139 + "…"
    assert alert.rendered["title"] == "WhatsApp from Aanya Rao"


def test_inbound_matches_account_phone(webhook):
    user = User.objects.create_user(email="acct@example.com", phone_number="98765 43210")
    post(inbound(wa_id="wamid.IN3"))
    assert WhatsAppConversation.objects.get().user == user


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ({"type": "image", "image": {"caption": "the design"}}, "[image] the design"),
        ({"type": "image", "image": {}}, "[image]"),
        ({"type": "location", "location": {"name": "Studio"}}, "[location] Studio"),
        ({"type": "reaction", "reaction": {"emoji": "👍"}}, "[reaction 👍]"),
        ({"type": "button", "button": {"text": "Yes"}}, "Yes"),
        (
            {"type": "interactive", "interactive": {"button_reply": {"title": "Confirm"}}},
            "Confirm",
        ),
        ({"type": "sticker"}, "[sticker]"),
    ],
)
def test_non_text_messages_are_described(message, expected):
    assert describe(message) == expected


def test_staff_alert_copy_without_names():
    from apps.notifications.messages import render

    assert render("staff_whatsapp_message", {"customer_number": "14155550100"})["title"] == (
        "WhatsApp from +14155550100"
    )
    assert render("staff_whatsapp_message", {})["title"] == "WhatsApp from a customer"


# Conversations in admin ---------------------------------------------------------------------


@pytest.fixture
def studio(db):
    user = User.objects.create_superuser(email="owner@example.com", password="Owner-pass-123!")
    client = Client()
    client.force_login(user)
    return client


def _conversation(webhook, customer_order):
    configure_whatsapp(app_secret=SECRET, access_token=TOKEN, phone_number_id="555")
    post(inbound())
    return WhatsAppConversation.objects.get()


def test_conversation_list_and_thread(studio, webhook, customer_order):
    conversation = _conversation(webhook, customer_order)
    listing = studio.get("/admin/notifications/whatsappconversation/").content.decode()
    assert "Aanya Rao" in listing and "+91 98765 43210" in listing
    assert "<strong>1</strong>" in listing  # unread
    assert "← Hi! Is my cake ready?" in listing and "LZ-WA-1" in listing
    page = studio.get(f"/admin/notifications/whatsappconversation/{conversation.pk}/change/")
    html = page.content.decode()
    assert page.status_code == 200
    assert "WhatsApp with Aanya Rao" in html and "Hi! Is my cake ready?" in html
    assert "Send reply" in html
    assert WhatsAppMessage.objects.get().read_by_staff_at is not None  # opened = read


def test_reply_within_window(studio, webhook, customer_order, graph):
    conversation = _conversation(webhook, customer_order)
    graph.respond("POST", "/555/messages", {"messages": [{"id": "wamid.REPLY"}]})
    url = f"/admin/notifications/whatsappconversation/{conversation.pk}/"
    assert studio.get(f"{url}reply/").status_code == 405
    response = studio.post(f"{url}reply/", {"text": "Yes, it's ready at 5 pm!"}, follow=True)
    assert [str(m) for m in response.context["messages"]] == ["Sent."]
    assert graph.calls[0]["body"] == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "919876543210",
        "type": "text",
        "text": {"preview_url": False, "body": "Yes, it's ready at 5 pm!"},
    }
    reply = WhatsAppMessage.objects.get(direction=WhatsAppMessage.OUTBOUND)
    assert reply.wa_message_id == "wamid.REPLY" and reply.status == "sent"
    assert reply.sent_by.email == "owner@example.com"
    # Receipts for replies update the stored message too.
    post(status("wamid.REPLY", "read"))
    reply.refresh_from_db()
    assert reply.status == "read" and reply.read_at and reply.delivered_at
    assert "Yes, it&#x27;s ready at 5 pm!" in response.content.decode()


def test_reply_failure_is_recorded(studio, webhook, customer_order, graph):
    conversation = _conversation(webhook, customer_order)
    graph.respond("POST", "/messages", {"error": {"message": "Re-engagement required"}}, 400)
    url = f"/admin/notifications/whatsappconversation/{conversation.pk}/reply/"
    response = studio.post(url, {"text": "Hello"}, follow=True)
    assert [str(m) for m in response.context["messages"]] == [
        "Not sent: Graph API error 400: Re-engagement required"
    ]
    assert WhatsAppMessage.objects.get(direction="outbound").status == "failed"
    response = studio.post(url, {"text": ""}, follow=True)
    assert "Write a message" in str(list(response.context["messages"])[0])


def test_reply_outside_window_offers_templates(studio, webhook, customer_order, graph):
    conversation = _conversation(webhook, customer_order)
    WhatsAppConversation.objects.filter(pk=conversation.pk).update(
        last_inbound_at=timezone.now() - timedelta(hours=25)
    )
    url = f"/admin/notifications/whatsappconversation/{conversation.pk}/"
    html = studio.get(f"{url}change/").content.decode()
    assert "Free-form replies are closed." in html and "Send template" in html
    response = studio.post(f"{url}reply/", {"text": "Hello"}, follow=True)
    text = str(list(response.context["messages"])[0])
    assert text.startswith("The 24-hour window for free-form replies closed")
    assert graph.calls == []

    graph.respond("POST", "/555/messages", {"messages": [{"id": "wamid.TPL"}]})
    response = studio.post(f"{url}send-template/", {"event_key": "ready"}, follow=True)
    assert [str(m) for m in response.context["messages"]] == ["Sent."]
    body = graph.calls[0]["body"]
    assert body["type"] == "template" and body["template"]["name"] == "order_ready"
    params = [p["text"] for p in body["template"]["components"][0]["parameters"]]
    expected = order_payload(customer_order)
    assert params[:2] == ["Aanya", expected["order_number"]]
    stored = WhatsAppMessage.objects.get(wa_message_id="wamid.TPL")
    assert stored.message_type == "template" and "order LZ-WA-1 is ready" in stored.body
    response = studio.post(f"{url}send-template/", {"event_key": "preparing"}, follow=True)
    assert "not enabled" in str(list(response.context["messages"])[0])


def test_template_needs_a_linked_order_and_window_needs_a_message(studio, db, graph):
    configure_whatsapp(access_token=TOKEN, phone_number_id="555")
    conversation = WhatsAppConversation.objects.create(customer_number="14155550100")
    url = f"/admin/notifications/whatsappconversation/{conversation.pk}/"
    html = studio.get(f"{url}change/").content.decode()
    assert "has not messaged you yet" in html and "No order is linked" in html
    response = studio.post(f"{url}send-template/", {"event_key": "ready"}, follow=True)
    assert "none is linked" in str(list(response.context["messages"])[0])
    response = studio.post(f"{url}reply/", {"text": "Hi"}, follow=True)
    assert "has not opened" in str(list(response.context["messages"])[0])


def test_reply_needs_credentials(studio, webhook, customer_order):
    post(inbound())
    conversation = WhatsAppConversation.objects.get()
    response = studio.post(
        f"/admin/notifications/whatsappconversation/{conversation.pk}/reply/",
        {"text": "Hi"},
        follow=True,
    )
    assert "Set the phone number ID and access token" in str(list(response.context["messages"])[0])


def test_view_only_staff_cannot_reply(webhook, customer_order):
    from django.contrib.auth.models import Permission

    post(inbound())
    conversation = WhatsAppConversation.objects.get()
    staff = User.objects.create_user(email="viewer@example.com", is_staff=True)
    staff.user_permissions.add(Permission.objects.get(codename="view_whatsappconversation"))
    client = Client()
    client.force_login(staff)
    url = f"/admin/notifications/whatsappconversation/{conversation.pk}/"
    page = client.get(f"{url}change/")
    assert page.status_code == 200 and "Send reply" not in page.content.decode()
    assert client.post(f"{url}reply/", {"text": "Hi"}).status_code == 403
    nobody = User.objects.create_user(email="nobody@example.com", is_staff=True)
    client.force_login(nobody)
    assert client.get(f"{url}change/").status_code == 403
