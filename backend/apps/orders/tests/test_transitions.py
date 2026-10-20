import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.orders.models import Order
from apps.orders.services.transitions import transition_order


def test_transition_rejects_unverified_confirmation(db):
    user = User.objects.create_user(email="transition@example.com")
    order = Order.objects.create(
        order_number="LZ-TRANSITION",
        user=user,
        customer_name="A",
        customer_phone="+919876543210",
        pickup_slot_start=timezone.now(),
        pickup_slot_end=timezone.now(),
        subtotal="10.00",
        tax_total="0.00",
        grand_total="10.00",
        idempotency_key="transition",
        request_fingerprint="x",
    )
    with pytest.raises(ValidationError):
        transition_order(order, Order.CONFIRMED, actor=user)
