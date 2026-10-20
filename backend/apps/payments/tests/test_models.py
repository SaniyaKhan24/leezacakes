from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import FieldFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.serializers import EvidenceUploadSerializer, ReviewSerializer
from apps.payments.services import review_submission, submit_evidence, verify_payment


@pytest.fixture
def order(db):
    user = User.objects.create_user(email="payment@example.com")
    return Order.objects.create(
        order_number="LZ-TEST-1",
        user=user,
        customer_name="Buyer",
        customer_phone="+919876543210",
        pickup_slot_start=timezone.now(),
        pickup_slot_end=timezone.now(),
        subtotal=Decimal("100.00"),
        tax_total=Decimal("0.00"),
        grand_total=Decimal("100.00"),
        idempotency_key="payment-test",
        request_fingerprint="f",
    )


def test_payment_amount_is_authoritative_order_total(order):
    payment = Payment.objects.create(order=order, user=order.user, amount_due=order.grand_total)
    assert payment.amount_due == Decimal("100.00")
    assert payment.status == Payment.AWAITING


def image_upload():
    stream = BytesIO()
    Image.new("RGB", (20, 20), "white").save(stream, format="PNG")
    return SimpleUploadedFile("receipt.png", stream.getvalue(), content_type="image/png")


@override_settings(PAYMENT_EVIDENCE_STORAGE_ROOT="C:/tmp/leeza-payment-tests")
def test_rejection_resubmission_and_verification(order):
    payment = Payment.objects.create(order=order, user=order.user, amount_due=order.grand_total)
    first = submit_evidence(payment, order.user, image_upload())
    reviewer = User.objects.create_user(email="reviewer@example.com")
    review_submission(payment, first, reviewer, "reject", "Unreadable")
    assert payment.__class__.objects.get(pk=payment.pk).status == Payment.REJECTED
    second = submit_evidence(payment, order.user, image_upload())
    review_submission(payment, second, reviewer, "accept")
    verified = verify_payment(payment, second, reviewer, Decimal("100.00"))
    assert verified.status == Payment.VERIFIED
    assert Order.objects.get(pk=order.pk).status == Order.CONFIRMED


def test_storage_failure_returns_validation_error_without_payment_mutation(order, monkeypatch):
    payment = Payment.objects.create(order=order, user=order.user, amount_due=order.grand_total)

    def fail_save(*args, **kwargs):
        raise OSError("storage unavailable")

    monkeypatch.setattr(FieldFile, "save", fail_save)
    with pytest.raises(ValidationError):
        submit_evidence(payment, order.user, image_upload())
    payment.refresh_from_db()
    assert payment.status == Payment.AWAITING


def test_evidence_serializer_rejects_non_image_upload():
    upload = SimpleUploadedFile("receipt.txt", b"not an image", content_type="text/plain")
    serializer = EvidenceUploadSerializer(data={"evidence": upload})
    assert not serializer.is_valid()
    assert "evidence" in serializer.errors


def test_evidence_and_review_serializers_reject_unsafe_inputs(settings):
    settings.PAYMENT_EVIDENCE_MAX_SIZE = 4
    oversized = SimpleUploadedFile("receipt.png", b"12345", content_type="image/png")
    evidence = EvidenceUploadSerializer(data={"evidence": oversized})
    assert not evidence.is_valid()

    gif_stream = BytesIO()
    Image.new("RGB", (2, 2), "white").save(gif_stream, format="GIF")
    gif = SimpleUploadedFile("receipt.gif", gif_stream.getvalue(), content_type="image/gif")
    evidence = EvidenceUploadSerializer(data={"evidence": gif})
    assert not evidence.is_valid()

    review = ReviewSerializer(data={"decision": "reject"})
    assert not review.is_valid()
