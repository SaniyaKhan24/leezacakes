from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product
from apps.catalog.selectors import public_product
from apps.common.pagination import StandardPagination

from .models import (
    CustomizationChoice,
    CustomizationOption,
    ProductCustomization,
    ProductCustomizationChoice,
)
from .permissions import IsCustomizationStaff
from .serializers import (
    ChoiceAdminSerializer,
    OptionAdminSerializer,
    OptionSerializer,
    ProductChoiceAdminSerializer,
    ProductChoiceSerializer,
    ProductCustomizationAdminSerializer,
    ProductCustomizationSerializer,
    ValidationRequestSerializer,
)
from .services.validation import validate_selections


def _public_product(slug):
    product = public_product(slug)
    if product is None:
        raise Http404
    return product


class ProductOptionsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=ProductCustomizationSerializer(many=True))
    def get(self, request, product_slug):
        product = _public_product(product_slug)
        configurations = (
            ProductCustomization.objects.filter(
                product=product, is_active=True, option__is_active=True
            )
            .select_related("option")
            .prefetch_related("choices__choice")
        )
        return Response(
            {
                "product": {"slug": product.slug, "name": product.name},
                "options": ProductCustomizationSerializer(configurations, many=True).data,
            }
        )


class ProductChoicesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=ProductChoiceSerializer(many=True))
    def get(self, request, product_slug, option_id):
        product = _public_product(product_slug)
        config = get_object_or_404(
            ProductCustomization,
            product=product,
            option_id=option_id,
            is_active=True,
            option__is_active=True,
        )
        choices = config.choices.filter(is_active=True, choice__is_active=True).select_related(
            "choice"
        )
        return Response(ProductChoiceSerializer(choices, many=True).data)


class ValidateSelectionsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=ValidationRequestSerializer, responses=dict)
    def post(self, request, product_slug):
        product = _public_product(product_slug)
        serializer = ValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(validate_selections(product, serializer.validated_data["selections"]))


class StaffView(APIView):
    permission_classes = [IsCustomizationStaff]


class AdminOptionListCreateView(StaffView):
    @extend_schema(responses=OptionAdminSerializer(many=True))
    def get(self, request):
        queryset = CustomizationOption.objects.all()
        if request.query_params.get("is_active") in {"true", "false"}:
            queryset = queryset.filter(is_active=request.query_params["is_active"] == "true")
        if request.query_params.get("input_type"):
            queryset = queryset.filter(input_type=request.query_params["input_type"])
        if request.query_params.get("search"):
            queryset = queryset.filter(name__icontains=request.query_params["search"])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return (
            paginator.get_paginated_response(OptionAdminSerializer(page, many=True).data)
            if page is not None
            else Response(OptionAdminSerializer(queryset, many=True).data)
        )

    @extend_schema(request=OptionAdminSerializer, responses=OptionAdminSerializer)
    def post(self, request):
        serializer = OptionAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(OptionAdminSerializer(serializer.save()).data, status=201)


class AdminOptionDetailView(StaffView):
    def get_object(self, option_id):
        return get_object_or_404(CustomizationOption, pk=option_id)

    @extend_schema(responses=OptionSerializer)
    def get(self, request, option_id):
        return Response(OptionSerializer(self.get_object(option_id)).data)

    @extend_schema(request=OptionAdminSerializer, responses=OptionAdminSerializer)
    def patch(self, request, option_id):
        serializer = OptionAdminSerializer(
            self.get_object(option_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        return Response(OptionAdminSerializer(serializer.save()).data)


class AdminChoiceCreateView(StaffView):
    @extend_schema(request=ChoiceAdminSerializer, responses=ChoiceAdminSerializer)
    def post(self, request, option_id):
        option = get_object_or_404(CustomizationOption, pk=option_id)
        serializer = ChoiceAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(ChoiceAdminSerializer(serializer.save(option=option)).data, status=201)


class AdminChoiceDetailView(StaffView):
    def get_object(self, option_id, choice_id):
        return get_object_or_404(CustomizationChoice, pk=choice_id, option_id=option_id)

    @extend_schema(responses=ChoiceAdminSerializer)
    def get(self, request, option_id, choice_id):
        return Response(ChoiceAdminSerializer(self.get_object(option_id, choice_id)).data)

    @extend_schema(request=ChoiceAdminSerializer, responses=ChoiceAdminSerializer)
    def patch(self, request, option_id, choice_id):
        serializer = ChoiceAdminSerializer(
            self.get_object(option_id, choice_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        return Response(ChoiceAdminSerializer(serializer.save()).data)


class AdminProductCustomizationCreateView(StaffView):
    @extend_schema(
        request=ProductCustomizationAdminSerializer, responses=ProductCustomizationAdminSerializer
    )
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        serializer = ProductCustomizationAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            ProductCustomizationAdminSerializer(serializer.save(product=product)).data, status=201
        )


class AdminProductCustomizationDetailView(StaffView):
    def get_object(self, product_id, product_customization_id):
        return get_object_or_404(
            ProductCustomization, pk=product_customization_id, product_id=product_id
        )

    @extend_schema(responses=ProductCustomizationAdminSerializer)
    def get(self, request, product_id, product_customization_id):
        return Response(
            ProductCustomizationAdminSerializer(
                self.get_object(product_id, product_customization_id)
            ).data
        )

    @extend_schema(
        request=ProductCustomizationAdminSerializer, responses=ProductCustomizationAdminSerializer
    )
    def patch(self, request, product_id, product_customization_id):
        serializer = ProductCustomizationAdminSerializer(
            self.get_object(product_id, product_customization_id), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        return Response(ProductCustomizationAdminSerializer(serializer.save()).data)


class AdminProductChoiceCreateView(StaffView):
    @extend_schema(request=ProductChoiceAdminSerializer, responses=ProductChoiceAdminSerializer)
    def post(self, request, product_id, product_customization_id):
        config = get_object_or_404(
            ProductCustomization, pk=product_customization_id, product_id=product_id
        )
        serializer = ProductChoiceAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["choice"].option_id != config.option_id:
            return Response(
                {"choice": ["Choice must belong to the configured option."]}, status=400
            )
        return Response(
            ProductChoiceAdminSerializer(serializer.save(product_customization=config)).data,
            status=201,
        )


class AdminProductChoiceDetailView(StaffView):
    def get_object(self, product_id, product_customization_id, product_choice_id):
        return get_object_or_404(
            ProductCustomizationChoice,
            pk=product_choice_id,
            product_customization_id=product_customization_id,
            product_customization__product_id=product_id,
        )

    @extend_schema(responses=ProductChoiceAdminSerializer)
    def get(self, request, product_id, product_customization_id, product_choice_id):
        return Response(
            ProductChoiceAdminSerializer(
                self.get_object(product_id, product_customization_id, product_choice_id)
            ).data
        )

    @extend_schema(request=ProductChoiceAdminSerializer, responses=ProductChoiceAdminSerializer)
    def patch(self, request, product_id, product_customization_id, product_choice_id):
        serializer = ProductChoiceAdminSerializer(
            self.get_object(product_id, product_customization_id, product_choice_id),
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        return Response(ProductChoiceAdminSerializer(serializer.save()).data)
