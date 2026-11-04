import re

from django.core.exceptions import ValidationError

PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 .()\-]{6,30}$")


def validate_phone(value):
    if value and not PHONE_PATTERN.fullmatch(value.strip()):
        raise ValidationError("Enter a valid phone number.")


def normalize_phone(value):
    return " ".join(value.strip().split()) if value else ""


def to_e164_digits(value, default_country_code="91"):
    """Return an E.164 number as digits only (no "+"), or None when it is not usable.

    Local Indian numbers (10 digits, optionally with a leading 0) get the default
    country code; "+" and "00" prefixes are treated as international.
    """
    phone = normalize_phone(value)
    if not phone:
        return None
    international = phone.startswith("+") or phone.startswith("00")
    digits = re.sub(r"\D", "", phone)
    if phone.startswith("00"):
        digits = digits[2:]
    elif not international:
        if len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        if len(digits) == 10:
            digits = f"{default_country_code}{digits}"
    if not 8 <= len(digits) <= 15 or digits.startswith("0"):
        return None
    return digits


def format_e164(digits):
    """Readable international form of E.164 digits: +91 90000 00000 for Indian mobiles."""
    if not digits:
        return ""
    if digits.startswith("91") and len(digits) == 12:
        return f"+91 {digits[2:7]} {digits[7:]}"
    return f"+{digits}"
