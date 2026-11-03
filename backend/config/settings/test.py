import tempfile
from decimal import Decimal

from .base import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

DEBUG = False
API_DOCS_ENABLED = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
FRONTEND_URL = "http://frontend.test"
# Tests never write into the repository; conftest.py also isolates each test.
PAYMENT_EVIDENCE_STORAGE_ROOT = tempfile.mkdtemp(prefix="leeza-test-evidence-")
MEDIA_ROOT = tempfile.mkdtemp(prefix="leeza-test-media-")
ORDER_TAX_POLICY_CONFIGURED = True
ORDER_TAX_RATE = Decimal("0")
ORDER_PRICES_INCLUDE_TAX = True
PAYMENT_UPI_ID = ""
PAYMENT_UPI_PAYEE_NAME = ""
PAYMENT_UPI_IS_SAMPLE = False
PICKUP_OPEN_HOUR = 10
PICKUP_CLOSE_HOUR = 20
PICKUP_SLOT_MINUTES = 60
PICKUP_DAYS_AHEAD = 14
PICKUP_MIN_LEAD_MINUTES = 240
