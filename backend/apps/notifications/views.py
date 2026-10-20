from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import NotificationPreferenceSerializer
from .services import get_preferences


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
