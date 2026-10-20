import re

from django.core.exceptions import ValidationError

PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 .()\-]{6,30}$")


def validate_phone(value):
    if value and not PHONE_PATTERN.fullmatch(value.strip()):
        raise ValidationError("Enter a valid phone number.")


def normalize_phone(value):
    return " ".join(value.strip().split()) if value else ""
