from django.contrib.auth import get_user_model
from django.contrib.auth import logout as django_logout
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from .models import Address
from .serializers import (
    AddressSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationSerializer,
    UserSerializer,
    VerificationConfirmSerializer,
    VerificationRequestSerializer,
)
from .services import (
    change_password,
    confirm_email,
    confirm_password_reset,
    create_address,
    issue_verification_token,
    login_user,
    register_user,
    request_password_reset,
    set_default_address,
    update_address,
)
from .throttles import AccountThrottle

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AccountThrottle]
    throttle_scope = "register"

    @extend_schema(request=RegistrationSerializer, responses=UserSerializer)
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_user(**serializer.validated_data)
        return Response({"data": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AccountThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses=UserSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, refresh = login_user(**serializer.validated_data)
        return Response(
            {
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data,
                }
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={
            "application/json": {"type": "object", "properties": {"refresh": {"type": "string"}}}
        },
        responses=None,
    )
    def post(self, request):
        token = request.data.get("refresh")
        if token:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken

                RefreshToken(token).blacklist()
            except Exception:  # noqa: BLE001
                pass
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AccountThrottle]
    throttle_scope = "refresh"

    @extend_schema(request=TokenRefreshSerializer, responses=TokenRefreshSerializer)
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"data": serializer.validated_data})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response({"data": UserSerializer(request.user).data})

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"data": serializer.data})


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AccountThrottle]
    throttle_scope = "password_change"

    @extend_schema(request=PasswordChangeSerializer, responses=None)
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        change_password(
            request.user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
        )
        return Response({"detail": "Password changed successfully."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AccountThrottle]
    throttle_scope = "password_reset"

    @extend_schema(request=PasswordResetRequestSerializer, responses=None)
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data["email"])
        return Response(
            {"detail": "If an eligible account exists, password-reset instructions will be sent."}
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AccountThrottle]
    throttle_scope = "password_reset_confirm"

    @extend_schema(request=PasswordResetConfirmSerializer, responses=None)
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        confirm_password_reset(
            uid=serializer.validated_data["uid"],
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )
        return Response({"detail": "Password has been reset successfully."})


class VerificationRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AccountThrottle]
    throttle_scope = "verification_request"

    @extend_schema(request=VerificationRequestSerializer, responses=None)
    def post(self, request):
        serializer = VerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = (
            request.user.email
            if request.user.is_authenticated
            else serializer.validated_data.get("email", "")
        )
        user = User.objects.filter(email__iexact=email.strip().lower(), is_active=True).first()
        if user and not user.is_email_verified:
            issue_verification_token(user)
        return Response({"detail": "If verification is required, instructions will be sent."})


class VerificationConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AccountThrottle]
    throttle_scope = "verification_confirm"

    @extend_schema(request=VerificationConfirmSerializer, responses=None)
    def post(self, request):
        serializer = VerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = confirm_email(
            uid=serializer.validated_data["uid"],
            raw_token=serializer.validated_data["token"],
        )
        return Response({"data": {"is_email_verified": user.is_email_verified}})


class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=AddressSerializer(many=True))
    def get(self, request):
        return Response({"data": AddressSerializer(request.user.addresses.all(), many=True).data})

    @extend_schema(request=AddressSerializer, responses=AddressSerializer)
    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = create_address(request.user, **serializer.validated_data)
        return Response({"data": AddressSerializer(address).data}, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, address_id):
        return get_object_or_404(Address, pk=address_id, user=request.user)

    @extend_schema(request=None, responses=AddressSerializer)
    def get(self, request, address_id):
        return Response({"data": AddressSerializer(self.get_object(request, address_id)).data})

    @extend_schema(request=AddressSerializer, responses=AddressSerializer)
    def patch(self, request, address_id):
        address = self.get_object(request, address_id)
        serializer = AddressSerializer(address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        address = update_address(address, **serializer.validated_data)
        return Response({"data": AddressSerializer(address).data})

    @extend_schema(responses=None)
    def delete(self, request, address_id):
        self.get_object(request, address_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddressSetDefaultView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=AddressSerializer)
    def post(self, request, address_id):
        address = get_object_or_404(Address, pk=address_id, user=request.user)
        return Response({"data": AddressSerializer(set_default_address(address)).data})
