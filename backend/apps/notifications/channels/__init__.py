"""Delivery channels. Each module exposes ``name``, ``is_enabled()`` and
``send(message, recipient) -> DeliveryResult``."""

from . import email, whatsapp
from .base import DeliveryResult

CHANNELS = {email.name: email, whatsapp.name: whatsapp}

__all__ = ["CHANNELS", "DeliveryResult", "email", "whatsapp"]
