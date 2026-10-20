from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CartItem
from .serializers import (
    CartItemWriteSerializer,
    CartSerializer,
    QuantitySerializer,
    SelectionsSerializer,
)
from .services.cart_service import (
    add_item,
    confirm_prices,
    get_or_create_cart,
    merge_guest_cart,
    replace_customizations,
    validate_cart,
)
from .services.pricing import cart_pricing


def cart_response(cart, request):
    lines, subtotal = cart_pricing(cart)
    return CartSerializer(
        cart, context={"request": request, "lines": lines, "subtotal": subtotal}
    ).data


class CartView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=CartSerializer)
    def get(self, request):
        return Response(cart_response(get_or_create_cart(request), request))


class CartItemListCreateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=CartItemWriteSerializer, responses=CartSerializer, operation_id="cart_items_create"
    )
    def post(self, request):
        serializer = CartItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = get_or_create_cart(request)
        item, created = add_item(cart, **serializer.validated_data)
        return Response(
            cart_response(cart, request),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(request=None, responses={204: None}, operation_id="cart_items_clear")
    def delete(self, request):
        cart = get_or_create_cart(request)
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemDetailView(APIView):
    permission_classes = [AllowAny]

    def get_item(self, request, item_id):
        cart = get_or_create_cart(request)
        return cart, get_object_or_404(CartItem, pk=item_id, cart=cart)

    @extend_schema(responses=CartSerializer, operation_id="cart_item_retrieve")
    def get(self, request, item_id):
        cart, item = self.get_item(request, item_id)
        return Response(cart_response(cart, request))

    @extend_schema(
        request=QuantitySerializer, responses=CartSerializer, operation_id="cart_item_update"
    )
    def patch(self, request, item_id):
        cart, item = self.get_item(request, item_id)
        serializer = QuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item.quantity = serializer.validated_data["quantity"]
        item.save(update_fields=("quantity", "updated_at"))
        return Response(cart_response(cart, request))

    @extend_schema(responses={204: None}, operation_id="cart_item_delete")
    def delete(self, request, item_id):
        _, item = self.get_item(request, item_id)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemCustomizationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=SelectionsSerializer, responses=CartSerializer)
    def put(self, request, item_id):
        cart = get_or_create_cart(request)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        serializer = SelectionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        replace_customizations(item, serializer.validated_data["selections"])
        return Response(cart_response(cart, request))


class CartValidateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses=dict)
    def post(self, request):
        return Response(validate_cart(get_or_create_cart(request)))


class CartConfirmPricesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses=CartSerializer)
    def post(self, request):
        cart = get_or_create_cart(request)
        confirm_prices(cart)
        return Response(cart_response(cart, request))


class CartMergeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=dict)
    def post(self, request):
        cart, issues = merge_guest_cart(request)
        result = {"merged": not issues, "cart": cart_response(cart, request), "issues": issues}
        return Response(result)


class CartCheckoutValidateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses=dict)
    def post(self, request):
        result = validate_cart(get_or_create_cart(request))
        result["ready_for_checkout"] = result["valid"] and not result["price_confirmation_required"]
        return Response(result)
