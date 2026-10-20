from decimal import Decimal

from apps.catalog.models import Product


def item_pricing(item):
    base = item.variant.price if item.variant_id else item.product.base_price
    if base is None:
        raise ValueError("Product has no configured price.")
    adjustment = sum(
        (selection.price_adjustment for selection in item.customizations.all()), Decimal("0.00")
    )
    unit = base + adjustment
    return {
        "base": base,
        "customization": adjustment,
        "unit": unit,
        "line": unit * item.quantity,
        "currency": Product.CURRENCY,
    }


def cart_pricing(cart):
    lines = []
    subtotal = Decimal("0.00")
    for item in cart.items.select_related("product", "variant").prefetch_related(
        "customizations__option", "customizations__choice"
    ):
        pricing = item_pricing(item)
        subtotal += pricing["line"]
        lines.append((item, pricing))
    return lines, subtotal
