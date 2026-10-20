from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.catalog.models import Product

from ..models import CustomizationOption, ProductCustomization


def validate_selections(product, selections):
    if (
        product.status != Product.PUBLISHED
        or not product.is_available
        or not product.category.is_active
    ):
        raise ValidationError({"product": "Product is not available for customization."})
    configurations = {
        config.option_id: config
        for config in ProductCustomization.objects.filter(
            product=product, is_active=True, option__is_active=True
        ).prefetch_related("choices__choice", "option")
    }
    if not isinstance(selections, list):
        raise ValidationError({"selections": "Expected a list."})
    seen_options = set()
    normalized = []
    total = Decimal("0.00")
    for selection in selections:
        if not isinstance(selection, dict) or "option_id" not in selection:
            raise ValidationError({"selections": "Each selection requires option_id."})
        option_id = selection["option_id"]
        if option_id in seen_options:
            raise ValidationError({"selections": "Duplicate options are not allowed."})
        seen_options.add(option_id)
        config = configurations.get(option_id)
        if not config:
            raise ValidationError({"selections": "Option is not available for this product."})
        option = config.option
        has_choices = "choice_ids" in selection
        has_text = "text_value" in selection
        if has_choices and has_text:
            raise ValidationError(
                {"selections": "A selection cannot contain both choices and text."}
            )
        if option.input_type == CustomizationOption.TEXT:
            value = selection.get("text_value", "")
            if not isinstance(value, str) or len(value) > 80:
                raise ValidationError({"selections": "Text values must be at most 80 characters."})
            if config.is_required and not value.strip():
                raise ValidationError({"selections": "A value is required for this option."})
            normalized.append(
                {
                    "option_id": option.id,
                    "option_name": option.name,
                    "text_value": value,
                    "price_adjustment": "0.00",
                    "currency": "INR",
                }
            )
            continue
        ids = selection.get("choice_ids")
        if not isinstance(ids, list) or len(ids) != len(set(ids)):
            raise ValidationError({"selections": "choice_ids must be a list without duplicates."})
        if option.input_type == CustomizationOption.SINGLE_CHOICE and len(ids) != 1:
            raise ValidationError({"selections": "Exactly one choice is required."})
        if config.is_required and not ids:
            raise ValidationError({"selections": "A choice is required for this option."})
        if config.min_selections is not None and len(ids) < config.min_selections:
            raise ValidationError({"selections": "Too few choices selected."})
        if config.max_selections is not None and len(ids) > config.max_selections:
            raise ValidationError({"selections": "Too many choices selected."})
        allowed = {
            item.choice_id: item
            for item in config.choices.all()
            if item.is_active and item.choice.is_active
        }
        for choice_id in ids:
            item = allowed.get(choice_id)
            if not item:
                raise ValidationError({"selections": "Choice is not available for this product."})
            total += item.price_adjustment
            normalized.append(
                {
                    "option_id": option.id,
                    "option_name": option.name,
                    "choice_id": item.choice_id,
                    "choice_name": item.choice.name,
                    "price_adjustment": str(item.price_adjustment),
                    "currency": item.currency,
                }
            )
    for config in configurations.values():
        if config.is_required and config.option_id not in seen_options:
            raise ValidationError(
                {"selections": f"Required option '{config.option.name}' is missing."}
            )
    return {
        "valid": True,
        "product": {"slug": product.slug},
        "selections": normalized,
        "customization_total": str(total),
        "currency": "INR",
    }
