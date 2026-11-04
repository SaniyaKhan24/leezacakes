"""Plain-text email through Django's configured EMAIL_BACKEND."""

from django.conf import settings
from django.core.mail import send_mail

from ..messages import email_text
from .base import DeliveryResult

name = "email"


def is_enabled():
    return bool(settings.EMAIL_PROVIDER_ENABLED)


def send(message, recipient):
    if not recipient:
        return DeliveryResult.skipped("No email address for this recipient.")
    if not message.get("email_subject") or not message.get("email_body"):
        return DeliveryResult.skipped("This event is not sent by email.")
    try:
        sent = send_mail(
            message["email_subject"],
            email_text(message),
            None,
            [recipient],
            fail_silently=False,
        )
    except Exception as exc:  # any backend error is recorded on the attempt, not raised
        return DeliveryResult.failed(f"{type(exc).__name__}: {exc}")
    if not sent:
        return DeliveryResult.failed("The email backend did not accept the message.")
    return DeliveryResult.sent()
