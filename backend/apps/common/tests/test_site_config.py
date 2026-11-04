from django.test import override_settings
from rest_framework.test import APIClient

from apps.notifications.tests.helpers import configure_whatsapp

SAMPLE = {
    "SITE_BUSINESS_NAME": "Leeza Cakes",
    "SITE_CONTACT_PHONE": "+91 90000 00000",
    "SITE_CONTACT_EMAIL": "hello@leezacakes.example",
    "SITE_INSTAGRAM": None,
    "SITE_ADDRESS": "Sample Studio Address, Bengaluru",
    "SITE_PICKUP_HOURS_LABEL": "Pickup daily, 10 am to 8 pm",
    "SITE_CONTENT_IS_SAMPLE": True,
}


def test_site_config_returns_configured_values(db):
    configure_whatsapp(business_number="+91 90000 00000")
    with override_settings(**SAMPLE):
        response = APIClient().get("/api/v1/site/")
    assert response.status_code == 200
    assert response.data == {
        "data": {
            "business_name": "Leeza Cakes",
            "contact_phone": "+91 90000 00000",
            "contact_email": "hello@leezacakes.example",
            "whatsapp": "+91 90000 00000",
            "whatsapp_link_number": "919000000000",
            "instagram": None,
            "address": "Sample Studio Address, Bengaluru",
            "pickup_hours_label": "Pickup daily, 10 am to 8 pm",
            "currency": "INR",
            "timezone": "Asia/Kolkata",
            "is_sample": True,
        }
    }


def test_site_config_leaves_unset_values_null(db):
    response = APIClient().get("/api/v1/site/")
    data = response.data["data"]
    assert data["business_name"] == "Leeza Cakes"
    for key in (
        "contact_phone",
        "contact_email",
        "whatsapp",
        "whatsapp_link_number",
        "instagram",
        "address",
    ):
        assert data[key] is None
    assert data["is_sample"] is False
