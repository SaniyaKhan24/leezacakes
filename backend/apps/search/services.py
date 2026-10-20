from django.db.models import Case, Count, F, Min, Q, Value, When

from apps.catalog.models import Product


def search_products(filters):
    query = " ".join(filters.get("q", "").split())
    queryset = (
        Product.objects.filter(status=Product.PUBLISHED, category__is_active=True)
        .annotate(
            eligible_price=Case(
                When(variants__is_active=True, then=Min("variants__price")), default=F("base_price")
            )
        )
        .select_related("category")
        .prefetch_related("images", "variants")
    )
    if filters.get("available") is True:
        queryset = queryset.filter(is_available=True)
    if filters.get("category"):
        queryset = queryset.filter(category__slug=filters["category"])
    if filters.get("min_price") is not None:
        queryset = queryset.filter(eligible_price__gte=filters["min_price"])
    if filters.get("max_price") is not None:
        queryset = queryset.filter(eligible_price__lte=filters["max_price"])
    if query:
        text_filter = Q(name__icontains=query) | Q(description__icontains=query)
        for term in query.split():
            text_filter |= Q(name__icontains=term) | Q(description__icontains=term)
        queryset = queryset.filter(text_filter).annotate(
            relevance=Case(
                When(name__iexact=query, then=Value(4)),
                When(name__icontains=query, then=Value(3)),
                When(description__icontains=query, then=Value(2)),
                default=Value(1),
            )
        )
    sort = filters.get("sort", "relevance")
    if sort == "price_asc":
        queryset = queryset.order_by("eligible_price", "id")
    elif sort == "price_desc":
        queryset = queryset.order_by("-eligible_price", "id")
    elif sort == "newest":
        queryset = queryset.order_by("-created_at", "id")
    elif query:
        queryset = queryset.order_by("-relevance", "-created_at", "id")
    else:
        queryset = queryset.order_by("-created_at", "id")
    return queryset, query


def facets(queryset):
    rows = (
        queryset.values("category__slug", "category__name")
        .annotate(count=Count("id"))
        .order_by("category__slug")
    )
    return {
        "categories": [
            {"value": row["category__slug"], "label": row["category__name"], "count": row["count"]}
            for row in rows
        ],
        "product_types": [],
        "colors": [],
        "occasions": [],
        "flavours": [],
    }
