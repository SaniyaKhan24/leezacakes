"""The WhatsApp & alert settings page: secrets, validation and the Meta operations."""

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from django.test import Client
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common import crypto
from apps.notifications.messages import WHATSAPP_TEMPLATE_DEFS
from apps.notifications.models import WhatsAppMessage, WhatsAppSettings, WhatsAppTemplate
from apps.notifications.tests.helpers import configure_whatsapp

TOKEN = "EAAG-very-secret-token-987"
APP_SECRET = "app-secret-123456"
CHANGE = "/admin/notifications/whatsappsettings/1/change/"
OPS = "/admin/notifications/whatsappsettings/operations/"


@pytest.fixture
def studio(db):
    user = User.objects.create_superuser(email="owner@example.com", password="Owner-pass-123!")
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def connected(db):
    return configure_whatsapp(
        access_token=TOKEN,
        phone_number_id="1098765432",
        business_account_id="2233445566",
        api_version="v26.0",
    )


def form_data(**overrides):
    config = WhatsAppSettings.load()
    templates = list(WhatsAppTemplate.objects.order_by("id"))
    data = {
        "business_number": config.business_number,
        "provider": config.provider,
        "phone_number_id": config.phone_number_id,
        "business_account_id": config.business_account_id,
        "api_version": config.api_version,
        "template_language": config.template_language,
        "staff_alert_numbers": config.staff_alert_numbers,
        "staff_alert_emails": config.staff_alert_emails,
        "access_token": "",
        "app_secret": "",
        "templates-TOTAL_FORMS": len(templates),
        "templates-INITIAL_FORMS": len(templates),
        "templates-MIN_NUM_FORMS": 0,
        "templates-MAX_NUM_FORMS": 1000,
    }
    if config.sending_enabled:
        data["sending_enabled"] = "on"
    for index, template in enumerate(templates):
        data[f"templates-{index}-id"] = template.pk
        data[f"templates-{index}-settings"] = 1
        data[f"templates-{index}-template_name"] = template.template_name
        if template.enabled:
            data[f"templates-{index}-enabled"] = "on"
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


# Encryption ---------------------------------------------------------------------------------


def test_secrets_are_encrypted_at_rest(db):
    config = configure_whatsapp(access_token=TOKEN, app_secret=APP_SECRET)
    raw = WhatsAppSettings.objects.values("access_token_encrypted", "app_secret_encrypted").get()
    assert TOKEN not in raw["access_token_encrypted"]
    assert APP_SECRET not in raw["app_secret_encrypted"]
    assert config.access_token == TOKEN
    assert config.app_secret == APP_SECRET


def test_crypto_round_trip_rotation_and_wrong_key(settings):
    old_key = settings.FIELD_ENCRYPTION_KEY
    token = crypto.encrypt("hello")
    assert token != "hello" and crypto.decrypt(token) == "hello"
    assert crypto.encrypt("") == "" and crypto.decrypt("") == ""
    new_key = "Zm9vYmFyYmF6cXV4cXV1eGNvcmdlZ3JhdWx0Z2FycGw="
    settings.FIELD_ENCRYPTION_KEY = f"{new_key},{old_key}"
    assert crypto.decrypt(token) == "hello"  # old key still decrypts after rotation
    settings.FIELD_ENCRYPTION_KEY = new_key
    assert crypto.decrypt(token) is None  # wrong key: treated as not set
    settings.FIELD_ENCRYPTION_KEY = ""
    with pytest.raises(ImproperlyConfigured):
        crypto.encrypt("x")
    settings.FIELD_ENCRYPTION_KEY = "not-a-key"
    with pytest.raises(ImproperlyConfigured):
        crypto.encrypt("x")
    with pytest.raises(ImproperlyConfigured):
        crypto.validate_key("not-a-key")
    with pytest.raises(ImproperlyConfigured):
        crypto.validate_key("")
    crypto.validate_key(old_key)


# The settings page --------------------------------------------------------------------------


def test_changelist_redirects_to_the_singleton(studio):
    response = studio.get("/admin/notifications/whatsappsettings/")
    assert response.status_code == 302
    assert response["Location"] == CHANGE
    assert WhatsAppTemplate.objects.count() == len(WHATSAPP_TEMPLATE_DEFS)
    assert not WhatsAppTemplate.objects.get(event_key="preparing").enabled
    assert studio.get("/admin/notifications/whatsappsettings/add/").status_code == 403


def test_change_page_renders_sections_tools_and_webhook(studio, connected):
    html = studio.get(CHANGE).content.decode()
    for text in (
        "Chat button",
        "Sending (Cloud API)",
        "Staff alerts",
        "Webhook",
        "Check connection",
        "Sync template status",
        "Submit missing templates",
        "Send test",
        "http://backend.test/api/v1/notifications/whatsapp/webhook/",
        connected.webhook_verify_token,
        "order_received",
        "Leeza Cakes Studio",
        "•••• saved. Leave blank to keep it.",
    ):
        assert text in html, text
    assert TOKEN not in html


def test_saving_secrets_is_write_only(studio, db):
    response = studio.post(
        CHANGE, form_data(access_token=TOKEN, app_secret=APP_SECRET, phone_number_id="1")
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    config = WhatsAppSettings.load()
    assert config.access_token == TOKEN and config.app_secret == APP_SECRET
    html = studio.get(CHANGE).content.decode()
    assert TOKEN not in html and APP_SECRET not in html
    assert html.count("•••• saved") == 2
    # A blank input keeps the saved secret.
    studio.post(CHANGE, form_data(business_account_id="99"))
    WhatsAppSettings.invalidate()
    assert WhatsAppSettings.load().access_token == TOKEN
    # "Remove" clears it.
    studio.post(CHANGE, form_data(clear_access_token="on"))
    WhatsAppSettings.invalidate()
    config = WhatsAppSettings.load()
    assert config.access_token == "" and config.app_secret == APP_SECRET
    assert "Not set." in studio.get(CHANGE).content.decode()


def test_undecryptable_secret_is_reported(studio, db, settings):
    configure_whatsapp(access_token=TOKEN)
    settings.FIELD_ENCRYPTION_KEY = "Zm9vYmFyYmF6cXV4cXV1eGNvcmdlZ3JhdWx0Z2FycGw="
    WhatsAppSettings.invalidate()
    assert "cannot be decrypted" in studio.get(CHANGE).content.decode()


def test_validation_and_normalisation(studio, db):
    response = studio.post(
        CHANGE,
        form_data(
            business_number="09000000000",
            staff_alert_numbers="+91 98765 43210, 9876543210\n+1 415 555 0100",
            staff_alert_emails="Owner@Example.com\nkitchen@example.com",
        ),
    )
    assert response.status_code == 302
    config = WhatsAppSettings.load()
    assert config.business_number == "+91 90000 00000"
    assert config.staff_numbers == ["+91 98765 43210", "+14155550100"]
    assert config.staff_emails == ["owner@example.com", "kitchen@example.com"]

    response = studio.post(
        CHANGE,
        form_data(
            business_number="12",
            staff_alert_numbers="bogus",
            staff_alert_emails="not-an-email",
            api_version="26",
            sending_enabled="on",
            phone_number_id="",
            **{"templates-0-template_name": "Bad Name"},
        ),
    )
    assert response.status_code == 200
    html = response.content.decode()
    assert "Enter a valid number with country code" in html
    assert "Not valid WhatsApp numbers: bogus." in html
    assert "Not valid email addresses: not-an-email." in html
    assert "Use the Graph API version format" in html
    assert "Sending needs the phone number ID and access token." in html
    assert "Lowercase letters, digits and underscores only." in html


def test_enabling_sending_with_credentials(studio, db):
    response = studio.post(
        CHANGE, form_data(sending_enabled="on", phone_number_id="123", access_token=TOKEN)
    )
    assert response.status_code == 302
    assert WhatsAppSettings.load().can_send()


def test_site_config_reads_the_saved_number(studio, db):
    assert APIClient().get("/api/v1/site/").data["data"]["whatsapp_link_number"] is None
    studio.post(CHANGE, form_data(business_number="+91 98765 43210"))
    data = APIClient().get("/api/v1/site/").data["data"]
    assert data["whatsapp"] == "+91 98765 43210"
    assert data["whatsapp_link_number"] == "919876543210"


def test_the_singleton_cannot_be_deleted(db):
    config = WhatsAppSettings.load()
    assert config.delete() == (0, {})
    assert WhatsAppSettings.objects.filter(pk=1).exists()
    assert str(config) == "WhatsApp & alert settings"
    assert str(config.templates.first()).startswith("order_created → ")


# Operations ---------------------------------------------------------------------------------


def messages_of(response):
    return [str(m) for m in response.context["messages"]] if response.context else []


def test_operations_require_post_and_permission(studio, db):
    assert studio.get(f"{OPS}check-connection/").status_code == 405
    staff = User.objects.create_user(email="helper@example.com", is_staff=True)
    staff.user_permissions.add(
        Permission.objects.get(
            codename="view_whatsappsettings", content_type__model="whatsappsettings"
        )
    )
    client = Client()
    client.force_login(staff)
    assert client.post(f"{OPS}check-connection/").status_code == 403
    assert "Sync template status" not in client.get(CHANGE).content.decode()


def test_operations_need_configuration(studio, db):
    response = studio.post(f"{OPS}check-connection/", follow=True)
    assert "Set the phone number ID and access token" in messages_of(response)[0]
    configure_whatsapp(access_token=TOKEN, phone_number_id="1")
    response = studio.post(f"{OPS}sync-templates/", follow=True)
    assert messages_of(response) == ["Set the WhatsApp Business Account ID first."]


def test_check_connection(studio, connected, graph):
    graph.respond(
        "GET",
        "/1098765432?fields=",
        {
            "display_phone_number": "+91 90000 00000",
            "verified_name": "Leeza Cakes",
            "quality_rating": "GREEN",
            "platform_type": "CLOUD_API",
            "code_verification_status": "VERIFIED",
            "throughput": {"level": "STANDARD"},
        },
    )
    response = studio.post(f"{OPS}check-connection/", follow=True)
    (text,) = messages_of(response)
    assert text.startswith("Connected: +91 90000 00000 · Leeza Cakes · quality GREEN")
    call = graph.calls[0]
    assert call["url"].startswith("https://graph.facebook.com/v26.0/1098765432?fields=")
    assert "display_phone_number" in call["url"] and TOKEN not in call["url"]
    assert call["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert call["timeout"] == 10
    assert "Connected" in WhatsAppSettings.load().last_check_result
    assert "Connected: +91 90000 00000" in studio.get(CHANGE).content.decode()


def test_check_connection_graph_error_is_redacted(studio, connected, graph):
    graph.respond(
        "GET",
        "/1098765432",
        {"error": {"message": f"Invalid OAuth access token {TOKEN}", "code": 190}},
        status=401,
    )
    response = studio.post(f"{OPS}check-connection/", follow=True)
    (text,) = messages_of(response)
    assert text.startswith("Graph API error 190: Invalid OAuth access token")
    assert TOKEN not in text and "[redacted]" in text


def test_sync_templates_follows_paging(studio, connected, graph):
    graph.respond(
        "GET",
        "/2233445566/message_templates?",
        {
            "data": [
                {"name": "order_received", "language": "en", "status": "APPROVED"},
                {"name": "order_ready", "language": "en_US", "status": "APPROVED"},
            ],
            "paging": {"next": "https://graph.facebook.com/v26.0/2233445566/page2"},
        },
    )
    graph.respond(
        "GET",
        "/page2",
        {
            "data": [
                {
                    "name": "payment_rejected",
                    "language": "en",
                    "status": "REJECTED",
                    "rejected_reason": "INVALID_FORMAT",
                },
                {
                    "name": "order_completed",
                    "language": "en",
                    "status": "PENDING",
                    "rejected_reason": "NONE",
                },
            ]
        },
    )
    response = studio.post(f"{OPS}sync-templates/", follow=True)
    assert "order_received: APPROVED" in messages_of(response)[0]
    statuses = dict(WhatsAppTemplate.objects.values_list("template_name", "meta_status"))
    assert statuses["order_received"] == "APPROVED"
    assert statuses["order_ready"] == "MISSING"  # only en_US exists
    assert statuses["payment_rejected"] == "REJECTED"
    assert statuses["order_completed"] == "PENDING"
    rejected = WhatsAppTemplate.objects.get(template_name="payment_rejected")
    assert rejected.meta_rejected_reason == "INVALID_FORMAT"
    assert WhatsAppTemplate.objects.get(template_name="order_completed").meta_rejected_reason == ""
    assert "fields=name%2Cstatus%2Clanguage%2Ccategory%2Crejected_reason" in graph.calls[0]["url"]
    assert "limit=200" in graph.calls[0]["url"]


def test_sync_templates_graph_error(studio, connected, graph):
    graph.respond("GET", "/message_templates", {"error": {"message": "No permission"}}, 403)
    response = studio.post(f"{OPS}sync-templates/", follow=True)
    assert messages_of(response) == ["Graph API error 403: No permission"]


def test_submit_missing_templates(studio, connected, graph):
    graph.respond(
        "GET",
        "/message_templates?",
        {"data": [{"name": "order_received", "language": "en", "status": "APPROVED"}]},
    )
    graph.respond("POST", "/message_templates", {"id": "1", "status": "PENDING"})
    WhatsAppTemplate.objects.filter(event_key="ready").update(enabled=False)
    response = studio.post(f"{OPS}submit-templates/", follow=True)
    texts = messages_of(response)
    posts = [call for call in graph.calls if call["method"] == "POST"]
    submitted = {call["body"]["name"] for call in posts}
    # Enabled and missing only: not order_received (exists), not ready / preparing (disabled).
    assert submitted == {
        "payment_received",
        "payment_rejected",
        "order_confirmed",
        "order_completed",
        "staff_new_order",
        "staff_payment_submitted",
    }
    body = next(call["body"] for call in posts if call["body"]["name"] == "staff_new_order")
    definition = WHATSAPP_TEMPLATE_DEFS["staff_order_created"]
    assert body == {
        "name": "staff_new_order",
        "language": "en",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": definition["body"],
                "example": {"body_text": [definition["samples"]]},
            }
        ],
    }
    assert posts[0]["url"] == "https://graph.facebook.com/v26.0/2233445566/message_templates"
    assert "staff_new_order: submitted (PENDING)" in texts
    assert WhatsAppTemplate.objects.get(template_name="staff_new_order").meta_status == "PENDING"


def test_submit_reports_per_template_errors_and_nothing_to_do(studio, connected, graph):
    graph.respond("GET", "/message_templates?", {"data": []})
    graph.respond(
        "POST", "/message_templates", {"error": {"message": "Name already used"}}, status=400
    )
    WhatsAppTemplate.objects.exclude(event_key="order_created").update(enabled=False)
    response = studio.post(f"{OPS}submit-templates/", follow=True)
    assert messages_of(response) == ["order_received: Graph API error 400: Name already used"]
    graph.respond(
        "GET",
        "/message_templates?",
        {"data": [{"name": "order_received", "language": "en", "status": "PENDING"}]},
    )
    response = studio.post(f"{OPS}submit-templates/", follow=True)
    assert "Nothing to submit" in messages_of(response)[0]


def test_send_test_message(studio, connected, graph):
    graph.respond("POST", "/1098765432/messages", {"messages": [{"id": "wamid.TEST"}]})
    response = studio.post(
        f"{OPS}send-test/",
        {"test_number": "98765 43210", "test_event": "ready"},
        follow=True,
    )
    assert messages_of(response) == [
        "Test message sent to +91 98765 43210 (message id wamid.TEST)."
    ]
    body = graph.calls[0]["body"]
    assert body["to"] == "919876543210"
    assert body["template"]["name"] == "order_ready"
    params = [p["text"] for p in body["template"]["components"][0]["parameters"]]
    assert params == WHATSAPP_TEMPLATE_DEFS["ready"]["samples"]
    stored = WhatsAppMessage.objects.get(wa_message_id="wamid.TEST")
    assert stored.direction == "outbound" and stored.status == "sent"
    assert "Thu 5 Nov, 12 pm" in stored.body


def test_send_test_message_errors(studio, connected, graph):
    graph.respond("POST", "/messages", {"error": {"message": "Recipient not in allowed list"}}, 400)
    response = studio.post(
        f"{OPS}send-test/", {"test_number": "+91 98765 43210", "test_event": "ready"}, follow=True
    )
    assert messages_of(response) == [
        "Test message failed: Graph API error 400: Recipient not in allowed list"
    ]
    response = studio.post(
        f"{OPS}send-test/", {"test_number": "12", "test_event": "ready"}, follow=True
    )
    assert messages_of(response) == ["Enter a valid WhatsApp number with country code."]
    response = studio.post(
        f"{OPS}send-test/", {"test_number": "9876543210", "test_event": "nope"}, follow=True
    )
    assert messages_of(response) == ["Choose an event that has a template name."]
