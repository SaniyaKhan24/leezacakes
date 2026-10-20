from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "image", "parent", "is_active", "sort_order")


class CategoryPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "image", "parent")


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "url", "image", "alt_text", "sort_order", "is_primary", "created_at")
        read_only_fields = ("id", "url", "created_at")

    def get_url(self, obj) -> str | None:
        return obj.image.url if obj.image else None


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ("id", "name", "sku", "price", "currency", "is_active", "sort_order")


class ProductPublicSerializer(serializers.ModelSerializer):
    category = CategoryPublicSerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "short_description",
            "category",
            "base_price",
            "currency",
            "effective_price",
            "weight_description",
            "preparation_time",
            "is_featured",
            "primary_image",
            "images",
            "variants",
        )

    def get_primary_image(self, obj) -> dict | None:
        image = next((item for item in obj.images.all() if item.is_primary), None)
        return ProductImageSerializer(image).data if image else None


class ProductAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "short_description",
            "category",
            "status",
            "is_available",
            "is_featured",
            "base_price",
            "currency",
            "weight_description",
            "preparation_time",
            "published_at",
        )
        read_only_fields = ("id", "published_at")

    def validate_currency(self, value):
        if value.upper() != Product.CURRENCY:
            raise serializers.ValidationError("Only INR is supported.")
        return value.upper()


class ProductImageAdminSerializer(ProductImageSerializer):
    class Meta(ProductImageSerializer.Meta):
        read_only_fields = ("id", "url", "created_at")


class ProductVariantAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ("id", "name", "sku", "price", "currency", "is_active", "sort_order")
        read_only_fields = ("id",)

    def validate_currency(self, value):
        if value.upper() != Product.CURRENCY:
            raise serializers.ValidationError("Only INR is supported.")
        return value.upper()
