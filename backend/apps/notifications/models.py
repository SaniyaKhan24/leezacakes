import secrets

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property


class Notification(models.Model):
    TRANSACTIONAL = "transactional"
    CUSTOMER = "customer"
    STAFF = "staff"
    AUDIENCE_CHOICES = ((CUSTOMER, "Customer"), (STAFF, "Staff"))
    CUSTOMER_EVENT_KEYS = (
        "order_created",
        "payment_submitted",
        "payment_verified",
        "order_confirmed",
        "preparing",
        "ready",
        "completed",
        "payment_rejected",
    )
    STAFF_EVENT_KEYS = (
        "staff_order_created",
        "staff_payment_submitted",
        "staff_whatsapp_message",
    )
    # Shown in-app only (no staff email/WhatsApp), e.g. to avoid WhatsApp reply loops.
    IN_APP_ONLY_EVENT_KEYS = ("staff_whatsapp_message",)
    EVENT_KEYS = CUSTOMER_EVENT_KEYS + STAFF_EVENT_KEYS
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="notifications",
    )
    audience = models.CharField(
        max_length=10, choices=AUDIENCE_CHOICES, default=CUSTOMER, db_index=True
    )
    event_key = models.CharField(max_length=40)
    category = models.CharField(max_length=20, default=TRANSACTIONAL)
    deduplication_key = models.CharField(max_length=180, unique=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("event_key", "created_at")),
            models.Index(fields=("user", "read_at"), name="notification_user_unread_idx"),
        ]

    def __str__(self):
        return f"{self.event_key}:{self.deduplication_key}"

    @cached_property
    def rendered(self):
        """Copy for this notification, rendered from its payload at read time."""
        from .messages import render

        return render(self.event_key, self.payload)


class DeliveryAttempt(models.Model):
    PENDING = "pending"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (SENT, "Sent"),
        (SKIPPED, "Skipped"),
        (FAILED, "Failed"),
    )
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="attempts"
    )
    channel = models.CharField(max_length=20)
    # Email address or E.164 digits; blank when the recipient is missing.
    recipient = models.CharField(max_length=254, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    provider_message_id = models.CharField(max_length=180, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    # Outbox scheduling: the worker picks up rows whose next_attempt_at has passed.
    # NULL means nothing more to do (sent, skipped, or gave up after retries).
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    # A worker holds a short lease while sending, so two workers never send the
    # same message; a crashed worker's lease simply expires.
    locked_until = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    # WhatsApp delivery receipts from the webhook.
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("notification", "channel", "recipient"),
                name="unique_delivery_per_channel_recipient",
            )
        ]
        indexes = [models.Index(fields=("next_attempt_at",), name="delivery_due_idx")]

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


# WhatsApp ------------------------------------------------------------------------------------


def _verify_token():
    return secrets.token_urlsafe(24)


class WhatsAppSettings(models.Model):
    """Singleton (pk=1) edited in admin: chat button, Cloud API sending, staff alert
    recipients and the webhook. Secrets are stored encrypted (FIELD_ENCRYPTION_KEY)."""

    CACHE_KEY = "notifications:whatsapp-settings"
    CACHE_SECONDS = 15
    PROVIDER_CHOICES = (("meta_cloud", "Meta WhatsApp Cloud API"),)

    business_number = models.CharField(
        "WhatsApp chat number",
        max_length=32,
        blank=True,
        help_text="Public number for the storefront's WhatsApp buttons, e.g. +91 90000 00000.",
    )
    sending_enabled = models.BooleanField(
        default=False,
        help_text="Send order updates and staff alerts as WhatsApp template messages.",
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="meta_cloud")
    phone_number_id = models.CharField(
        "Phone number ID",
        max_length=64,
        blank=True,
        help_text="WhatsApp Manager / App Dashboard → WhatsApp → API Setup → Phone number ID.",
    )
    business_account_id = models.CharField(
        "WhatsApp Business Account ID",
        max_length=64,
        blank=True,
        help_text="The WABA ID from API Setup; needed to sync and submit templates.",
    )
    api_version = models.CharField("Graph API version", max_length=16, default="v26.0")
    template_language = models.CharField(
        max_length=16, default="en", help_text="Language code of the templates, e.g. en."
    )
    access_token_encrypted = models.TextField(blank=True, editable=False)
    app_secret_encrypted = models.TextField(blank=True, editable=False)
    webhook_verify_token = models.CharField(max_length=64, default=_verify_token, editable=False)
    staff_alert_numbers = models.TextField(
        "Staff WhatsApp numbers",
        blank=True,
        help_text="One per line (or comma separated), with country code.",
    )
    staff_alert_emails = models.TextField(
        "Staff alert emails", blank=True, help_text="One per line (or comma separated)."
    )
    last_check_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_check_result = models.TextField(blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "WhatsApp & alert settings"
        verbose_name_plural = "WhatsApp & alert settings"

    def __str__(self):
        return "WhatsApp & alert settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    def delete(self, *args, **kwargs):  # the singleton is never deleted
        return 0, {}

    @classmethod
    def load(cls):
        """The settings row (created with default templates on first use), cached for a
        few seconds per process and invalidated whenever settings or templates are saved."""
        cached = cache.get(cls.CACHE_KEY)
        if cached is not None:
            return cached
        instance, _ = cls.objects.get_or_create(pk=1)
        instance.ensure_templates()
        instance.template_map = {t.event_key: t for t in instance.templates.all()}
        cache.set(cls.CACHE_KEY, instance, cls.CACHE_SECONDS)
        return instance

    get_solo = load

    @classmethod
    def invalidate(cls):
        cache.delete(cls.CACHE_KEY)

    def ensure_templates(self):
        from .messages import WHATSAPP_TEMPLATE_DEFS

        existing = set(self.templates.values_list("event_key", flat=True))
        missing = [
            WhatsAppTemplate(
                settings_id=self.pk,
                event_key=event_key,
                template_name=definition["name"],
                enabled=definition["enabled"],
            )
            for event_key, definition in WHATSAPP_TEMPLATE_DEFS.items()
            if event_key not in existing
        ]
        if missing:
            WhatsAppTemplate.objects.bulk_create(missing)

    # Secrets ------------------------------------------------------------------------------

    @property
    def access_token(self):
        from apps.common.crypto import decrypt

        return decrypt(self.access_token_encrypted) or ""

    @access_token.setter
    def access_token(self, value):
        from apps.common.crypto import encrypt

        self.access_token_encrypted = encrypt(value)

    @property
    def app_secret(self):
        from apps.common.crypto import decrypt

        return decrypt(self.app_secret_encrypted) or ""

    @app_secret.setter
    def app_secret(self, value):
        from apps.common.crypto import encrypt

        self.app_secret_encrypted = encrypt(value)

    # Derived values -----------------------------------------------------------------------

    @staticmethod
    def split_list(value):
        return [
            part.strip() for part in (value or "").replace(",", "\n").splitlines() if part.strip()
        ]

    @property
    def staff_numbers(self):
        """Staff WhatsApp numbers as stored (validated E.164 with +)."""
        return self.split_list(self.staff_alert_numbers)

    @property
    def staff_emails(self):
        return self.split_list(self.staff_alert_emails)

    @property
    def business_number_digits(self):
        from apps.accounts.validators import to_e164_digits

        return to_e164_digits(self.business_number)

    def can_send(self):
        return bool(self.sending_enabled and self.phone_number_id and self.access_token)

    def template_for(self, event_key):
        """The enabled template mapping for an event, or None."""
        mapping = getattr(self, "template_map", None)
        if mapping is None:
            mapping = {t.event_key: t for t in self.templates.all()}
        template = mapping.get(event_key)
        if template and template.enabled and template.template_name:
            return template
        return None

    @staticmethod
    def webhook_path():
        return reverse("notifications:whatsapp-webhook")

    def webhook_url(self):
        return f"{settings.BACKEND_PUBLIC_URL}{self.webhook_path()}"


class WhatsAppTemplate(models.Model):
    """Which approved Meta template each event uses, and its last known Meta status."""

    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"
    MISSING = "MISSING"
    STATUS_CHOICES = (
        (APPROVED, "Approved"),
        (PENDING, "Pending review"),
        (REJECTED, "Rejected"),
        (PAUSED, "Paused"),
        (DISABLED, "Disabled"),
        (MISSING, "Not in Meta"),
    )
    settings = models.ForeignKey(
        WhatsAppSettings, on_delete=models.CASCADE, related_name="templates"
    )
    event_key = models.CharField(max_length=40, unique=True)
    template_name = models.CharField(max_length=512, blank=True)
    enabled = models.BooleanField(default=True)
    meta_status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True)
    meta_rejected_reason = models.CharField(max_length=255, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("id",)
        verbose_name = "WhatsApp template"

    def __str__(self):
        return f"{self.event_key} → {self.template_name or '-'}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        WhatsAppSettings.invalidate()

    @property
    def definition(self):
        from .messages import WHATSAPP_TEMPLATE_DEFS

        return WHATSAPP_TEMPLATE_DEFS.get(self.event_key)


class WhatsAppConversation(models.Model):
    """All WhatsApp messages with one customer number."""

    customer_number = models.CharField(max_length=20, unique=True)  # E.164 digits
    contact_name = models.CharField(max_length=160, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="whatsapp_conversations",
    )
    order = models.ForeignKey(
        "orders.Order",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="The customer's most recent order when the conversation was matched.",
    )
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_inbound_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-last_message_at", "-id")
        verbose_name = "WhatsApp conversation"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.contact_name or f"+{self.customer_number}"


class WhatsAppMessage(models.Model):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    DIRECTION_CHOICES = ((INBOUND, "From customer"), (OUTBOUND, "From the studio"))
    conversation = models.ForeignKey(
        WhatsAppConversation, on_delete=models.CASCADE, related_name="messages"
    )
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    wa_message_id = models.CharField(max_length=180, unique=True, null=True, blank=True)
    from_number = models.CharField(max_length=20, blank=True)
    to_number = models.CharField(max_length=20, blank=True)
    contact_name = models.CharField(max_length=160, blank=True)
    message_type = models.CharField(max_length=30, default="text")
    body = models.TextField(blank=True)
    timestamp = models.DateTimeField()
    # Outbound delivery state (sent / delivered / read / failed) from status webhooks.
    status = models.CharField(max_length=20, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    read_by_staff_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("timestamp", "id")
        indexes = [models.Index(fields=("conversation", "direction", "read_by_staff_at"))]
        verbose_name = "WhatsApp message"

    def __str__(self):
        return f"{self.direction}:{self.wa_message_id or self.pk}"
