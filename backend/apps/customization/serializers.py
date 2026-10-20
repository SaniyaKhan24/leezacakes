from rest_framework import serializers

from .models import (
    CustomizationChoice,
    CustomizationOption,
    ProductCustomization,
    ProductCustomizationChoice,
)


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomizationChoice
        fields = ("id", "option", "name", "slug", "description", "is_active", "sort_order")
        read_only_fields = ("id", "option")


class OptionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = CustomizationOption
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "input_type",
            "is_active",
            "sort_order",
            "choices",
        )
        read_only_fields = ("id", "choices")


class ProductChoiceSerializer(serializers.ModelSerializer):
    choice_name = serializers.CharField(source="choice.name", read_only=True)

    class Meta:
        model = ProductCustomizationChoice
        fields = (
            "id",
            "choice",
            "choice_name",
            "price_adjustment",
            "currency",
            "is_active",
            "sort_order",
        )
        read_only_fields = ("id", "currency", "choice_name")


class ProductCustomizationSerializer(serializers.ModelSerializer):
    option = OptionSerializer(read_only=True)
    choices = ProductChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = ProductCustomization
        fields = (
            "id",
            "product",
            "option",
            "is_required",
            "is_active",
            "sort_order",
            "min_selections",
            "max_selections",
            "choices",
        )


class OptionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomizationOption
        fields = ("id", "name", "slug", "description", "input_type", "is_active", "sort_order")
        read_only_fields = ("id",)


class ChoiceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomizationChoice
        fields = ("id", "option", "name", "slug", "description", "is_active", "sort_order")
        read_only_fields = ("id", "option")


class ProductCustomizationAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCustomization
        fields = (
            "id",
            "product",
            "option",
            "is_required",
            "is_active",
            "sort_order",
            "min_selections",
            "max_selections",
        )
        read_only_fields = ("id", "product")


class ProductChoiceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCustomizationChoice
        fields = (
            "id",
            "product_customization",
            "choice",
            "price_adjustment",
            "currency",
            "is_active",
            "sort_order",
        )
        read_only_fields = ("id", "product_customization", "currency")


class SelectionSerializer(serializers.Serializer):
    option_id = serializers.IntegerField()
    choice_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    text_value = serializers.CharField(required=False, allow_blank=True, max_length=80)


class ValidationRequestSerializer(serializers.Serializer):
    selections = SelectionSerializer(many=True)
