from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination

from .models import Order
from .serializers import (
    CheckoutSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    StaffOrderSerializer,
    TransitionSerializer,
)
from .services.checkout import create_order
from .services.transitions import transition_order


class CustomerOrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CheckoutSerializer, responses=OrderDetailSerializer)
    def post(self, request):
        key = request.headers.get("Idempotency-Key", "").strip()
        if not key or len(key) > 128:
            return Response(
                {"idempotency_key": ["A valid Idempotency-Key header is required."]}, status=400
            )
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order, created = create_order(request.user, serializer.validated_data, key)
        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(responses=OrderListSerializer(many=True))
    def get(self, request):
        queryset = Order.objects.filter(user=request.user).prefetch_related("items")
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"])
        if request.query_params.get("ordering") not in (None, "created_at", "-created_at"):
            return Response({"ordering": ["Unsupported ordering field."]}, status=400)
        if request.query_params.get("ordering") == "created_at":
            queryset = queryset.order_by("created_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(OrderListSerializer(page, many=True).data)


class CustomerOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OrderDetailSerializer)
    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.filter(user=request.user).prefetch_related("items__customizations"),
            pk=order_id,
        )
        return Response(OrderDetailSerializer(order).data)


class StaffOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=StaffOrderSerializer(many=True))
    def get(self, request):
        if not request.user.is_staff:
            return Response({"detail": "Staff permissions are required."}, status=403)
        queryset = Order.objects.all().prefetch_related("items", "status_history")
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"])
        if request.query_params.get("order_number"):
            queryset = queryset.filter(order_number=request.query_params["order_number"])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(OrderListSerializer(page, many=True).data)


class StaffOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_order(self, request, order_id):
        if not request.user.is_staff:
            return None
        return get_object_or_404(
            Order.objects.prefetch_related("items__customizations", "status_history"), pk=order_id
        )

    @extend_schema(responses=StaffOrderSerializer)
    def get(self, request, order_id):
        order = self.get_order(request, order_id)
        if order is None:
            return Response({"detail": "Staff permissions are required."}, status=403)
        return Response(StaffOrderSerializer(order).data)


class StaffOrderTransitionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=TransitionSerializer, responses=StaffOrderSerializer)
    def post(self, request, order_id):
        if not request.user.is_staff:
            return Response({"detail": "Staff permissions are required."}, status=403)
        order = get_object_or_404(Order, pk=order_id)
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = transition_order(order, actor=request.user, **serializer.validated_data)
        return Response(StaffOrderSerializer(order).data)
