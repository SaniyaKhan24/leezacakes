import pytest
from django.test import Client

from apps.accounts.models import User
from apps.notifications.models import DeliveryAttempt, Notification
from apps.notifications.services import dispatch_notification, emit_staff_event
from apps.notifications.tests.helpers import configure_whatsapp


@pytest.fixture
def studio(db):
    user = User.objects.create_superuser(email="studio@example.com", password="Studio-pass-123!")
    client = Client()
    client.force_login(user)
    return user, client


def test_admin_pages_include_live_alerts_for_staff(studio):
    _, client = studio
    response = client.get("/admin/")
    assert response.status_code == 200
    html = response.content.decode()
    assert "Leeza Cakes Studio" in html
    assert 'id="lz-alerts-config"' in html
    assert 'data-count-url="/api/v1/notifications/inbox/unread-count/"' in html
    assert 'data-list-url="/api/v1/notifications/inbox/"' in html
    assert 'data-read-url="/api/v1/notifications/inbox/read/"' in html
    assert 'id="lz-alerts-badge"' in html
    assert "Enable desktop alerts" in html
    assert "AudioContext" in html
    assert "new Notification(" in html
    assert "Log out" in html  # the default user links are kept
    # Other admin pages extend the same base.
    assert 'id="lz-alerts-config"' in client.get("/admin/orders/order/").content.decode()


def test_login_page_has_no_alert_script(db):
    response = Client().get("/admin/login/")
    assert response.status_code == 200
    html = response.content.decode()
    assert "Leeza Cakes Studio" in html
    assert "lz-alerts-config" not in html


def test_no_content_security_policy_blocks_the_inline_script(studio):
    _, client = studio
    response = client.get("/admin/")
    assert "Content-Security-Policy" not in response.headers


def test_notification_and_delivery_admin_pages(studio, settings):
    user, client = studio
    configure_whatsapp(staff_alert_emails=["owner@leezacakes.test"])
    payload = {"order_id": "8a1c2b9e-0000-4000-8000-000000000001", "order_number": "LZ-5"}
    emit_staff_event("staff_order_created", payload, "order:5:staff")
    broadcast = Notification.objects.get(user__isnull=True)
    dispatch_notification(broadcast.pk)
    assert broadcast.attempts.filter(status=DeliveryAttempt.SENT).exists()

    changelist = client.get("/admin/notifications/notification/")
    assert changelist.status_code == 200
    html = changelist.content.decode()
    assert "New order LZ-5" in html
    assert "1 sent" in html
    assert "In-app only" in html
    for query in ("?audience__exact=staff", "?read=unread", "?read=read", "?event_key=x"):
        assert client.get(f"/admin/notifications/notification/{query}").status_code == 200
    change = client.get(f"/admin/notifications/notification/{broadcast.pk}/change/")
    assert change.status_code == 200
    assert "owner@leezacakes.test" in change.content.decode()
    attempts = client.get("/admin/notifications/deliveryattempt/?status__exact=skipped")
    assert attempts.status_code == 200
    assert "whatsapp provider is not configured." in attempts.content.decode()
    attempt = broadcast.attempts.first()
    detail = client.get(f"/admin/notifications/deliveryattempt/{attempt.pk}/change/")
    assert detail.status_code == 200
    assert client.get("/admin/notifications/deliveryattempt/add/").status_code == 403
    assert client.get("/admin/notifications/notificationpreference/").status_code == 200
