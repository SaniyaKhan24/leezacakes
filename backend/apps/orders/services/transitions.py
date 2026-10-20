from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ..models import Order, OrderStatusHistory

ALLOWED = {
    Order.PENDING_PAYMENT: {Order.CONFIRMED},
    Order.CONFIRMED: {Order.PREPARING},
    Order.PREPARING: {Order.READY},
    Order.READY: {Order.COMPLETED},
}


@transaction.atomic
def transition_order(order, to_status, actor, reason=""):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if to_status not in ALLOWED.get(order.status, set()):
        raise ValidationError({"to_status": "This order transition is not allowed."})
    if to_status == Order.CONFIRMED and order.payment_status != Order.PAYMENT_VERIFIED:
        raise ValidationError({"to_status": "Payment must be verified before confirmation."})
    old = order.status
    order.status = to_status
    now = timezone.now()
    if to_status == Order.CONFIRMED:
        order.confirmed_at = now
    if to_status == Order.COMPLETED:
        order.completed_at = now
    order.save(update_fields=("status", "confirmed_at", "completed_at", "updated_at"))
    OrderStatusHistory.objects.create(
        order=order, from_status=old, to_status=to_status, changed_by=actor, reason=reason
    )
    from apps.notifications.services import emit_event

    event_key = {
        Order.CONFIRMED: "order_confirmed",
        Order.PREPARING: "preparing",
        Order.READY: "ready",
        Order.COMPLETED: "completed",
    }.get(to_status)
    if event_key:
        emit_event(
            event_key,
            user=order.user,
            payload={"order_number": order.order_number, "status": to_status},
            deduplication_key=f"order:{order.id}:{event_key}",
        )
    return order
