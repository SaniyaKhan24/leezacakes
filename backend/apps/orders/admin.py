from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html_join
from rest_framework.exceptions import ValidationError

from .models import Order, OrderItem, OrderItemCustomization, OrderStatusHistory
from .services.transitions import transition_order


def _error_text(exc):
    detail = exc.detail
    if isinstance(detail, dict):
        parts = []
        for value in detail.values():
            parts.extend(value if isinstance(value, list) else [value])
        return " ".join(str(part) for part in parts)
    return str(detail)


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class OrderItemInline(ReadOnlyInline):
    model = OrderItem
    fields = (
        "product_name_snapshot",
        "variant_name_snapshot",
        "customization_summary",
        "quantity",
        "unit_price",
        "line_total",
    )
    readonly_fields = fields

    @admin.display(description="Customisations")
    def customization_summary(self, obj):
        rows = [
            (
                row.option_name_snapshot,
                row.choice_name_snapshot or row.value_snapshot or "-",
                f" (+₹{row.price_adjustment})" if row.price_adjustment else "",
            )
            for row in obj.customizations.all()
        ]
        if not rows:
            return "-"
        return format_html_join("", "<div><strong>{}</strong>: {}{}</div>", rows)


class OrderStatusHistoryInline(ReadOnlyInline):
    model = OrderStatusHistory
    fields = ("created_at", "from_status", "to_status", "changed_by", "reason")
    readonly_fields = fields


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer",
        "status",
        "payment_status",
        "payment_review",
        "pickup_slot",
        "grand_total",
        "created_at",
    )
    list_filter = ("status", "payment_status", "pickup_slot_start", "created_at")
    search_fields = (
        "order_number",
        "customer_name",
        "customer_phone",
        "customer_email",
        "user__email",
    )
    list_select_related = ("user", "payment")
    date_hierarchy = "pickup_slot_start"
    ordering = ("-created_at",)
    inlines = (OrderItemInline, OrderStatusHistoryInline)
    readonly_fields = (
        "order_number",
        "user",
        "status",
        "payment_status",
        "customer_name",
        "customer_phone",
        "customer_email",
        "pickup_slot_start",
        "pickup_slot_end",
        "currency",
        "subtotal",
        "discount_total",
        "tax_total",
        "grand_total",
        "customer_note",
        "idempotency_key",
        "request_fingerprint",
        "created_at",
        "updated_at",
        "confirmed_at",
        "completed_at",
        "cancelled_at",
    )
    fields = readonly_fields
    actions = ("start_preparing", "mark_ready", "mark_completed", "cancel_orders")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Customer", ordering="customer_name")
    def customer(self, obj):
        return f"{obj.customer_name} ({obj.customer_phone})"

    @admin.display(description="Payment review")
    def payment_review(self, obj):
        payment = getattr(obj, "payment", None)
        return payment.get_status_display() if payment else "-"

    @admin.display(description="Pickup", ordering="pickup_slot_start")
    def pickup_slot(self, obj):
        start = timezone.localtime(obj.pickup_slot_start)
        end = timezone.localtime(obj.pickup_slot_end)
        return f"{start:%a %d %b, %H:%M}–{end:%H:%M}"

    def _transition(self, request, queryset, to_status, label):
        moved = 0
        for order in queryset:
            try:
                transition_order(order, to_status, actor=request.user, reason="Updated in admin.")
            except ValidationError as exc:
                self.message_user(
                    request, f"{order.order_number}: {_error_text(exc)}", messages.ERROR
                )
                continue
            moved += 1
        if moved:
            self.message_user(request, f"{moved} order(s) {label}.", messages.SUCCESS)

    @admin.action(description="Start preparing", permissions=["change"])
    def start_preparing(self, request, queryset):
        self._transition(request, queryset, Order.PREPARING, "moved to preparing")

    @admin.action(description="Mark ready for pickup", permissions=["change"])
    def mark_ready(self, request, queryset):
        self._transition(request, queryset, Order.READY, "marked ready for pickup")

    @admin.action(description="Mark completed", permissions=["change"])
    def mark_completed(self, request, queryset):
        self._transition(request, queryset, Order.COMPLETED, "completed")

    @admin.action(description="Cancel", permissions=["change"])
    def cancel_orders(self, request, queryset):
        self._transition(request, queryset, Order.CANCELLED, "cancelled")


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
