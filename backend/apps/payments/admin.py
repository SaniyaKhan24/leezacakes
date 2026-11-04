from django.contrib import admin, messages
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html
from rest_framework.exceptions import ValidationError

from .models import Payment, PaymentStatusHistory, PaymentSubmission
from .services import review_submission, verify_payment

DEFAULT_REJECTION_REASON = (
    "We could not match this proof to a received UPI payment. Please upload a clear "
    "screenshot that shows the amount, the date and the UPI reference (UTR) number."
)


def evidence_url(submission):
    return reverse(
        "payments:staff-evidence",
        kwargs={"payment_id": submission.payment_id, "submission_id": submission.pk},
    )


def _error_text(exc):
    detail = exc.detail
    if isinstance(detail, dict):
        parts = []
        for value in detail.values():
            parts.extend(value if isinstance(value, list) else [value])
        return " ".join(str(part) for part in parts)
    if isinstance(detail, list):
        return " ".join(str(part) for part in detail)
    return str(detail)


class SubmissionInline(admin.TabularInline):
    model = PaymentSubmission
    extra = 0
    can_delete = False
    fields = (
        "evidence_preview",
        "status",
        "submitted_by",
        "submitted_at",
        "original_filename",
        "file_size",
        "reviewed_by",
        "reviewed_at",
        "rejection_reason",
    )
    readonly_fields = fields
    ordering = ("-submitted_at",)

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Proof")
    def evidence_preview(self, obj):
        if not obj.pk or not obj.evidence_file:
            return "-"
        url = evidence_url(obj)
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            '<img src="{}" alt="Payment proof" style="max-height:140px;max-width:140px;'
            'border-radius:6px;border:1px solid #ddd"><br>Open full size</a>',
            url,
            url,
        )


class PaymentStatusHistoryInline(admin.TabularInline):
    model = PaymentStatusHistory
    extra = 0
    can_delete = False
    fields = ("created_at", "from_status", "to_status", "changed_by", "reason")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer",
        "status",
        "amount_due",
        "latest_proof",
        "created_at",
        "verified_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = ("order__order_number", "user__email", "order__customer_name")
    list_select_related = ("order", "user")
    ordering = ("-created_at",)
    readonly_fields = (
        "order",
        "user",
        "method",
        "status",
        "amount_due",
        "currency",
        "verified_amount",
        "verified_by",
        "verified_at",
        "created_at",
        "updated_at",
    )
    fields = readonly_fields
    inlines = (SubmissionInline, PaymentStatusHistoryInline)
    actions = ("accept_and_verify", "reject_latest")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_verify_permission(self, request):
        return request.user.is_superuser or request.user.has_perm("payments.verify_payment")

    @admin.display(description="Order", ordering="order__order_number")
    def order_number(self, obj):
        return obj.order.order_number

    @admin.display(description="Customer", ordering="user__email")
    def customer(self, obj):
        return f"{obj.order.customer_name} <{obj.user.email}>"

    @admin.display(description="Latest proof")
    def latest_proof(self, obj):
        submission = obj.submissions.first()
        if not submission:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{}</a>',
            evidence_url(submission),
            submission.get_status_display(),
        )

    @admin.action(description="Accept latest proof and verify payment", permissions=["verify"])
    def accept_and_verify(self, request, queryset):
        verified = 0
        for payment in queryset.select_related("order"):
            label = payment.order.order_number
            submission = payment.submissions.first()
            if submission is None:
                self.message_user(
                    request, f"{label}: no payment proof has been uploaded.", messages.ERROR
                )
                continue
            try:
                with transaction.atomic():
                    if submission.status == PaymentSubmission.PENDING_REVIEW:
                        submission = review_submission(payment, submission, request.user, "accept")
                    verify_payment(
                        payment,
                        submission,
                        request.user,
                        payment.amount_due,
                        reason="Verified in admin.",
                    )
            except ValidationError as exc:
                self.message_user(request, f"{label}: {_error_text(exc)}", messages.ERROR)
                continue
            verified += 1
        if verified:
            self.message_user(
                request, f"Verified {verified} payment(s); orders are confirmed.", messages.SUCCESS
            )

    @admin.action(description="Reject latest proof", permissions=["verify"])
    def reject_latest(self, request, queryset):
        rejected = 0
        for payment in queryset.select_related("order"):
            label = payment.order.order_number
            submission = payment.submissions.first()
            if submission is None or submission.status != PaymentSubmission.PENDING_REVIEW:
                self.message_user(
                    request, f"{label}: there is no proof waiting for review.", messages.ERROR
                )
                continue
            try:
                review_submission(
                    payment, submission, request.user, "reject", DEFAULT_REJECTION_REASON
                )
            except ValidationError as exc:
                self.message_user(request, f"{label}: {_error_text(exc)}", messages.ERROR)
                continue
            rejected += 1
        if rejected:
            self.message_user(
                request,
                f"Rejected {rejected} proof(s); customers can upload a new one.",
                messages.SUCCESS,
            )


@admin.register(PaymentStatusHistory)
class PaymentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("payment", "from_status", "to_status", "changed_by", "created_at")
    readonly_fields = [field.name for field in PaymentStatusHistory._meta.fields]
