from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.validators import normalize_phone, validate_phone

from .models import Order, OrderItem, OrderItemCustomization, OrderStatusHistory


class CheckoutSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=160)
    customer_phone = serializers.CharField(validators=[validate_phone])
    customer_email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    pickup_slot_start = serializers.DateTimeField()
    pickup_slot_end = serializers.DateTimeField()
    customer_note = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate_customer_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name cannot be blank.")
        return value.strip()

    def validate_customer_phone(self, value):
        return normalize_phone(value)


class OrderItemCustomizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemCustomization
        fields = (
            "option_name_snapshot",
            "choice_name_snapshot",
            "value_snapshot",
            "price_adjustment",
        )


class OrderItemSerializer(serializers.ModelSerializer):
    customizations = OrderItemCustomizationSerializer(many=True, read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name_snapshot",
            "variant_name_snapshot",
            "sku_snapshot",
            "quantity",
            "unit_base_price",
            "unit_customization_total",
            "unit_price",
            "line_total",
            "customizations",
        )


class OrderListSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "status",
            "payment_status",
            "currency",
            "grand_total",
            "item_count",
            "pickup_slot_start",
            "pickup_slot_end",
            "created_at",
        )

    @extend_schema_field(serializers.IntegerField())
    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()
    pickup = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "status",
            "payment_status",
            "payment",
            "customer",
            "pickup",
            "currency",
            "subtotal",
            "discount_total",
            "tax_total",
            "grand_total",
            "customer_note",
            "items",
            "created_at",
            "confirmed_at",
            "completed_at",
        )

    @extend_schema_field(serializers.DictField())
    def get_payment(self, obj):
        return {"status": obj.payment_status}

    @extend_schema_field(serializers.DictField())
    def get_customer(self, obj):
        return {"name": obj.customer_name, "phone": obj.customer_phone, "email": obj.customer_email}

    @extend_schema_field(serializers.DictField())
    def get_pickup(self, obj):
        return {"slot_start": obj.pickup_slot_start, "slot_end": obj.pickup_slot_end}


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ("from_status", "to_status", "reason", "created_at")


class StaffOrderSerializer(OrderDetailSerializer):
    status_history = StatusHistorySerializer(many=True, read_only=True)

    class Meta(OrderDetailSerializer.Meta):
        fields = OrderDetailSerializer.Meta.fields + ("status_history", "idempotency_key")


class TransitionSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
