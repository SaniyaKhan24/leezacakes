from rest_framework import serializers


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=200)
    category = serializers.CharField(required=False, max_length=140)
    product_type = serializers.CharField(required=False, max_length=40)
    occasion = serializers.CharField(required=False, max_length=80)
    color = serializers.CharField(required=False, max_length=80)
    flavour = serializers.CharField(required=False, max_length=80)
    min_price = serializers.DecimalField(
        required=False, min_value=0, max_digits=10, decimal_places=2
    )
    max_price = serializers.DecimalField(
        required=False, min_value=0, max_digits=10, decimal_places=2
    )
    available = serializers.BooleanField(required=False)
    sort = serializers.ChoiceField(
        required=False,
        choices=("relevance", "price_asc", "price_desc", "newest"),
        default="relevance",
    )
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=50, default=20)
    include_facets = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if (
            attrs.get("min_price") is not None
            and attrs.get("max_price") is not None
            and attrs["min_price"] > attrs["max_price"]
        ):
            raise serializers.ValidationError({"price": "min_price must not exceed max_price."})
        unsupported = ("product_type", "occasion", "color", "flavour")
        if any(key in attrs for key in unsupported):
            raise serializers.ValidationError(
                {
                    key: "This filter is unavailable in the current catalog schema."
                    for key in unsupported
                    if key in attrs
                }
            )
        return attrs


class SearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    category = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    available = serializers.BooleanField(source="is_available")
    match_type = serializers.CharField(default="direct")

    def get_category(self, obj):
        return {"slug": obj.category.slug, "name": obj.category.name}

    def get_primary_image(self, obj):
        image = next(iter(obj.images.all()), None)
        return image.image.url if image and image.image else None

    def get_price(self, obj):
        amount = getattr(obj, "eligible_price", None) or obj.base_price
        variants = obj._prefetched_objects_cache.get("variants", [])
        return {
            "amount": str(amount) if amount is not None else None,
            "currency": "INR",
            "display_type": "starting_from" if variants else "fixed",
        }
