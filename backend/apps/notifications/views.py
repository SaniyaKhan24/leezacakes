import hmac
import json
import logging

from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination

from .models import WhatsAppSettings
from .serializers import (
    InboxNotificationSerializer,
    MarkReadSerializer,
    NotificationPreferenceSerializer,
    UnreadCountSerializer,
)
from .services import get_preferences, inbox_queryset, mark_read, unread_count
from .whatsapp_services import process_webhook, verify_signature

logger = logging.getLogger(__name__)

AUDIENCE_PARAMETER = OpenApiParameter(
    "audience",
    str,
    enum=["customer", "staff"],
    required=False,
    description="Only this audience's notifications (staff rows exist for staff users only).",
)
UNREAD_PARAMETER = OpenApiParameter(
    "unread", bool, required=False, description="true lists unread notifications only."
)


def _audience(request):
    return request.query_params.get("audience") or None


class InboxPagination(StandardPagination):
    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data["unread_count"] = unread_count(self.request.user)
        return response

    def get_paginated_response_schema(self, schema):
        schema = super().get_paginated_response_schema(schema)
        schema["properties"]["unread_count"] = {"type": "integer", "example": 2}
        schema["required"] = [*schema.get("required", []), "unread_count"]
        return schema


class InboxView(ListAPIView):
    """In-app notifications for the signed-in user, newest first."""

    permission_classes = [IsAuthenticated]
    serializer_class = InboxNotificationSerializer
    pagination_class = InboxPagination

    def get_queryset(self):
        queryset = inbox_queryset(self.request.user, _audience(self.request))
        if self.request.query_params.get("unread") in {"1", "true", "True"}:
            queryset = queryset.filter(read_at__isnull=True)
        return queryset.order_by("-created_at", "-id")

    @extend_schema(parameters=[AUDIENCE_PARAMETER, UNREAD_PARAMETER])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class InboxUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UnreadCountSerializer, parameters=[AUDIENCE_PARAMETER])
    def get(self, request):
        return Response({"unread_count": unread_count(request.user, _audience(request))})


class InboxMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=MarkReadSerializer, responses=UnreadCountSerializer)
    def post(self, request):
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        count = mark_read(
            request.user,
            ids=serializer.validated_data.get("ids"),
            mark_all=serializer.validated_data["all"],
        )
        return Response({"unread_count": count})


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=NotificationPreferenceSerializer)
    def get(self, request):
        return Response(NotificationPreferenceSerializer(get_preferences(request.user)).data)

    @extend_schema(
        request=NotificationPreferenceSerializer, responses=NotificationPreferenceSerializer
    )
    def patch(self, request):
        preference = get_preferences(request.user)
        serializer = NotificationPreferenceSerializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        if any(key.startswith("marketing_") and key.endswith("_enabled") for key in request.data):
            updated.marketing_consent_recorded_at = timezone.now()
            updated.marketing_consent_source = "account_settings"
            updated.save(
                update_fields=(
                    "marketing_consent_recorded_at",
                    "marketing_consent_source",
                    "updated_at",
                )
            )
        return Response(NotificationPreferenceSerializer(updated).data)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(APIView):
    """Meta WhatsApp Cloud API webhook: verification (GET) and events (POST).

    Unauthenticated by design; POST bodies must carry a valid X-Hub-Signature-256 made
    with the app secret saved in admin. Not throttled, so Meta's retries are never dropped.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(exclude=True)
    def get(self, request):
        config = WhatsAppSettings.load()
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token") or ""
        challenge = request.query_params.get("hub.challenge") or ""
        if mode == "subscribe" and hmac.compare_digest(token, config.webhook_verify_token):
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse("Verification failed.", status=403, content_type="text/plain")

    @extend_schema(exclude=True)
    def post(self, request):
        raw = request.body  # read before anything parses the stream
        config = WhatsAppSettings.load()
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(raw, signature, config.app_secret):
            logger.warning("Rejected a WhatsApp webhook with a missing or invalid signature.")
            return HttpResponse("Invalid signature.", status=403, content_type="text/plain")
        try:
            payload = json.loads(raw.decode() or "{}")
        except (UnicodeDecodeError, ValueError):
            logger.warning("Ignored a signed WhatsApp webhook that is not JSON.")
            return HttpResponse("ok", content_type="text/plain")
        process_webhook(payload)
        return HttpResponse("ok", content_type="text/plain")
