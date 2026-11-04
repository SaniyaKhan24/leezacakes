from django.utils import timezone
from rest_framework import serializers

from apps.accounts.validators import normalize_phone, validate_phone

from .models import Enquiry


class EnquiryCreateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(
        required=False, allow_blank=True, max_length=32, validators=[validate_phone]
    )
    message = serializers.CharField(max_length=Enquiry.MESSAGE_MAX_LENGTH)
    servings = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=1000
    )

    class Meta:
        model = Enquiry
        fields = (
            "kind",
            "name",
            "email",
            "phone",
            "occasion",
            "event_date",
            "servings",
            "budget",
            "message",
        )
        extra_kwargs = {
            "kind": {"required": False},
            "occasion": {"required": False},
            "event_date": {"required": False},
            "budget": {"required": False},
        }

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Please tell us your name.")
        return value.strip()

    def validate_email(self, value):
        return value.strip().lower()

    def validate_phone(self, value):
        return normalize_phone(value)

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("Please include a message.")
        return value.strip()

    def validate_event_date(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError("The event date must be today or later.")
        return value


class EnquiryCreatedSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reference = serializers.CharField()


class EnquiryCreatedEnvelopeSerializer(serializers.Serializer):
    data = EnquiryCreatedSerializer()
