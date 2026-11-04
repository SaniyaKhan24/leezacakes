from rest_framework import serializers

from .models import Notification, NotificationPreference


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


class InboxNotificationSerializer(serializers.ModelSerializer):
    audience = serializers.ChoiceField(choices=Notification.AUDIENCE_CHOICES, read_only=True)
    title = serializers.CharField(source="rendered.title", read_only=True)
    body = serializers.CharField(source="rendered.body", read_only=True)
    link = serializers.CharField(source="rendered.link", read_only=True)

    class Meta:
        model = Notification
        fields = ("id", "event_key", "audience", "title", "body", "link", "created_at", "read_at")
        read_only_fields = fields


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField(min_value=0)


class MarkReadSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, max_length=500
    )
    all = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not attrs.get("all") and not attrs.get("ids"):
            raise serializers.ValidationError('Provide "ids" or "all": true.')
        return attrs
