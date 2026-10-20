from rest_framework import serializers

from .models import NotificationPreference


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            "marketing_whatsapp_enabled",
            "marketing_sms_enabled",
            "marketing_email_enabled",
            "marketing_consent_recorded_at",
            "marketing_consent_source",
            "updated_at",
        )
        read_only_fields = ("marketing_consent_recorded_at", "updated_at")
