from .models import Category, Product, ProductVariant


def public_categories():
    return Category.objects.filter(is_active=True).select_related("parent")


def public_products():
    return (
        Product.objects.filter(
            status=Product.PUBLISHED, is_available=True, category__is_active=True
        )
        .select_related("category")
        .prefetch_related("images", "variants")
    )


def public_product(slug):
    return public_products().filter(slug=slug).first()


def public_variants(product):
    return ProductVariant.objects.filter(product=product, is_active=True)
