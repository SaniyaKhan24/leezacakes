from django.contrib import admin

from .models import Order, OrderItem, OrderItemCustomization, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name_snapshot", "variant_name_snapshot", "unit_price", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "user",
        "status",
        "payment_status",
        "grand_total",
        "pickup_slot_start",
    )
    list_filter = ("status", "payment_status")
    search_fields = ("order_number", "customer_phone")
    inlines = (OrderItemInline,)
    readonly_fields = ("order_number", "idempotency_key", "request_fingerprint")


@admin.register(OrderItemCustomization)
class OrderItemCustomizationAdmin(admin.ModelAdmin):
    list_display = (
        "order_item",
        "option_name_snapshot",
        "choice_name_snapshot",
        "price_adjustment",
    )


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "from_status", "to_status", "changed_by", "created_at")
    readonly_fields = tuple(field.name for field in OrderStatusHistory._meta.fields)
