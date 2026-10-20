from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class CustomizationOption(models.Model):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    INPUT_TYPES = (
        (SINGLE_CHOICE, "Single choice"),
        (MULTIPLE_CHOICE, "Multiple choice"),
        (TEXT, "Free text"),
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    input_type = models.CharField(max_length=20, choices=INPUT_TYPES)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "name", "id")

    def __str__(self):
        return self.name


class CustomizationChoice(models.Model):
    option = models.ForeignKey(
        CustomizationOption, on_delete=models.PROTECT, related_name="choices"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "name", "id")
        constraints = [
            models.UniqueConstraint(fields=("option", "slug"), name="unique_choice_slug_per_option")
        ]

    def __str__(self):
        return f"{self.option.name}: {self.name}"


class ProductCustomization(models.Model):
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.PROTECT, related_name="customizations"
    )
    option = models.ForeignKey(
        CustomizationOption, on_delete=models.PROTECT, related_name="product_customizations"
    )
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    min_selections = models.PositiveIntegerField(null=True, blank=True)
    max_selections = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product", "option"), name="unique_product_customization"
            )
        ]

    def __str__(self):
        return f"{self.product.name}: {self.option.name}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.min_selections is not None
            and self.max_selections is not None
            and self.min_selections > self.max_selections
        ):
            raise ValidationError({"min_selections": "Minimum cannot exceed maximum."})
        if (
            self.option_id
            and self.option.input_type == CustomizationOption.TEXT
            and (self.min_selections or self.max_selections)
        ):
            raise ValidationError("Selection limits apply only to choice options.")


class ProductCustomizationChoice(models.Model):
    product_customization = models.ForeignKey(
        ProductCustomization, on_delete=models.PROTECT, related_name="choices"
    )
    choice = models.ForeignKey(
        CustomizationChoice, on_delete=models.PROTECT, related_name="product_configurations"
    )
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        default=Decimal("0.00"),
    )
    currency = models.CharField(max_length=3, default="INR")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product_customization", "choice"),
                name="unique_product_customization_choice",
            )
        ]

    def __str__(self):
        return self.choice.name

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.product_customization_id
            and self.choice_id
            and self.product_customization.option_id != self.choice.option_id
        ):
            raise ValidationError({"choice": "Choice must belong to the configured option."})
