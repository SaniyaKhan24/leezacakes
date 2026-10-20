from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Cart, CartItem, CartItemCustomization


class CartItemCustomizationSerializer(serializers.ModelSerializer):
    option_id = serializers.IntegerField(source="option.id", read_only=True)
    option_name = serializers.CharField(source="option.name", read_only=True)
    choice_id = serializers.IntegerField(source="choice.id", read_only=True, allow_null=True)
    choice_name = serializers.CharField(source="choice.name", read_only=True, allow_null=True)

    class Meta:
        model = CartItemCustomization
        fields = (
            "option_id",
            "option_name",
            "choice_id",
            "choice_name",
            "text_value",
            "price_adjustment",
        )


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()
    variant = serializers.SerializerMethodField()
    customizations = CartItemCustomizationSerializer(many=True, read_only=True)
    unit_price = serializers.SerializerMethodField()
    line_subtotal = serializers.SerializerMethodField()
    price_confirmation_required = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "product",
            "variant",
            "quantity",
            "customizations",
            "unit_price",
            "line_subtotal",
            "price_confirmation_required",
        )

    @extend_schema_field(serializers.DictField())
    def get_product(self, obj):
        return {"id": str(obj.product_id), "name": obj.product.name, "slug": obj.product.slug}

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_variant(self, obj):
        return {"id": str(obj.variant_id), "name": obj.variant.name} if obj.variant_id else None

    @extend_schema_field(serializers.CharField())
    def get_unit_price(self, obj):
        return str(self.context["pricing"][obj.id]["unit"])

    @extend_schema_field(serializers.CharField())
    def get_line_subtotal(self, obj):
        return str(self.context["pricing"][obj.id]["line"])

    @extend_schema_field(serializers.BooleanField())
    def get_price_confirmation_required(self, obj):
        price = self.context["pricing"][obj.id]["unit"]
        return obj.acknowledged_unit_price is not None and price > obj.acknowledged_unit_price


class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    price_confirmation_required = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "status", "currency", "items", "subtotal", "price_confirmation_required")

    def _pricing(self, obj):
        return {item.id: pricing for item, pricing in self.context["lines"]}

    @extend_schema_field(CartItemSerializer(many=True))
    def get_items(self, obj):
        pricing = self._pricing(obj)
        return CartItemSerializer(obj.items.all(), many=True, context={"pricing": pricing}).data

    @extend_schema_field(serializers.CharField())
    def get_subtotal(self, obj):
        return str(self.context["subtotal"])

    @extend_schema_field(serializers.BooleanField())
    def get_price_confirmation_required(self, obj):
        return any(
            item.acknowledged_unit_price is not None
            and price["unit"] > item.acknowledged_unit_price
            for item, price in self.context["lines"]
        )


class CartItemWriteSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, max_value=CartItem.MAX_QUANTITY)
    selections = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class QuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=CartItem.MAX_QUANTITY)


class SelectionsSerializer(serializers.Serializer):
    selections = serializers.ListField(child=serializers.DictField())
