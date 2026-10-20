from django.contrib import admin

from .models import Cart, CartItem, CartItemCustomization


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "status", "updated_at")
    list_filter = ("status",)
    inlines = (CartItemInline,)


@admin.register(CartItemCustomization)
class CartItemCustomizationAdmin(admin.ModelAdmin):
    list_display = ("cart_item", "option", "choice", "price_adjustment")
