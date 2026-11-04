from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .models import DeliveryAttempt, Notification, NotificationPreference


class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReadStateFilter(admin.SimpleListFilter):
    title = "read"
    parameter_name = "read"

    def lookups(self, request, model_admin):
        return (("unread", "Unread"), ("read", "Read"))

    def queryset(self, request, queryset):
        if self.value() == "unread":
            return queryset.filter(read_at__isnull=True)
        if self.value() == "read":
            return queryset.filter(read_at__isnull=False)
        return queryset


class DeliveryAttemptInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = DeliveryAttempt
    extra = 0
    fields = (
        "channel",
        "recipient",
        "status",
        "attempt_count",
        "next_attempt_at",
        "provider_message_id",
        "error_message",
        "updated_at",
    )
    readonly_fields = fields


STATUS_COLOURS = {
    DeliveryAttempt.SENT: "#1a7f37",
    DeliveryAttempt.FAILED: "#cf222e",
    DeliveryAttempt.SKIPPED: "#6e7781",
    DeliveryAttempt.PENDING: "#9a6700",
}


@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "created_at",
        "event_key",
        "audience",
        "recipient",
        "title",
        "is_read",
        "deliveries",
    )
    list_filter = ("audience", "event_key", ReadStateFilter, "created_at")
    search_fields = ("deduplication_key", "user__email", "payload__order_number")
    list_select_related = ("user",)
    ordering = ("-created_at", "-id")
    date_hierarchy = "created_at"
    inlines = (DeliveryAttemptInline,)
    fields = (
        "event_key",
        "audience",
        "user",
        "title",
        "body",
        "link",
        "created_at",
        "read_at",
        "deduplication_key",
        "payload",
    )
    readonly_fields = fields

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                sent_count=Count("attempts", filter=Q(attempts__status=DeliveryAttempt.SENT)),
                failed_count=Count("attempts", filter=Q(attempts__status=DeliveryAttempt.FAILED)),
                skipped_count=Count("attempts", filter=Q(attempts__status=DeliveryAttempt.SKIPPED)),
            )
        )

    @admin.display(description="Recipient", ordering="user__email")
    def recipient(self, obj):
        if obj.user_id:
            return obj.user.email
        return "Staff email / WhatsApp" if obj.audience == Notification.STAFF else "-"

    @admin.display(description="Title")
    def title(self, obj):
        return obj.rendered["title"]

    @admin.display(description="Body")
    def body(self, obj):
        return obj.rendered["body"]

    @admin.display(description="Link")
    def link(self, obj):
        link = obj.rendered["link"]
        return format_html('<a href="{}">{}</a>', link, link) if link else "-"

    @admin.display(description="Read", boolean=True, ordering="read_at")
    def is_read(self, obj):
        return obj.read_at is not None if obj.user_id else None

    @admin.display(description="Deliveries")
    def deliveries(self, obj):
        parts = [
            (count, status)
            for count, status in (
                (getattr(obj, "sent_count", 0), DeliveryAttempt.SENT),
                (getattr(obj, "failed_count", 0), DeliveryAttempt.FAILED),
                (getattr(obj, "skipped_count", 0), DeliveryAttempt.SKIPPED),
            )
            if count
        ]
        if not parts:
            return "In-app only" if obj.user_id else "-"
        return format_html_join(
            " · ",
            '<span style="color:{}">{} {}</span>',
            ((STATUS_COLOURS[status], count, status) for count, status in parts),
        )


@admin.register(DeliveryAttempt)
class DeliveryAttemptAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "updated_at",
        "event",
        "channel",
        "recipient",
        "status",
        "attempt_count",
        "next_attempt_at",
        "delivered_at",
        "read_at",
        "error_message",
    )
    list_filter = ("channel", "status", "notification__audience", "notification__event_key")
    actions = ("retry_now",)
    search_fields = ("recipient", "provider_message_id", "notification__deduplication_key")
    list_select_related = ("notification",)
    ordering = ("-updated_at", "-id")
    fields = (
        "notification",
        "channel",
        "recipient",
        "status",
        "attempt_count",
        "provider_message_id",
        "error_message",
        "next_attempt_at",
        "last_attempt_at",
        "delivered_at",
        "read_at",
        "locked_until",
        "created_at",
        "updated_at",
    )
    readonly_fields = fields

    @admin.display(description="Event", ordering="notification__event_key")
    def event(self, obj):
        return obj.notification.event_key

    def has_retry_permission(self, request):
        return request.user.has_perm("notifications.change_deliveryattempt")

    @admin.action(description="Retry now (queue for the worker)", permissions=["retry"])
    def retry_now(self, request, queryset):
        # Anything not yet sent goes back on the queue; the worker picks it up in seconds.
        count = queryset.exclude(status=DeliveryAttempt.SENT).update(
            status=DeliveryAttempt.PENDING, next_attempt_at=timezone.now(), locked_until=None
        )
        self.message_user(request, f"Queued {count} deliveries; sent ones were left alone.")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "marketing_whatsapp_enabled",
        "marketing_sms_enabled",
        "marketing_email_enabled",
        "updated_at",
    )
    list_select_related = ("user",)
    readonly_fields = ("marketing_consent_recorded_at", "marketing_consent_source", "updated_at")


# WhatsApp settings and conversations are registered in whatsapp_admin.
from . import whatsapp_admin  # noqa: E402, F401
