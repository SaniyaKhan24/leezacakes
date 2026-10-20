import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


def private_evidence_path(instance, filename):
    return f"payment-evidence/{instance.payment_id}/{uuid.uuid4().hex}.bin"


def private_evidence_storage():
    from django.core.files.storage import FileSystemStorage

    root = getattr(settings, "PAYMENT_EVIDENCE_STORAGE_ROOT", "")
    if not root:
        root = str(settings.BASE_DIR / "private_payment_evidence")
    return FileSystemStorage(location=root, base_url="")


class Payment(models.Model):
    UPI_QR = "upi_qr"
    AWAITING = "awaiting_payment"
    PENDING = "pending_verification"
    VERIFIED = "verified"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (AWAITING, "Awaiting payment"),
        (PENDING, "Pending verification"),
        (VERIFIED, "Verified"),
        (REJECTED, "Rejected"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="payment")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments"
    )
    method = models.CharField(max_length=20, default=UPI_QR)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=AWAITING)
    amount_due = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    currency = models.CharField(max_length=3, default="INR")
    verified_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_payments",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = (("verify_payment", "Can verify payments"),)
        indexes = [models.Index(fields=("status", "created_at"))]

    def __str__(self):
        return f"{self.order.order_number}: {self.status}"


class PaymentSubmission(models.Model):
    PENDING_REVIEW = "pending_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (PENDING_REVIEW, "Pending review"),
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="submissions")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_submissions"
    )
    evidence_file = models.FileField(
        upload_to=private_evidence_path, storage=private_evidence_storage
    )
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=80)
    file_size = models.PositiveBigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING_REVIEW)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_payment_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-submitted_at", "id")
        indexes = [models.Index(fields=("payment", "status", "submitted_at"))]

    def __str__(self):
        return f"{self.payment_id}:{self.status}"


class PaymentStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="status_history")
    from_status = models.CharField(max_length=32, blank=True, default="")
    to_status = models.CharField(max_length=32)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    related_submission = models.ForeignKey(
        PaymentSubmission, null=True, blank=True, on_delete=models.SET_NULL
    )
    reason = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")

    def __str__(self):
        return f"{self.payment_id}: {self.to_status}"
