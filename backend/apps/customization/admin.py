from django.contrib import admin

from .models import (
    CustomizationChoice,
    CustomizationOption,
    ProductCustomization,
    ProductCustomizationChoice,
)


@admin.register(CustomizationOption)
class CustomizationOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "input_type", "is_active", "sort_order")
    list_filter = ("input_type", "is_active")
    search_fields = ("name", "slug")


@admin.register(CustomizationChoice)
class CustomizationChoiceAdmin(admin.ModelAdmin):
    list_display = ("name", "option", "is_active", "sort_order")
    list_filter = ("is_active", "option")


@admin.register(ProductCustomization)
class ProductCustomizationAdmin(admin.ModelAdmin):
    list_display = ("product", "option", "is_required", "is_active")
    list_filter = ("is_active", "is_required")


@admin.register(ProductCustomizationChoice)
class ProductCustomizationChoiceAdmin(admin.ModelAdmin):
    list_display = ("product_customization", "choice", "price_adjustment", "is_active")
    list_filter = ("is_active", "currency")
