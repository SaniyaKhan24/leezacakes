from django.contrib import admin

from .models import Category, Product, ProductImage, ProductVariant


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "status", "is_available", "is_featured", "effective_price")
    list_filter = ("status", "is_available", "is_featured", "category")
    search_fields = ("name", "slug")
    inlines = (ProductImageInline, ProductVariantInline)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "is_primary", "sort_order")
    list_filter = ("is_primary",)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "price", "currency", "is_active")
    list_filter = ("is_active", "currency")
