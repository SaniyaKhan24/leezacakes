import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.catalog.models import Product, ProductVariant
from apps.customization.models import CustomizationChoice, CustomizationOption


class Cart(models.Model):
    ACTIVE = "active"
    CONVERTED = "converted"
    STATUS_CHOICES = ((ACTIVE, "Active"), (CONVERTED, "Converted"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="carts",
    )
    session_key = models.CharField(max_length=64, null=True, blank=True, unique=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=ACTIVE)
    currency = models.CharField(max_length=3, default="INR")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(status="active", user__isnull=False),
                name="one_active_cart_per_user",
            ),
        ]
        indexes = [models.Index(fields=("status", "updated_at"))]

    def __str__(self):
        return str(self.id)


class CartItem(models.Model):
    MAX_QUANTITY = 20
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="cart_items")
    variant = models.ForeignKey(
        ProductVariant, null=True, blank=True, on_delete=models.PROTECT, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(MAX_QUANTITY)]
    )
    acknowledged_unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=("cart", "product", "variant"))]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class CartItemCustomization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart_item = models.ForeignKey(CartItem, on_delete=models.CASCADE, related_name="customizations")
    option = models.ForeignKey(CustomizationOption, on_delete=models.PROTECT)
    choice = models.ForeignKey(CustomizationChoice, null=True, blank=True, on_delete=models.PROTECT)
    text_value = models.CharField(max_length=80, blank=True)
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("cart_item", "option", "choice", "text_value"), name="unique_cart_selection"
            )
        ]

    def __str__(self):
        return self.choice.name if self.choice_id else self.text_value
