import hashlib
import json

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.catalog.models import Product
from apps.catalog.services import validate_variant_for_product
from apps.customization.models import CustomizationChoice, CustomizationOption
from apps.customization.services.validation import validate_selections

from ..models import Cart, CartItem, CartItemCustomization
from .pricing import cart_pricing, item_pricing


def guest_session(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


@transaction.atomic
def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.select_for_update().get_or_create(
            user=request.user, status=Cart.ACTIVE, defaults={"currency": "INR"}
        )
        return cart
    key = guest_session(request)
    cart, _ = Cart.objects.get_or_create(
        session_key=key, status=Cart.ACTIVE, defaults={"currency": "INR"}
    )
    return cart


def normalize_selections(selections):
    return sorted(
        [
            {
                "option_id": row["option_id"],
                "choice_ids": sorted(row.get("choice_ids", [])),
                "text_value": row.get("text_value", "").strip(),
            }
            for row in selections
        ],
        key=lambda row: row["option_id"],
    )


def selection_key(selections):
    return hashlib.sha256(
        json.dumps(normalize_selections(selections), sort_keys=True).encode()
    ).hexdigest()


def item_selection_key(item):
    rows = []
    for selection in item.customizations.all():
        rows.append(
            {
                "option_id": selection.option_id,
                "choice_ids": [selection.choice_id] if selection.choice_id else [],
                "text_value": selection.text_value,
            }
        )
    return selection_key(rows)


def _eligible_product(product_id, variant_id):
    product = Product.objects.filter(
        id=product_id, status=Product.PUBLISHED, is_available=True, category__is_active=True
    ).first()
    if not product:
        raise ValidationError({"product_id": "Product is not available."})
    variant = None
    if variant_id is not None:
        variant = validate_variant_for_product(product, variant_id)
        if not variant:
            raise ValidationError({"variant_id": "Variant is not available for this product."})
    return product, variant


@transaction.atomic
def add_item(cart, product_id, variant_id=None, quantity=1, selections=None):
    selections = selections or []
    if quantity < 1 or quantity > CartItem.MAX_QUANTITY:
        raise ValidationError({"quantity": "Quantity must be between 1 and 20."})
    product, variant = _eligible_product(product_id, variant_id)
    validated = validate_selections(product, selections)
    item = CartItem.objects.create(cart=cart, product=product, variant=variant, quantity=quantity)
    for row in validated["selections"]:
        option = CustomizationOption.objects.get(pk=row["option_id"])
        choice = (
            CustomizationChoice.objects.filter(pk=row.get("choice_id")).first()
            if row.get("choice_id")
            else None
        )
        CartItemCustomization.objects.create(
            cart_item=item,
            option=option,
            choice=choice,
            text_value=row.get("text_value", ""),
            price_adjustment=row["price_adjustment"],
        )
    pricing = item_pricing(item)
    item.acknowledged_unit_price = pricing["unit"]
    item.save(update_fields=("acknowledged_unit_price", "updated_at"))
    existing = None
    for candidate in cart.items.exclude(pk=item.pk).prefetch_related("customizations"):
        if (
            candidate.product_id == product.id
            and candidate.variant_id == (variant.id if variant else None)
            and item_selection_key(candidate) == item_selection_key(item)
        ):
            existing = candidate
            break
    if existing:
        if existing.quantity + quantity > CartItem.MAX_QUANTITY:
            raise ValidationError({"quantity": "Quantity limit exceeded."})
        existing.quantity += quantity
        existing.acknowledged_unit_price = pricing["unit"]
        existing.save(update_fields=("quantity", "acknowledged_unit_price", "updated_at"))
        item.delete()
        return existing, False
    return item, True


@transaction.atomic
def replace_customizations(item, selections):
    validated = validate_selections(item.product, selections)
    item.customizations.all().delete()
    for row in validated["selections"]:
        option = CustomizationOption.objects.get(pk=row["option_id"])
        choice = (
            CustomizationChoice.objects.filter(pk=row.get("choice_id")).first()
            if row.get("choice_id")
            else None
        )
        CartItemCustomization.objects.create(
            cart_item=item,
            option=option,
            choice=choice,
            text_value=row.get("text_value", ""),
            price_adjustment=row["price_adjustment"],
        )
    item.acknowledged_unit_price = item_pricing(item)["unit"]
    item.save(update_fields=("acknowledged_unit_price", "updated_at"))
    return item


def validate_cart(cart):
    issues, changes, valid_lines = [], [], []
    try:
        lines, subtotal = cart_pricing(cart)
    except ValueError as exc:
        return {
            "valid": False,
            "price_confirmation_required": False,
            "currency": "INR",
            "subtotal": "0.00",
            "changes": [],
            "issues": [str(exc)],
        }
    for item, pricing in lines:
        selections = {}
        for row in item.customizations.all():
            entry = selections.setdefault(row.option_id, {"option_id": row.option_id})
            if row.choice_id:
                entry.setdefault("choice_ids", []).append(row.choice_id)
            else:
                entry["text_value"] = row.text_value
        try:
            validate_selections(item.product, list(selections.values()))
        except ValidationError as exc:
            issues.append(
                {"item_id": str(item.id), "reason": "customization_invalid", "detail": exc.detail}
            )
        if (
            item.product.status != Product.PUBLISHED
            or not item.product.is_available
            or not item.product.category.is_active
        ):
            issues.append({"item_id": str(item.id), "reason": "product_unavailable"})
        if item.variant_id and (
            not item.variant.is_active or item.variant.product_id != item.product_id
        ):
            issues.append({"item_id": str(item.id), "reason": "variant_unavailable"})
        if (
            item.acknowledged_unit_price is not None
            and pricing["unit"] > item.acknowledged_unit_price
        ):
            changes.append(
                {
                    "item_id": str(item.id),
                    "previous_unit_price": str(item.acknowledged_unit_price),
                    "current_unit_price": str(pricing["unit"]),
                    "reason": "price_changed",
                    "requires_confirmation": True,
                }
            )
        valid_lines.append(item)
    return {
        "valid": not issues,
        "price_confirmation_required": bool(changes),
        "currency": "INR",
        "subtotal": str(subtotal),
        "changes": changes,
        "issues": issues,
    }


@transaction.atomic
def confirm_prices(cart):
    result = validate_cart(cart)
    if not result["valid"]:
        raise ValidationError({"cart": result["issues"]})
    for item in cart.items.all():
        item.acknowledged_unit_price = item_pricing(item)["unit"]
        item.save(update_fields=("acknowledged_unit_price", "updated_at"))
    return validate_cart(cart)


@transaction.atomic
def merge_guest_cart(request):
    if not request.user.is_authenticated:
        raise ValidationError({"detail": "Authentication is required."})
    key = request.session.session_key
    guest = Cart.objects.select_for_update().filter(session_key=key, status=Cart.ACTIVE).first()
    target = get_or_create_cart(request)
    if not guest or guest.pk == target.pk:
        return target, []
    issues = []
    for item in list(guest.items.prefetch_related("customizations")):
        selections = [
            {
                "option_id": row.option_id,
                "choice_ids": [row.choice_id] if row.choice_id else [],
                "text_value": row.text_value,
            }
            for row in item.customizations.all()
        ]
        try:
            merged, _ = add_item(
                target, item.product_id, item.variant_id, item.quantity, selections
            )
            item.delete()
        except ValidationError as exc:
            issues.append({"item_id": str(item.id), "detail": exc.detail})
    if not issues:
        guest.status = Cart.CONVERTED
        guest.session_key = None
        guest.save(update_fields=("status", "session_key", "updated_at"))
    return target, issues
