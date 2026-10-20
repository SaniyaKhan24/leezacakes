from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Payment, PaymentStatusHistory, PaymentSubmission


def create_payment_for_order(order):
    payment, _ = Payment.objects.get_or_create(
        order=order,
        defaults={
            "user": order.user,
            "amount_due": order.grand_total,
            "currency": order.currency,
        },
    )
    return payment


@transaction.atomic
def submit_evidence(payment, user, evidence):
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.user_id != user.id:
        raise ValidationError({"payment": "Payment was not found."})
    if payment.status == Payment.VERIFIED:
        raise ValidationError({"payment": "Verified payments cannot receive new evidence."})
    old_status = payment.status
    submission = PaymentSubmission(
        payment=payment,
        submitted_by=user,
        original_filename=evidence.name[:255],
        content_type=getattr(evidence, "content_type", "application/octet-stream"),
        file_size=evidence.size,
    )
    try:
        submission.evidence_file.save(f"{uuid4().hex}.upload", evidence, save=False)
        submission.save()
    except Exception as exc:
        raise ValidationError({"evidence": "Private evidence storage is unavailable."}) from exc
    payment.status = Payment.PENDING
    payment.save(update_fields=("status", "updated_at"))
    if old_status != Payment.PENDING:
        PaymentStatusHistory.objects.create(
            payment=payment,
            from_status=old_status,
            to_status=Payment.PENDING,
            related_submission=submission,
        )
    return submission


@transaction.atomic
def review_submission(payment, submission, reviewer, decision, reason=""):
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    submission = PaymentSubmission.objects.select_for_update().get(
        pk=submission.pk, payment=payment
    )
    if submission.status != PaymentSubmission.PENDING_REVIEW:
        raise ValidationError({"submission": "This submission has already been reviewed."})
    submission.status = (
        PaymentSubmission.ACCEPTED if decision == "accept" else PaymentSubmission.REJECTED
    )
    submission.reviewed_by = reviewer
    submission.reviewed_at = timezone.now()
    submission.rejection_reason = reason if decision == "reject" else ""
    submission.save(update_fields=("status", "reviewed_by", "reviewed_at", "rejection_reason"))
    if decision == "reject":
        old = payment.status
        payment.status = Payment.REJECTED
        payment.save(update_fields=("status", "updated_at"))
        PaymentStatusHistory.objects.create(
            payment=payment,
            from_status=old,
            to_status=Payment.REJECTED,
            changed_by=reviewer,
            related_submission=submission,
            reason=reason,
        )
        from apps.notifications.services import emit_event

        emit_event(
            "payment_rejected",
            user=payment.user,
            payload={"order_number": payment.order.order_number},
            deduplication_key=f"submission:{submission.id}:payment_rejected",
        )
    return submission


@transaction.atomic
def verify_payment(payment, submission, reviewer, verified_amount, reason=""):
    from apps.orders.models import Order
    from apps.orders.services.transitions import transition_order

    payment = Payment.objects.select_for_update().select_related("order").get(pk=payment.pk)
    submission = PaymentSubmission.objects.select_for_update().get(
        pk=submission.pk, payment=payment
    )
    if payment.status == Payment.VERIFIED:
        return payment
    if submission.status != PaymentSubmission.ACCEPTED:
        raise ValidationError({"submission": "Evidence must be accepted before verification."})
    if Decimal(verified_amount) != payment.amount_due:
        raise ValidationError({"verified_amount": "Verified amount must match the order total."})
    old = payment.status
    payment.status = Payment.VERIFIED
    payment.verified_amount = verified_amount
    payment.verified_by = reviewer
    payment.verified_at = timezone.now()
    payment.save(
        update_fields=("status", "verified_amount", "verified_by", "verified_at", "updated_at")
    )
    PaymentStatusHistory.objects.create(
        payment=payment,
        from_status=old,
        to_status=Payment.VERIFIED,
        changed_by=reviewer,
        related_submission=submission,
        reason=reason,
    )
    order = payment.order
    order.payment_status = Order.PAYMENT_VERIFIED
    order.save(update_fields=("payment_status", "updated_at"))
    transition_order(order, Order.CONFIRMED, actor=reviewer, reason="Payment manually verified.")
    from apps.notifications.services import emit_event

    emit_event(
        "payment_verified",
        user=order.user,
        payload={"order_number": order.order_number},
        deduplication_key=f"payment:{payment.id}:payment_verified",
    )
    return payment
