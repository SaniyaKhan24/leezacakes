from django.conf import settings
from django.db import models


class Notification(models.Model):
    TRANSACTIONAL = "transactional"
    EVENT_KEYS = (
        "order_created",
        "payment_verified",
        "order_confirmed",
        "preparing",
        "ready",
        "completed",
        "payment_rejected",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    event_key = models.CharField(max_length=40)
    category = models.CharField(max_length=20, default=TRANSACTIONAL)
    deduplication_key = models.CharField(max_length=180, unique=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=("event_key", "created_at"))]

    def __str__(self):
        return f"{self.event_key}:{self.deduplication_key}"


class DeliveryAttempt(models.Model):
    PENDING = "pending"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="attempts"
    )
    channel = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default=PENDING)
    provider_message_id = models.CharField(max_length=180, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.notification_id}:{self.channel}:{self.status}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    marketing_whatsapp_enabled = models.BooleanField(default=False)
    marketing_sms_enabled = models.BooleanField(default=False)
    marketing_email_enabled = models.BooleanField(default=False)
    marketing_consent_recorded_at = models.DateTimeField(null=True, blank=True)
    marketing_consent_source = models.CharField(max_length=80, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification preferences for {self.user_id}"
