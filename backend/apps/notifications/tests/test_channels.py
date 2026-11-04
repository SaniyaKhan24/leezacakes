import json
import smtplib
import urllib.error
import urllib.request
from io import BytesIO

import pytest

from apps.notifications.channels import email as email_channel
from apps.notifications.channels import whatsapp as whatsapp_channel
from apps.notifications.messages import render
from apps.notifications.models import DeliveryAttempt, Notification
from apps.notifications.services import dispatch_notification, emit_event, emit_staff_event
from apps.notifications.tests.helpers import configure_whatsapp
from apps.payments.tests.test_models import order  # noqa: F401

TOKEN = "EAAG-secret-token-123"


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def whatsapp(db, settings, monkeypatch):
    configure_whatsapp(
        sending_enabled=True,
        provider="meta_cloud",
        access_token=TOKEN,
        phone_number_id="1098765432",
        api_version="v26.0",
        template_language="en",
    )
    settings.EMAIL_PROVIDER_ENABLED = False
    calls = []
    state = {"response": b'{"messages": [{"id": "wamid.HBgM"}]}', "error": None}

    def fake_urlopen(request, timeout=None):
        calls.append({"request": request, "timeout": timeout})
        if state["error"] is not None:
            raise state["error"]
        return FakeResponse(state["response"])

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return {"calls": calls, "state": state}


def _order_notification(order, event_key="order_created"):  # noqa: F811
    from apps.notifications.services import order_payload

    return emit_event(
        event_key,
        user=order.user,
        payload=order_payload(order),
        deduplication_key=f"order:{order.id}:{event_key}",
    )


def test_whatsapp_cloud_api_request(order, whatsapp):  # noqa: F811
    order.customer_name = "Aarav Mehta"
    order.customer_phone = "+91 98765-43210"
    order.save()
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="whatsapp")
    assert attempt.status == DeliveryAttempt.SENT
    assert attempt.provider_message_id == "wamid.HBgM"
    assert attempt.recipient == "919876543210"
    (call,) = whatsapp["calls"]
    request = call["request"]
    assert call["timeout"] == 10
    assert request.full_url == "https://graph.facebook.com/v26.0/1098765432/messages"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == f"Bearer {TOKEN}"
    assert request.get_header("Content-type") == "application/json"
    message = render("order_created", notification.payload)
    assert json.loads(request.data) == {
        "messaging_product": "whatsapp",
        "to": "919876543210",
        "type": "template",
        "template": {
            "name": "order_received",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "Aarav"},
                        {"type": "text", "text": "LZ-TEST-1"},
                        {"type": "text", "text": "₹100"},
                        {"type": "text", "text": message["whatsapp_params"][3]},
                    ],
                }
            ],
        },
    }
    dispatch_notification(notification.pk)
    assert len(whatsapp["calls"]) == 1  # SENT attempts are never repeated


def test_whatsapp_falls_back_to_account_phone(order, whatsapp):  # noqa: F811
    order.customer_phone = ""
    order.save()
    order.user.phone_number = "98765 00000"
    order.user.save()
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    assert notification.attempts.get(channel="whatsapp").recipient == "919876500000"


def test_whatsapp_http_error_records_graph_message_without_token(order, whatsapp):  # noqa: F811
    error = {
        "error": {
            "message": f"(#132001) Template name does not exist in the translation {TOKEN}",
            "type": "OAuthException",
            "code": 132001,
            "error_data": {"details": "template name (order_received) does not exist in en"},
        }
    }
    whatsapp["state"]["error"] = urllib.error.HTTPError(
        "https://graph.facebook.com", 404, "Not Found", {}, BytesIO(json.dumps(error).encode())
    )
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="whatsapp")
    assert attempt.status == DeliveryAttempt.FAILED
    assert attempt.error_message.startswith("Graph API error 132001: (#132001) Template name")
    assert "does not exist in en" in attempt.error_message
    assert TOKEN not in attempt.error_message
    assert "[redacted]" in attempt.error_message
    # A failed attempt is retried on the next dispatch.
    whatsapp["state"]["error"] = None
    dispatch_notification(notification.pk)
    attempt.refresh_from_db()
    assert attempt.status == DeliveryAttempt.SENT
    assert attempt.attempt_count == 2
    assert attempt.error_message == ""


def test_whatsapp_http_error_without_json_body(order, whatsapp):  # noqa: F811
    whatsapp["state"]["error"] = urllib.error.HTTPError(
        "https://graph.facebook.com", 500, "Server Error", {}, BytesIO(b"<html>")
    )
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    assert notification.attempts.get(channel="whatsapp").error_message == (
        "Graph API error 500: Server Error"
    )


def test_whatsapp_network_error_is_failed(order, whatsapp):  # noqa: F811
    whatsapp["state"]["error"] = urllib.error.URLError("timed out")
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="whatsapp")
    assert attempt.status == DeliveryAttempt.FAILED
    assert attempt.error_message == "WhatsApp request failed: timed out"


def test_whatsapp_without_template_is_skipped(order, whatsapp, settings):  # noqa: F811
    notification = _order_notification(order, "preparing")
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="whatsapp")
    assert attempt.status == DeliveryAttempt.SKIPPED
    assert "No WhatsApp template is enabled for this event" in attempt.error_message
    assert whatsapp["calls"] == []


def test_whatsapp_without_phone_is_skipped(order, whatsapp):  # noqa: F811
    order.customer_phone = ""
    order.save()
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="whatsapp")
    assert attempt.status == DeliveryAttempt.SKIPPED
    assert attempt.error_message == "No phone number."
    assert whatsapp["calls"] == []


def test_whatsapp_disabled_is_skipped(order, whatsapp, settings):  # noqa: F811
    configure_whatsapp(sending_enabled=False)
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="whatsapp")
    assert attempt.status == DeliveryAttempt.SKIPPED
    assert attempt.error_message == "whatsapp provider is not configured."
    assert whatsapp["calls"] == []


def test_whatsapp_provider_misconfiguration_is_skipped(whatsapp, settings):
    message = render("order_created", {})
    configure_whatsapp(access_token="")
    assert whatsapp_channel.send(message, "919876543210").error == (
        "WhatsApp phone number ID or access token is not set."
    )
    configure_whatsapp(provider="other_bsp")
    assert "Unknown WhatsApp provider" in whatsapp_channel.send(message, "919876543210").error
    configure_whatsapp(provider="meta_cloud")
    disabled = render("payment_verified", {})
    assert "No WhatsApp template" in whatsapp_channel.send(disabled, "919876543210").error
    assert whatsapp_channel.send(message, "").status == DeliveryAttempt.SKIPPED
    assert whatsapp["calls"] == []


def test_staff_whatsapp_numbers(db, whatsapp, settings):
    configure_whatsapp(staff_alert_numbers=["+91 90000 11111", "not-a-number"])
    payload = {"order_number": "LZ-9", "customer_name": "Meera", "grand_total": "850"}
    emit_staff_event("staff_payment_submitted", payload, "submission:s:staff")
    broadcast = Notification.objects.get(user__isnull=True)
    dispatch_notification(broadcast.pk)
    sent = broadcast.attempts.get(channel="whatsapp", status=DeliveryAttempt.SENT)
    assert sent.recipient == "919000011111"
    invalid = broadcast.attempts.get(channel="whatsapp", status=DeliveryAttempt.SKIPPED)
    assert invalid.error_message == "'not-a-number' is not a valid WhatsApp number."
    body = json.loads(whatsapp["calls"][0]["request"].data)
    assert body["template"]["name"] == "staff_payment_submitted"
    assert [p["text"] for p in body["template"]["components"][0]["parameters"]] == [
        "LZ-9",
        "Meera",
        "₹850",
    ]


def test_template_without_params_has_no_components(whatsapp):
    provider = whatsapp_channel.MetaCloudProvider(TOKEN, "1", "v26.0")
    result = provider.send_template("919876543210", "hello_world", "en_US", [])
    assert result.status == "sent"
    body = json.loads(whatsapp["calls"][0]["request"].data)
    assert body["template"] == {"name": "hello_world", "language": {"code": "en_US"}}


# Email --------------------------------------------------------------------------------------


def test_customer_email_sent_with_link(order, settings, mailoutbox):  # noqa: F811
    settings.EMAIL_PROVIDER_ENABLED = True
    order.customer_email = "buyer@example.com"
    order.save()
    notification = _order_notification(order, "ready")
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="email")
    assert attempt.status == DeliveryAttempt.SENT
    assert attempt.recipient == "buyer@example.com"
    (mail,) = mailoutbox
    assert mail.to == ["buyer@example.com"]
    assert mail.subject == "Order LZ-TEST-1 is ready for pickup"
    assert f"http://frontend.test/orders/{order.id}" in mail.body
    assert mail.from_email == settings.DEFAULT_FROM_EMAIL


def test_customer_email_falls_back_to_account_email(order, settings, mailoutbox):  # noqa: F811
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    assert mailoutbox[0].to == ["payment@example.com"]


def test_email_disabled_is_skipped(order, settings, mailoutbox):  # noqa: F811
    settings.EMAIL_PROVIDER_ENABLED = False
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="email")
    assert attempt.status == DeliveryAttempt.SKIPPED
    assert attempt.error_message == "email provider is not configured."
    assert mailoutbox == []


def test_email_backend_error_is_failed(order, settings, monkeypatch):  # noqa: F811
    def broken(*args, **kwargs):
        raise smtplib.SMTPException("relay refused")

    monkeypatch.setattr(email_channel, "send_mail", broken)
    notification = _order_notification(order)
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="email")
    assert attempt.status == DeliveryAttempt.FAILED
    assert attempt.error_message == "SMTPException: relay refused"


def test_email_not_accepted_is_failed(monkeypatch):
    monkeypatch.setattr(email_channel, "send_mail", lambda *a, **k: 0)
    result = email_channel.send(render("order_created", {}), "x@example.com")
    assert result.status == DeliveryAttempt.FAILED


def test_event_without_email_copy_is_skipped(order, settings, mailoutbox):  # noqa: F811
    notification = _order_notification(order, "payment_verified")
    dispatch_notification(notification.pk)
    attempt = notification.attempts.get(channel="email")
    assert attempt.status == DeliveryAttempt.SKIPPED
    assert attempt.error_message == "This event is not sent by email."
    assert mailoutbox == []
    assert email_channel.send(render("order_created", {}), "").status == "skipped"


def test_staff_email_goes_to_staff_notify_emails(db, settings, mailoutbox):
    configure_whatsapp(staff_alert_emails=["owner@leezacakes.test", "kitchen@leezacakes.test"])
    payload = {
        "order_id": "8a1c2b9e-0000-4000-8000-000000000001",
        "order_number": "LZ-7",
        "customer_name": "Aarav Mehta",
        "grand_total": "2340.00",
    }
    emit_staff_event("staff_order_created", payload, "order:7:staff")
    dispatch_notification(Notification.objects.get(user__isnull=True).pk)
    assert sorted(m.to[0] for m in mailoutbox) == [
        "kitchen@leezacakes.test",
        "owner@leezacakes.test",
    ]
    mail = mailoutbox[0]
    assert mail.subject == "New order LZ-7 · ₹2,340"
    assert (
        "http://backend.test/admin/orders/order/8a1c2b9e-0000-4000-8000-000000000001/change/"
        in mail.body
    )
