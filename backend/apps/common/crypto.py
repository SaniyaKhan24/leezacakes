"""Fernet encryption for secrets stored in the database (e.g. provider API tokens).

FIELD_ENCRYPTION_KEY holds one or more comma-separated urlsafe-base64 32-byte keys.
The first key encrypts; every key can decrypt, so keys can be rotated by putting the
new key first and re-saving the secrets. Generate a key with:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import logging

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def _fernet():
    keys = [key.strip() for key in (settings.FIELD_ENCRYPTION_KEY or "").split(",") if key.strip()]
    if not keys:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must be configured to store secrets.")
    try:
        return MultiFernet([Fernet(key.encode()) for key in keys])
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY must be urlsafe base64-encoded 32-byte Fernet keys."
        ) from exc


def validate_key(value):
    """Raise ImproperlyConfigured unless `value` is a usable key list."""
    keys = [key.strip() for key in (value or "").split(",") if key.strip()]
    if not keys:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must be configured.")
    try:
        for key in keys:
            Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY must be urlsafe base64-encoded 32-byte Fernet keys."
        ) from exc


def encrypt(plaintext):
    """Encrypt a string; empty values are stored as ''."""
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token):
    """Decrypt a stored value. Returns None when it cannot be decrypted (wrong key)."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        logger.warning("A stored secret could not be decrypted with FIELD_ENCRYPTION_KEY.")
        return None
