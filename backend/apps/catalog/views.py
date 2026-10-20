from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination

from .models import Category, Product, ProductImage, ProductVariant
from .permissions import IsCatalogueStaff
from .selectors import public_categories, public_products, public_variants
from .serializers import (
    CategoryPublicSerializer,
    CategorySerializer,
    ProductAdminSerializer,
    ProductImageAdminSerializer,
    ProductPublicSerializer,
    ProductVariantAdminSerializer,
    ProductVariantSerializer,
)
from .services import archive_product, publish_product, save_product_image, set_primary_image


def _bool(value):
    if value is None:
        return None
    if value.lower() in {"true", "1"}:
        return True
    if value.lower() in {"false", "0"}:
        return False
    return "invalid"


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=CategoryPublicSerializer(many=True))
    def get(self, request):
        queryset = public_categories()
        if request.query_params.get("parent"):
            queryset = queryset.filter(parent_id=request.query_params["parent"])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return (
            paginator.get_paginated_response(CategoryPublicSerializer(page, many=True).data)
            if page is not None
            else Response(CategoryPublicSerializer(queryset, many=True).data)
        )


class CategoryDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=CategoryPublicSerializer)
    def get(self, request, slug):
        category = get_object_or_404(public_categories(), slug=slug)
        return Response(CategoryPublicSerializer(category).data)


class ProductListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=ProductPublicSerializer(many=True))
    def get(self, request):
        queryset = public_products()
        params = request.query_params
        if params.get("category"):
            queryset = queryset.filter(category__slug=params["category"])
        if params.get("search"):
            term = params["search"].strip()
            queryset = queryset.filter(Q(name__icontains=term) | Q(description__icontains=term))
        featured = _bool(params.get("featured"))
        if featured == "invalid":
            return Response({"featured": ["Use true or false."]}, status=400)
        if featured is not None:
            queryset = queryset.filter(is_featured=featured)
        try:
            if params.get("min_price"):
                queryset = queryset.filter(
                    Q(base_price__gte=Decimal(params["min_price"]))
                    | Q(variants__price__gte=Decimal(params["min_price"]))
                )
            if params.get("max_price"):
                queryset = queryset.filter(
                    Q(base_price__lte=Decimal(params["max_price"]))
                    | Q(variants__price__lte=Decimal(params["max_price"]))
                )
        except (InvalidOperation, ValueError):
            return Response({"price": ["Use a valid decimal amount."]}, status=400)
        ordering = params.get("ordering", "-created_at")
        if ordering not in {"name", "-name", "created_at", "-created_at", "price", "-price"}:
            return Response({"ordering": ["Unsupported ordering field."]}, status=400)
        if ordering == "price":
            queryset = queryset.order_by("base_price", "id")
        elif ordering == "-price":
            queryset = queryset.order_by("-base_price", "id")
        else:
            queryset = queryset.order_by(ordering, "id")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset.distinct(), request, view=self)
        return (
            paginator.get_paginated_response(ProductPublicSerializer(page, many=True).data)
            if page is not None
            else Response(ProductPublicSerializer(queryset.distinct(), many=True).data)
        )


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=ProductPublicSerializer)
    def get(self, request, slug):
        return Response(
            ProductPublicSerializer(get_object_or_404(public_products(), slug=slug)).data
        )


class ProductVariantListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=ProductVariantSerializer(many=True))
    def get(self, request, slug):
        product = get_object_or_404(public_products(), slug=slug)
        return Response(ProductVariantSerializer(public_variants(product), many=True).data)


class StaffAPIView(APIView):
    permission_classes = [IsCatalogueStaff]


class AdminCategoryListCreateView(StaffAPIView):
    @extend_schema(responses=CategorySerializer(many=True))
    def get(self, request):
        paginator = StandardPagination()
        page = paginator.paginate_queryset(Category.objects.all(), request, view=self)
        return (
            paginator.get_paginated_response(CategorySerializer(page, many=True).data)
            if page is not None
            else Response(CategorySerializer(Category.objects.all(), many=True).data)
        )

    @extend_schema(request=CategorySerializer, responses=CategorySerializer)
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(CategorySerializer(serializer.save()).data, status=status.HTTP_201_CREATED)


class AdminCategoryDetailView(StaffAPIView):
    def get_object(self, category_id):
        return get_object_or_404(Category, pk=category_id)

    @extend_schema(request=None, responses=CategorySerializer)
    def get(self, request, category_id):
        return Response(CategorySerializer(self.get_object(category_id)).data)

    @extend_schema(request=CategorySerializer, responses=CategorySerializer)
    def patch(self, request, category_id):
        obj = self.get_object(category_id)
        serializer = CategorySerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(CategorySerializer(serializer.save()).data)


class AdminCategoryDeactivateView(StaffAPIView):
    @extend_schema(request=None, responses=CategorySerializer)
    def post(self, request, category_id):
        category = get_object_or_404(Category, pk=category_id)
        category.is_active = False
        category.save(update_fields=("is_active", "updated_at"))
        return Response(CategorySerializer(category).data)


class AdminProductListCreateView(StaffAPIView):
    @extend_schema(responses=ProductAdminSerializer(many=True))
    def get(self, request):
        queryset = Product.objects.select_related("category").all()
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"])
        if request.query_params.get("category"):
            queryset = queryset.filter(category__slug=request.query_params["category"])
        if request.query_params.get("search"):
            queryset = queryset.filter(name__icontains=request.query_params["search"])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return (
            paginator.get_paginated_response(ProductAdminSerializer(page, many=True).data)
            if page is not None
            else Response(ProductAdminSerializer(queryset, many=True).data)
        )

    @extend_schema(request=ProductAdminSerializer, responses=ProductAdminSerializer)
    def post(self, request):
        serializer = ProductAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            ProductAdminSerializer(serializer.save()).data, status=status.HTTP_201_CREATED
        )


class AdminProductDetailView(StaffAPIView):
    def get_object(self, product_id):
        return get_object_or_404(Product, pk=product_id)

    @extend_schema(request=None, responses=ProductAdminSerializer)
    def get(self, request, product_id):
        return Response(ProductAdminSerializer(self.get_object(product_id)).data)

    @extend_schema(request=ProductAdminSerializer, responses=ProductAdminSerializer)
    def patch(self, request, product_id):
        obj = self.get_object(product_id)
        serializer = ProductAdminSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(ProductAdminSerializer(serializer.save()).data)


class AdminProductPublishView(StaffAPIView):
    @extend_schema(request=None, responses=ProductAdminSerializer)
    def post(self, request, product_id):
        try:
            product = publish_product(get_object_or_404(Product, pk=product_id))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ProductAdminSerializer(product).data)


class AdminProductArchiveView(StaffAPIView):
    @extend_schema(request=None, responses=ProductAdminSerializer)
    def post(self, request, product_id):
        return Response(
            ProductAdminSerializer(archive_product(get_object_or_404(Product, pk=product_id))).data
        )


class AdminImageCreateView(StaffAPIView):
    @extend_schema(request=ProductImageAdminSerializer, responses=ProductImageAdminSerializer)
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        serializer = ProductImageAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            ProductImageAdminSerializer(
                save_product_image(product, **serializer.validated_data)
            ).data,
            status=201,
        )


class AdminImageDetailView(StaffAPIView):
    def get_object(self, product_id, image_id):
        return get_object_or_404(ProductImage, pk=image_id, product_id=product_id)

    @extend_schema(request=ProductImageAdminSerializer, responses=ProductImageAdminSerializer)
    def patch(self, request, product_id, image_id):
        image = self.get_object(product_id, image_id)
        serializer = ProductImageAdminSerializer(image, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        image = serializer.save()
        if "is_primary" in serializer.validated_data:
            image = set_primary_image(image, image.is_primary)
        return Response(ProductImageAdminSerializer(image).data)

    @extend_schema(responses=None)
    def delete(self, request, product_id, image_id):
        self.get_object(product_id, image_id).delete()
        return Response(status=204)


class AdminVariantCreateView(StaffAPIView):
    @extend_schema(request=ProductVariantAdminSerializer, responses=ProductVariantAdminSerializer)
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        serializer = ProductVariantAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            ProductVariantAdminSerializer(serializer.save(product=product)).data, status=201
        )


class AdminVariantDetailView(StaffAPIView):
    def get_object(self, product_id, variant_id):
        return get_object_or_404(ProductVariant, pk=variant_id, product_id=product_id)

    @extend_schema(request=ProductVariantAdminSerializer, responses=ProductVariantAdminSerializer)
    def patch(self, request, product_id, variant_id):
        variant = self.get_object(product_id, variant_id)
        serializer = ProductVariantAdminSerializer(variant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(ProductVariantAdminSerializer(serializer.save()).data)


class AdminVariantDeactivateView(StaffAPIView):
    @extend_schema(request=None, responses=ProductVariantAdminSerializer)
    def post(self, request, product_id, variant_id):
        variant = self.get_object(product_id, variant_id)
        variant.is_active = False
        variant.save(update_fields=("is_active", "updated_at"))
        return Response(ProductVariantAdminSerializer(variant).data)

    def get_object(self, product_id, variant_id):
        return get_object_or_404(ProductVariant, pk=variant_id, product_id=product_id)
