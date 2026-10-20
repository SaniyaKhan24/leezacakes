from decimal import Decimal

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


class PaymentSerializer(serializers.ModelSerializer):
    latest_submission = serializers.SerializerMethodField()
    can_submit_evidence = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "method",
            "status",
            "amount_due",
            "currency",
            "verified_amount",
            "verified_at",
            "latest_submission",
            "can_submit_evidence",
        )
        read_only_fields = fields

    @extend_schema_field(SubmissionSerializer(allow_null=True))
    def get_latest_submission(self, obj):
        item = obj.submissions.first()
        return SubmissionSerializer(item).data if item else None

    @extend_schema_field(serializers.BooleanField())
    def get_can_submit_evidence(self, obj):
        return obj.status in {Payment.AWAITING, Payment.REJECTED}


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
