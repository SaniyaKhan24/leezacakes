from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.orders.models import Order
from apps.payments.models import Payment


@pytest.fixture
def order(db):
    user = User.objects.create_user(email="payment@example.com")
    return Order.objects.create(
        order_number="LZ-TEST-1",
        user=user,
        customer_name="Buyer",
        customer_phone="+919876543210",
        pickup_slot_start=timezone.now(),
        pickup_slot_end=timezone.now(),
        subtotal=Decimal("100.00"),
        tax_total=Decimal("0.00"),
        grand_total=Decimal("100.00"),
        idempotency_key="payment-test",
        request_fingerprint="f",
    )


def test_payment_amount_is_authoritative_order_total(order):
    payment = Payment.objects.create(order=order, user=order.user, amount_due=order.grand_total)
    assert payment.amount_due == Decimal("100.00")
    assert payment.status == Payment.AWAITING
