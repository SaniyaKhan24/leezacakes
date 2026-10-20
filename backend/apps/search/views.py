from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SearchQuerySerializer, SearchResultSerializer
from .services import facets, search_products


def parse_query_params(request):
    data = request.query_params.copy()
    for key in ("available", "include_facets"):
        if key in data:
            if data[key].lower() not in {"true", "false"}:
                raise ValidationError({key: f"{key} must be true or false."})
            data[key] = data[key].lower() == "true"
    serializer = SearchQuerySerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class SearchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=dict)
    def get(self, request):
        filters = parse_query_params(request)
        queryset, normalized = search_products(filters)
        page, page_size = filters["page"], filters["page_size"]
        total = queryset.count()
        results = queryset[(page - 1) * page_size : page * page_size]
        applied = {
            key: value
            for key, value in filters.items()
            if key not in {"q", "page", "page_size", "sort", "include_facets"}
        }
        return Response(
            {
                "query": request.query_params.get("q"),
                "normalized_query": normalized,
                "count": total,
                "page": page,
                "page_size": page_size,
                "sort": filters["sort"],
                "applied_filters": applied,
                "fallback_used": False,
                "results": SearchResultSerializer(results, many=True).data,
                "facets": facets(queryset) if filters["include_facets"] else {},
                "suggestions": [],
            }
        )
