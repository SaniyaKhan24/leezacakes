from django.contrib import admin

from .models import Payment, PaymentStatusHistory, PaymentSubmission


class SubmissionInline(admin.TabularInline):
    model = PaymentSubmission
    extra = 0
    readonly_fields = ("submitted_by", "evidence_file", "status", "reviewed_by", "reviewed_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "amount_due", "currency", "verified_at")
    list_filter = ("status", "currency")
    readonly_fields = (
        "order",
        "user",
        "amount_due",
        "verified_amount",
        "verified_by",
        "verified_at",
    )
    inlines = (SubmissionInline,)


@admin.register(PaymentStatusHistory)
class PaymentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("payment", "from_status", "to_status", "changed_by", "created_at")
    readonly_fields = [field.name for field in PaymentStatusHistory._meta.fields]
