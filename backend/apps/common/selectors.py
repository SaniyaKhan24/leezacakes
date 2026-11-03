from django.conf import settings


def site_config():
    """Public business details. Unset values stay None; nothing is invented."""
    return {
        "business_name": settings.SITE_BUSINESS_NAME,
        "contact_phone": settings.SITE_CONTACT_PHONE,
        "contact_email": settings.SITE_CONTACT_EMAIL,
        "whatsapp": settings.SITE_WHATSAPP,
        "instagram": settings.SITE_INSTAGRAM,
        "address": settings.SITE_ADDRESS,
        "pickup_hours_label": settings.SITE_PICKUP_HOURS_LABEL,
        "currency": "INR",
        "timezone": settings.TIME_ZONE,
        "is_sample": bool(settings.SITE_CONTENT_IS_SAMPLE),
    }
