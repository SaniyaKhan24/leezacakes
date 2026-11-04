"""Production refuses to start without a usable FIELD_ENCRYPTION_KEY."""

import os
import secrets
import subprocess  # nosec B404 - fixed interpreter command, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALID_KEY = "Zm9vYmFyYmF6cXV4cXV1eGNvcmdlZ3JhdWx0Z2FycGw="


def load_production(**overrides):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("DJANGO_", "DB_", "FIELD_", "CORS_", "CSRF_", "FRONTEND_"))
    }
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.production",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
            "DJANGO_ALLOWED_HOSTS": "api.example.invalid",
            "CORS_ALLOWED_ORIGINS": "https://shop.example.invalid",
            "CSRF_TRUSTED_ORIGINS": "https://shop.example.invalid",
            "FRONTEND_URL": "https://shop.example.invalid",
            "DB_NAME": "x",
            "DB_USER": "x",
            "DB_PASSWORD": "x",
            "DB_HOST": "localhost",
            **overrides,
        }
    )
    code = "import django; django.setup(); print('loaded')"
    return subprocess.run(  # nosec B603 - fixed interpreter command
        [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True
    )


@pytest.mark.parametrize(
    ("key", "message"),
    [("", "FIELD_ENCRYPTION_KEY must be configured"), ("short", "Fernet keys")],
)
def test_production_requires_an_encryption_key(key, message):
    result = load_production(FIELD_ENCRYPTION_KEY=key)
    assert result.returncode != 0
    assert message in result.stderr


def test_production_starts_with_a_valid_key():
    result = load_production(FIELD_ENCRYPTION_KEY=VALID_KEY)
    assert result.returncode == 0, result.stderr
    assert "loaded" in result.stdout
