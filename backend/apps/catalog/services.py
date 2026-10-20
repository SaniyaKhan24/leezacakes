from django.db import transaction
from django.utils import timezone

from .models import Product, ProductImage, ProductVariant


@transaction.atomic
def publish_product(product):
    if (
        not product.category.is_active
        or not product.name.strip()
        or product.effective_price is None
    ):
        raise ValueError(
            "Product requires an active category and a valid price before publication."
        )
    product.status = Product.PUBLISHED
    product.published_at = product.published_at or timezone.now()
    product.save(update_fields=("status", "published_at", "updated_at"))
    return product


@transaction.atomic
def archive_product(product):
    product.status = Product.ARCHIVED
    product.save(update_fields=("status", "updated_at"))
    return product


@transaction.atomic
def save_product_image(product, **data):
    if data.get("is_primary"):
        ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)
    return ProductImage.objects.create(product=product, **data)


@transaction.atomic
def set_primary_image(image, is_primary=True):
    if is_primary:
        ProductImage.objects.filter(product=image.product, is_primary=True).exclude(
            pk=image.pk
        ).update(is_primary=False)
    image.is_primary = is_primary
    image.save(update_fields=("is_primary",))
    return image


def validate_variant_for_product(product, variant_id):
    return ProductVariant.objects.filter(
        id=variant_id,
        product=product,
        is_active=True,
        product__status=Product.PUBLISHED,
        product__is_available=True,
    ).first()
