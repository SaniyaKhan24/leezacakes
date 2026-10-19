from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()


class HealthView(APIView):
    """Liveness only: no database, infrastructure details or authentication."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(
        responses=HealthSerializer, auth=[], description="Process liveness; not database readiness."
    )
    def get(self, request):
        return Response({"status": "ok"})
