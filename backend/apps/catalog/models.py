import uuid
from decimal import Decimal

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="catalog/categories/", blank=True, null=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "name", "id")
        indexes = [models.Index(fields=("is_active", "sort_order"))]

    def __str__(self):
        return self.name

    def clean(self):
        if self.parent_id and self.parent_id == self.pk:
            from django.core.exceptions import ValidationError

            raise ValidationError({"parent": "A category cannot be its own parent."})


class Product(models.Model):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    STATUS_CHOICES = ((DRAFT, "Draft"), (PUBLISHED, "Published"), (ARCHIVED, "Archived"))
    CURRENCY = "INR"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=320, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=DRAFT)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=3, default=CURRENCY)
    weight_description = models.CharField(max_length=80, blank=True)
    preparation_time = models.PositiveIntegerField(
        null=True, blank=True, help_text="Preparation time in minutes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "id")
        indexes = [
            models.Index(fields=("status", "is_available")),
            models.Index(fields=("category", "status")),
        ]

    def __str__(self):
        return self.name

    @property
    def effective_price(self):
        variant_price = (
            self.variants.filter(is_active=True)
            .order_by("price")
            .values_list("price", flat=True)
            .first()
        )
        return variant_price if variant_price is not None else self.base_price


def validate_image_size(value):
    if value.size > 5 * 1024 * 1024:
        from django.core.exceptions import ValidationError

        raise ValidationError("Images must be 5 MB or smaller.")


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="images")
    image = models.ImageField(
        upload_to="catalog/products/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validate_image_size],
    )
    alt_text = models.CharField(max_length=240)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product",),
                condition=models.Q(is_primary=True),
                name="one_primary_image_per_product",
            )
        ]

    def __str__(self):
        return self.alt_text


class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="variants")
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=80, unique=True, null=True, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    currency = models.CharField(max_length=3, default=Product.CURRENCY)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("sort_order", "price", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product", "name"), name="unique_variant_name_per_product"
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"
