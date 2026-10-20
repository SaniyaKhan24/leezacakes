import hashlib
import json
import secrets
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.cart.models import Cart
from apps.cart.services.cart_service import validate_cart
from apps.cart.services.pricing import cart_pricing

from ..models import Order, OrderItem, OrderItemCustomization, OrderStatusHistory


def _fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def _order_number():
    return f"LZ-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def _tax(subtotal):
    if not getattr(settings, "ORDER_TAX_POLICY_CONFIGURED", False):
        raise ValidationError(
            {"checkout": "Checkout is unavailable until tax policy is configured."}
        )
    rate = getattr(settings, "ORDER_TAX_RATE", None)
    if rate is None:
        raise ValidationError(
            {"checkout": "Checkout is unavailable until tax policy is configured."}
        )
    return (subtotal * Decimal(str(rate)) / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


@transaction.atomic
def create_order(user, checkout_data, idempotency_key):
    fingerprint = _fingerprint(checkout_data)
    existing = (
        Order.objects.select_for_update().filter(user=user, idempotency_key=idempotency_key).first()
    )
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise ValidationError(
                {"idempotency_key": "This key was already used for different checkout data."}
            )
        return existing, False
    cart = Cart.objects.select_for_update().filter(user=user, status=Cart.ACTIVE).first()
    if not cart or not cart.items.exists():
        raise ValidationError({"cart": "Cart is empty."})
    validation = validate_cart(cart)
    if not validation["valid"]:
        raise ValidationError({"cart": validation["issues"]})
    if validation["price_confirmation_required"]:
        raise ValidationError({"cart": "Price confirmation is required before checkout."})
    start = checkout_data["pickup_slot_start"]
    end = checkout_data["pickup_slot_end"]
    if timezone.is_naive(start) or timezone.is_naive(end) or end <= start:
        raise ValidationError(
            {"pickup_slot": "Pickup slot must be a valid timezone-aware interval."}
        )
    lines, subtotal = cart_pricing(cart)
    tax = _tax(subtotal)
    grand = subtotal + tax
    order = Order.objects.create(
        order_number=_order_number(),
        user=user,
        customer_name=checkout_data["customer_name"].strip(),
        customer_phone=checkout_data["customer_phone"],
        customer_email=checkout_data.get("customer_email") or "",
        pickup_slot_start=start,
        pickup_slot_end=end,
        subtotal=subtotal,
        tax_total=tax,
        grand_total=grand,
        customer_note=checkout_data.get("customer_note", ""),
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
    )
    for item, pricing in lines:
        order_item = OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            product_name_snapshot=item.product.name,
            variant_name_snapshot=item.variant.name if item.variant_id else "",
            sku_snapshot=item.variant.sku if item.variant_id and item.variant.sku else "",
            quantity=item.quantity,
            unit_base_price=pricing["base"],
            unit_customization_total=pricing["customization"],
            unit_price=pricing["unit"],
            line_total=pricing["line"],
        )
        for selection in item.customizations.select_related("option", "choice"):
            OrderItemCustomization.objects.create(
                order_item=order_item,
                option=selection.option,
                choice=selection.choice,
                option_name_snapshot=selection.option.name,
                choice_name_snapshot=selection.choice.name if selection.choice_id else "",
                value_snapshot=selection.text_value,
                price_adjustment=selection.price_adjustment,
            )
    OrderStatusHistory.objects.create(order=order, to_status=Order.PENDING_PAYMENT)
    from apps.notifications.services import emit_event
    from apps.payments.services import create_payment_for_order

    create_payment_for_order(order)
    emit_event(
        "order_created",
        user=user,
        payload={"order_number": order.order_number},
        deduplication_key=f"order:{order.id}:order_created",
    )
    cart.status = Cart.CONVERTED
    cart.save(update_fields=("status", "updated_at"))
    return order, True
