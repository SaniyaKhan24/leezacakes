import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _isolated_file_storage(settings, tmp_path):
    """Keep payment evidence and media uploads out of the repository."""
    settings.PAYMENT_EVIDENCE_STORAGE_ROOT = str(tmp_path / "private_payment_evidence")
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture(autouse=True)
def _reset_throttles():
    cache.clear()
    yield
    cache.clear()
