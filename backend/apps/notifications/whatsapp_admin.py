"""Django admin for WhatsApp: the settings page with its operations, and conversations."""

import re

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db.models import Count, Q
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.accounts.validators import format_e164, to_e164_digits

from .messages import WHATSAPP_TEMPLATE_DEFS
from .models import WhatsAppConversation, WhatsAppMessage, WhatsAppSettings, WhatsAppTemplate
from .whatsapp_services import (
    WhatsAppError,
    check_connection,
    send_reply,
    send_template_to_conversation,
    send_test_message,
    submit_missing_templates,
    sync_templates,
    window_closes_at,
    within_service_window,
)


def settings_url():
    return reverse("admin:notifications_whatsappsettings_change", args=[1])


TEMPLATE_NAME = re.compile(r"^[a-z0-9_]{1,512}$")
API_VERSION = re.compile(r"^v\d{1,3}\.\d{1,2}$")


def secret_status(encrypted, plain):
    if not encrypted:
        return "Not set."
    if not plain:
        return "Saved, but it cannot be decrypted with FIELD_ENCRYPTION_KEY; enter it again."
    return "•••• saved. Leave blank to keep it."


class WhatsAppSettingsForm(forms.ModelForm):
    access_token = forms.CharField(
        label="Access token",
        required=False,
        strip=True,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "off"}),
    )
    clear_access_token = forms.BooleanField(label="Remove the saved access token", required=False)
    app_secret = forms.CharField(
        label="App secret",
        required=False,
        strip=True,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "off"}),
    )
    clear_app_secret = forms.BooleanField(label="Remove the saved app secret", required=False)

    class Meta:
        model = WhatsAppSettings
        fields = (
            "business_number",
            "sending_enabled",
            "provider",
            "phone_number_id",
            "business_account_id",
            "api_version",
            "template_language",
            "staff_alert_numbers",
            "staff_alert_emails",
        )
        widgets = {
            "staff_alert_numbers": forms.Textarea(attrs={"rows": 3, "cols": 40}),
            "staff_alert_emails": forms.Textarea(attrs={"rows": 3, "cols": 40}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        self.fields["access_token"].help_text = (
            "Permanent System User token with whatsapp_business_messaging and "
            "whatsapp_business_management. "
            + secret_status(instance.access_token_encrypted, instance.access_token)
        )
        self.fields["app_secret"].help_text = (
            "App Dashboard → App settings → Basic → App secret; signs webhook calls. "
            + secret_status(instance.app_secret_encrypted, instance.app_secret)
        )

    def clean_business_number(self):
        value = self.cleaned_data["business_number"].strip()
        if not value:
            return ""
        digits = to_e164_digits(value)
        if not digits:
            raise ValidationError("Enter a valid number with country code, e.g. +91 90000 00000.")
        return format_e164(digits)

    def clean_staff_alert_numbers(self):
        values = WhatsAppSettings.split_list(self.cleaned_data["staff_alert_numbers"])
        invalid = [value for value in values if not to_e164_digits(value)]
        if invalid:
            raise ValidationError(f"Not valid WhatsApp numbers: {', '.join(invalid)}.")
        unique = dict.fromkeys(format_e164(to_e164_digits(value)) for value in values)
        return "\n".join(unique)

    def clean_staff_alert_emails(self):
        values = WhatsAppSettings.split_list(self.cleaned_data["staff_alert_emails"])
        invalid = []
        for value in values:
            try:
                validate_email(value)
            except ValidationError:
                invalid.append(value)
        if invalid:
            raise ValidationError(f"Not valid email addresses: {', '.join(invalid)}.")
        return "\n".join(dict.fromkeys(value.lower() for value in values))

    def clean_api_version(self):
        value = self.cleaned_data["api_version"].strip()
        if not API_VERSION.match(value):
            raise ValidationError("Use the Graph API version format, e.g. v26.0.")
        return value

    def clean(self):
        cleaned = super().clean()
        token = cleaned.get("access_token") or (
            "" if cleaned.get("clear_access_token") else self.instance.access_token
        )
        if cleaned.get("sending_enabled"):
            missing = [
                label
                for label, present in (
                    ("phone number ID", cleaned.get("phone_number_id")),
                    ("access token", token),
                )
                if not present
            ]
            if missing:
                raise ValidationError(
                    f"Sending needs the {' and '.join(missing)}. Add them, then enable sending."
                )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        for name in ("access_token", "app_secret"):
            if self.cleaned_data.get(f"clear_{name}"):
                setattr(instance, name, "")
            if self.cleaned_data.get(name):
                setattr(instance, name, self.cleaned_data[name])
        if commit:
            instance.save()
        return instance


class WhatsAppTemplateForm(forms.ModelForm):
    class Meta:
        model = WhatsAppTemplate
        fields = ("template_name", "enabled")

    def clean_template_name(self):
        value = self.cleaned_data["template_name"].strip()
        if value and not TEMPLATE_NAME.match(value):
            raise ValidationError("Lowercase letters, digits and underscores only.")
        return value


class WhatsAppTemplateInline(admin.TabularInline):
    model = WhatsAppTemplate
    form = WhatsAppTemplateForm
    extra = 0
    can_delete = False
    fields = (
        "event",
        "template_name",
        "enabled",
        "body",
        "meta_status",
        "meta_rejected_reason",
        "last_synced_at",
    )
    readonly_fields = ("event", "body", "meta_status", "meta_rejected_reason", "last_synced_at")
    verbose_name_plural = "Templates (one per event; bodies are submitted to Meta as written)"

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Event")
    def event(self, obj):
        return obj.event_key.replace("_", " ")

    @admin.display(description="Body ({{n}} = variables)")
    def body(self, obj):
        definition = obj.definition
        return definition["body"] if definition else "-"


@admin.register(WhatsAppSettings)
class WhatsAppSettingsAdmin(admin.ModelAdmin):
    form = WhatsAppSettingsForm
    inlines = (WhatsAppTemplateInline,)
    change_form_template = "admin/notifications/whatsappsettings/change_form.html"
    readonly_fields = ("connection_status", "webhook_url", "webhook_verify_token")
    fieldsets = (
        (
            "Chat button",
            {
                "fields": ("business_number",),
                "description": "Shown on the website's WhatsApp buttons (wa.me click-to-chat).",
            },
        ),
        (
            "Sending (Cloud API)",
            {
                "fields": (
                    "sending_enabled",
                    "provider",
                    "phone_number_id",
                    "business_account_id",
                    "access_token",
                    "clear_access_token",
                    "api_version",
                    "template_language",
                    "connection_status",
                ),
                "description": (
                    "Order updates and staff alerts are sent as approved templates. Save, "
                    "then use Check connection, Submit missing templates and Send test "
                    "message above before enabling sending."
                ),
            },
        ),
        (
            "Staff alerts",
            {
                "fields": ("staff_alert_numbers", "staff_alert_emails"),
                "description": "Who is alerted about new orders and payment screenshots.",
            },
        ),
        (
            "Webhook",
            {
                "fields": ("webhook_url", "webhook_verify_token", "app_secret", "clear_app_secret"),
                "description": (
                    "In the Meta App Dashboard → WhatsApp → Configuration, paste the callback "
                    "URL and verify token below, then subscribe to the “messages” field. "
                    "Delivery receipts and customer replies arrive here."
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_object(self, request, object_id, from_field=None):
        WhatsAppSettings.load()  # creates the row and default templates on first visit
        return super().get_object(request, object_id, from_field)

    def changelist_view(self, request, extra_context=None):
        WhatsAppSettings.load()
        return HttpResponseRedirect(
            reverse("admin:notifications_whatsappsettings_change", args=[1])
        )

    @admin.display(description="Last connection check")
    def connection_status(self, obj):
        if not obj.last_check_at:
            return "Not checked yet."
        return f"{timezone.localtime(obj.last_check_at):%d %b %Y, %H:%M} — {obj.last_check_result}"

    @admin.display(description="Callback URL")
    def webhook_url(self, obj):
        url = obj.webhook_url()
        hint = "" if url.startswith("https://") else " (Meta requires a public https:// URL)"
        return format_html("<code>{}</code>{}", url, hint)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "test_events": [
                (key, definition["name"]) for key, definition in WHATSAPP_TEMPLATE_DEFS.items()
            ],
            "can_operate": self.has_change_permission(request),
        }
        return super().change_view(request, object_id, form_url, extra_context)

    def get_urls(self):
        operations = [
            ("check-connection", self.check_connection_view, "check"),
            ("sync-templates", self.sync_templates_view, "sync"),
            ("submit-templates", self.submit_templates_view, "submit"),
            ("send-test", self.send_test_view, "send_test"),
        ]
        return [
            path(
                f"operations/{slug}/",
                self.admin_site.admin_view(view),
                name=f"notifications_whatsappsettings_{name}",
            )
            for slug, view, name in operations
        ] + super().get_urls()

    # Operations (POST + CSRF via admin_view, change permission) -----------------------------

    def _operate(self, request, action):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        if not self.has_change_permission(request):
            raise PermissionDenied
        WhatsAppSettings.invalidate()
        try:
            action(WhatsAppSettings.load())
        except WhatsAppError as exc:
            self.message_user(request, str(exc), messages.ERROR)
        return HttpResponseRedirect(
            reverse("admin:notifications_whatsappsettings_change", args=[1])
        )

    def check_connection_view(self, request):
        def action(config):
            ok, text = check_connection(config)
            self.message_user(request, text, messages.SUCCESS if ok else messages.ERROR)

        return self._operate(request, action)

    def sync_templates_view(self, request):
        def action(config):
            results = sync_templates(config)
            summary = ", ".join(f"{t.template_name}: {status}" for t, status in results)
            self.message_user(request, f"Template status synced. {summary}", messages.SUCCESS)

        return self._operate(request, action)

    def submit_templates_view(self, request):
        def action(config):
            results = submit_missing_templates(config)
            if not results:
                self.message_user(
                    request, "Nothing to submit: every enabled template exists in Meta."
                )
            for template, ok, text in results:
                level = messages.SUCCESS if ok else messages.ERROR
                self.message_user(request, f"{template.template_name}: {text}", level)

        return self._operate(request, action)

    def send_test_view(self, request):
        def action(config):
            number = request.POST.get("test_number", "")
            event_key = request.POST.get("test_event", "")
            result = send_test_message(config, number, event_key, user=request.user)
            if result.status == "sent":
                self.message_user(
                    request,
                    f"Test message sent to {format_e164(to_e164_digits(number))} "
                    f"(message id {result.provider_message_id}).",
                    messages.SUCCESS,
                )
            else:
                self.message_user(request, f"Test message failed: {result.error}", messages.ERROR)

        return self._operate(request, action)


# Conversations --------------------------------------------------------------------------------


class ReplyForm(forms.Form):
    text = forms.CharField(
        label="Reply", max_length=4096, widget=forms.Textarea(attrs={"rows": 3, "cols": 60})
    )


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "number",
        "unread",
        "latest_message",
        "linked_customer",
        "linked_order",
        "last_message_at",
        "reply_window",
    )
    search_fields = ("customer_number", "contact_name", "user__email", "order__order_number")
    list_select_related = ("user", "order")
    ordering = ("-last_message_at", "-id")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(
                        messages__direction=WhatsAppMessage.INBOUND,
                        messages__read_by_staff_at__isnull=True,
                    ),
                )
            )
        )

    @admin.display(description="Customer", ordering="contact_name")
    def customer(self, obj):
        return obj.display_name

    @admin.display(description="Number", ordering="customer_number")
    def number(self, obj):
        return format_e164(obj.customer_number)

    @admin.display(description="Unread", ordering="unread_count")
    def unread(self, obj):
        count = getattr(obj, "unread_count", 0)
        return format_html("<strong>{}</strong>", count) if count else "-"

    @admin.display(description="Latest message")
    def latest_message(self, obj):
        message = obj.messages.order_by("-timestamp", "-id").first()
        if not message:
            return "-"
        arrow = "←" if message.direction == WhatsAppMessage.INBOUND else "→"
        text = message.body if len(message.body) <= 80 else f"{message.body[:79]}…"
        return f"{arrow} {text}"

    @admin.display(description="Account")
    def linked_customer(self, obj):
        return obj.user.email if obj.user_id else "-"

    @admin.display(description="Order")
    def linked_order(self, obj):
        if not obj.order_id:
            return "-"
        url = reverse("admin:orders_order_change", args=[obj.order_id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)

    @admin.display(description="Free-form replies")
    def reply_window(self, obj):
        return "open" if within_service_window(obj) else "template only"

    def get_urls(self):
        return [
            path(
                "<int:object_id>/reply/",
                self.admin_site.admin_view(self.reply_view),
                name="notifications_whatsappconversation_reply",
            ),
            path(
                "<int:object_id>/send-template/",
                self.admin_site.admin_view(self.send_template_view),
                name="notifications_whatsappconversation_send_template",
            ),
        ] + super().get_urls()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        conversation = get_object_or_404(WhatsAppConversation, pk=object_id)
        if not self.has_view_or_change_permission(request, conversation):
            raise PermissionDenied
        conversation.messages.filter(
            direction=WhatsAppMessage.INBOUND, read_by_staff_at__isnull=True
        ).update(read_by_staff_at=timezone.now())
        config = WhatsAppSettings.load()
        templates = [
            (key, config.template_for(key).template_name)
            for key in WHATSAPP_TEMPLATE_DEFS
            if config.template_for(key) and not key.startswith("staff_")
        ]
        context = {
            **self.admin_site.each_context(request),
            "opts": self.opts,
            "title": f"WhatsApp with {conversation.display_name}",
            "subtitle": format_e164(conversation.customer_number),
            "conversation": conversation,
            "number": format_e164(conversation.customer_number),
            "thread": conversation.messages.select_related("sent_by").order_by("timestamp", "id"),
            "window_open": within_service_window(conversation),
            "window_closes_at": window_closes_at(conversation),
            "reply_form": ReplyForm(),
            "templates": templates,
            "can_reply": self.has_change_permission(request, conversation),
            "has_view_permission": True,
            **(extra_context or {}),
        }
        return TemplateResponse(
            request, "admin/notifications/whatsappconversation/thread.html", context
        )

    def _conversation_action(self, request, object_id, action):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        conversation = get_object_or_404(WhatsAppConversation, pk=object_id)
        if not self.has_change_permission(request, conversation):
            raise PermissionDenied
        try:
            message = action(conversation)
        except WhatsAppError as exc:
            self.message_user(request, str(exc), messages.ERROR)
        else:
            if message is not None and message.status == "failed":
                self.message_user(request, f"Not sent: {message.error_message}", messages.ERROR)
            elif message is not None:
                self.message_user(request, "Sent.", messages.SUCCESS)
        return HttpResponseRedirect(
            reverse("admin:notifications_whatsappconversation_change", args=[conversation.pk])
        )

    def reply_view(self, request, object_id):
        def action(conversation):
            form = ReplyForm(request.POST)
            if not form.is_valid():
                raise WhatsAppError("Write a message of up to 4096 characters.")
            return send_reply(conversation, form.cleaned_data["text"], request.user)

        return self._conversation_action(request, object_id, action)

    def send_template_view(self, request, object_id):
        def action(conversation):
            return send_template_to_conversation(
                conversation, request.POST.get("event_key", ""), request.user
            )

        return self._conversation_action(request, object_id, action)
