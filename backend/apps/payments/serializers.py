from decimal import Decimal
from urllib.parse import quote, urlencode

from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from PIL import Image
from rest_framework import serializers

from .models import Payment, PaymentSubmission


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSubmission
        fields = (
            "id",
            "status",
            "original_filename",
            "content_type",
            "file_size",
            "rejection_reason",
            "submitted_at",
            "reviewed_at",
        )
        read_only_fields = fields


class PaymentInstructionsSerializer(serializers.Serializer):
    upi_id = serializers.CharField()
    payee_name = serializers.CharField(allow_blank=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    upi_uri = serializers.CharField()
    note = serializers.CharField()
    is_sample = serializers.BooleanField()


def payment_instructions(payment):
    """UPI instructions for a payment, or None when no UPI ID is configured."""
    upi_id = getattr(settings, "PAYMENT_UPI_ID", "")
    if not upi_id:
        return None
    payee = getattr(settings, "PAYMENT_UPI_PAYEE_NAME", "")
    is_sample = bool(getattr(settings, "PAYMENT_UPI_IS_SAMPLE", False))
    order_number = payment.order.order_number
    amount = f"{payment.amount_due:.2f}"
    params = {"pa": upi_id}
    if payee:
        params["pn"] = payee
    params.update({"am": amount, "cu": payment.currency, "tn": order_number})
    note = (
        f"Pay exactly ₹{amount} by UPI and write {order_number} in the payment note. "
        "Then upload a screenshot of the successful payment so we can verify it."
    )
    if is_sample:
        note = "These are sample payment details for local development. Do not send money. " + note
    return {
        "upi_id": upi_id,
        "payee_name": payee,
        "amount": amount,
        "currency": payment.currency,
        "upi_uri": "upi://pay?" + urlencode(params, quote_via=quote, safe="@"),
        "note": note,
        "is_sample": is_sample,
    }


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    latest_submission = serializers.SerializerMethodField()
    can_submit_evidence = serializers.SerializerMethodField()
    instructions = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "order_number",
            "method",
            "status",
            "amount_due",
            "currency",
            "verified_amount",
            "verified_at",
            "latest_submission",
            "can_submit_evidence",
            "instructions",
        )
        read_only_fields = fields

    @extend_schema_field(SubmissionSerializer(allow_null=True))
    def get_latest_submission(self, obj):
        item = obj.submissions.first()
        return SubmissionSerializer(item).data if item else None

    @extend_schema_field(serializers.BooleanField())
    def get_can_submit_evidence(self, obj):
        return obj.status in {Payment.AWAITING, Payment.REJECTED}

    @extend_schema_field(PaymentInstructionsSerializer(allow_null=True))
    def get_instructions(self, obj):
        return payment_instructions(obj)


class EvidenceUploadSerializer(serializers.Serializer):
    evidence = serializers.FileField()

    def validate_evidence(self, value):
        max_size = getattr(settings, "PAYMENT_EVIDENCE_MAX_SIZE", 5 * 1024 * 1024)
        if value.size <= 0 or value.size > max_size:
            raise serializers.ValidationError(
                "Evidence file is empty or exceeds the configured size limit."
            )
        value.seek(0)
        try:
            image = Image.open(value)
            image.verify()
            image_format = image.format
        except Exception as exc:
            raise serializers.ValidationError("Evidence must be a valid image.") from exc
        if image_format not in {"PNG", "JPEG", "WEBP"}:
            raise serializers.ValidationError("Only PNG, JPEG and WEBP evidence is supported.")
        value.seek(0)
        return value


class ReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("accept", "reject"))
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        if attrs["decision"] == "reject" and not attrs.get("reason", "").strip():
            raise serializers.ValidationError({"reason": "A rejection reason is required."})
        return attrs


class VerifySerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    verified_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.00")
    )
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
