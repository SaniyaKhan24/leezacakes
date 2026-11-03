from django.contrib import admin, messages

from .models import Enquiry
from .services import set_status


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "kind",
        "name",
        "email",
        "phone",
        "event_date",
        "servings",
        "status",
        "created_at",
    )
    list_filter = ("status", "kind", "event_date", "created_at")
    search_fields = ("reference", "name", "email", "phone", "occasion", "message")
    ordering = ("-created_at",)
    readonly_fields = (
        "reference",
        "kind",
        "name",
        "email",
        "phone",
        "occasion",
        "event_date",
        "servings",
        "budget",
        "message",
        "created_at",
        "updated_at",
    )
    fields = ("status", *readonly_fields)
    actions = ("mark_contacted", "mark_closed")

    def has_add_permission(self, request):
        return False

    @admin.action(description="Mark as contacted", permissions=["change"])
    def mark_contacted(self, request, queryset):
        count = set_status(queryset, Enquiry.CONTACTED)
        self.message_user(request, f"{count} enquiry(ies) marked contacted.", messages.SUCCESS)

    @admin.action(description="Mark as closed", permissions=["change"])
    def mark_closed(self, request, queryset):
        count = set_status(queryset, Enquiry.CLOSED)
        self.message_user(request, f"{count} enquiry(ies) closed.", messages.SUCCESS)
