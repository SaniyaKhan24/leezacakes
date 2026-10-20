import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.models import Product, ProductVariant
from apps.customization.models import CustomizationChoice, CustomizationOption


class Order(models.Model):
    PENDING_PAYMENT = "pending_payment_verification"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready_for_pickup"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (PENDING_PAYMENT, "Pending payment verification"),
        (CONFIRMED, "Confirmed"),
        (PREPARING, "Preparing"),
        (READY, "Ready for pickup"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    )
    PAYMENT_PENDING = "pending_verification"
    PAYMENT_VERIFIED = "verified"
    PAYMENT_STATUSES = ((PAYMENT_PENDING, "Pending verification"), (PAYMENT_VERIFIED, "Verified"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=PENDING_PAYMENT)
    payment_status = models.CharField(
        max_length=24, choices=PAYMENT_STATUSES, default=PAYMENT_PENDING
    )
    customer_name = models.CharField(max_length=160)
    customer_phone = models.CharField(max_length=32)
    customer_email = models.EmailField(blank=True, default="")
    pickup_slot_start = models.DateTimeField()
    pickup_slot_end = models.DateTimeField()
    currency = models.CharField(max_length=3, default="INR")
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    discount_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    customer_note = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "idempotency_key"), name="unique_order_idempotency_per_user"
            )
        ]
        indexes = [
            models.Index(fields=("user", "created_at")),
            models.Index(fields=("status", "pickup_slot_start")),
        ]
        ordering = ("-created_at", "id")

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)
    product_name_snapshot = models.CharField(max_length=180)
    variant_name_snapshot = models.CharField(max_length=120, blank=True)
    sku_snapshot = models.CharField(max_length=80, blank=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_base_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    unit_customization_total = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    line_total = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product_name_snapshot


class OrderItemCustomization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, related_name="customizations"
    )
    option = models.ForeignKey(
        CustomizationOption, null=True, blank=True, on_delete=models.SET_NULL
    )
    choice = models.ForeignKey(
        CustomizationChoice, null=True, blank=True, on_delete=models.SET_NULL
    )
    option_name_snapshot = models.CharField(max_length=120)
    choice_name_snapshot = models.CharField(max_length=120, blank=True)
    value_snapshot = models.CharField(max_length=80, blank=True)
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.option_name_snapshot


class OrderStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=32, blank=True, default="")
    to_status = models.CharField(max_length=32)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    reason = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")

    def __str__(self):
        return f"{self.order.order_number}: {self.to_status}"
