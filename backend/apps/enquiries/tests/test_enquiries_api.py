from datetime import timedelta

import pytest
from django.contrib.messages import get_messages
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.enquiries.models import Enquiry, reference_for

URL = "/api/v1/enquiries/"


@pytest.fixture
def client_api():
    return APIClient()


def custom_cake(**overrides):
    payload = {
        "kind": "custom_cake",
        "name": "  Kabir Shah ",
        "email": "Kabir@Example.com",
        "phone": " +91  90000 00002 ",
        "occasion": "30th birthday",
        "event_date": (timezone.localdate() + timedelta(days=10)).isoformat(),
        "servings": 25,
        "budget": "₹4,000–5,000",
        "message": "A two-tier pistachio rose cake with fresh flowers, please.",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_custom_cake_enquiry_is_created_with_reference(client_api):
    response = client_api.post(URL, custom_cake(), format="json")
    assert response.status_code == 201
    data = response.data["data"]
    enquiry = Enquiry.objects.get(pk=data["id"])
    assert data["reference"] == enquiry.reference == reference_for(enquiry.id)
    assert data["reference"].startswith("ENQ-") and len(data["reference"]) == 10
    assert enquiry.kind == Enquiry.CUSTOM_CAKE
    assert enquiry.status == Enquiry.NEW
    assert enquiry.name == "Kabir Shah"
    assert enquiry.email == "kabir@example.com"
    assert enquiry.phone == "+91 90000 00002"
    assert enquiry.servings == 25


@pytest.mark.django_db
def test_minimal_general_enquiry(client_api):
    response = client_api.post(
        URL,
        {"name": "Asha", "email": "asha@example.com", "message": "Do you do eggless?"},
        format="json",
    )
    assert response.status_code == 201
    enquiry = Enquiry.objects.get()
    assert enquiry.kind == Enquiry.GENERAL
    assert enquiry.phone == "" and enquiry.event_date is None and enquiry.servings is None
    assert str(enquiry).startswith(enquiry.reference)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"message": ""}, "message"),
        ({"message": "   "}, "message"),
        ({"message": "x" * 2001}, "message"),
        ({"name": "  "}, "name"),
        ({"email": "not-an-email"}, "email"),
        ({"phone": "call me"}, "phone"),
        ({"event_date": (timezone.localdate() - timedelta(days=1)).isoformat()}, "event_date"),
        ({"servings": 0}, "servings"),
        ({"servings": -3}, "servings"),
        ({"kind": "wedding"}, "kind"),
    ],
)
def test_enquiry_validation(client_api, overrides, field):
    response = client_api.post(URL, custom_cake(**overrides), format="json")
    assert response.status_code == 400
    assert field in str(response.data)
    assert Enquiry.objects.count() == 0


@pytest.mark.django_db
def test_event_date_today_is_allowed(client_api):
    payload = custom_cake(event_date=timezone.localdate().isoformat())
    assert client_api.post(URL, payload, format="json").status_code == 201


@pytest.mark.django_db
def test_enquiries_are_throttled(client_api):
    statuses = [client_api.post(URL, custom_cake(), format="json").status_code for _ in range(11)]
    assert statuses[:10] == [201] * 10
    assert statuses[10] == 429


@pytest.mark.django_db
def test_enquiry_admin_actions(client):
    admin_user = User.objects.create_superuser(email="studio@example.com", password="x-Pass-123!")
    enquiry = Enquiry.objects.create(name="A", email="a@example.com", message="Hello")
    client.force_login(admin_user)
    listing = client.get("/admin/enquiries/enquiry/")
    assert listing.status_code == 200 and enquiry.reference in listing.content.decode()
    assert client.get(f"/admin/enquiries/enquiry/{enquiry.id}/change/").status_code == 200
    for action, status in (("mark_contacted", "contacted"), ("mark_closed", "closed")):
        response = client.post(
            "/admin/enquiries/enquiry/",
            {"action": action, "_selected_action": [str(enquiry.id)]},
            follow=True,
        )
        assert any("1 enquiry" in str(m) for m in get_messages(response.wsgi_request))
        enquiry.refresh_from_db()
        assert enquiry.status == status
