from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .health import database_ready
from .serializers import HealthSerializer


class HealthLiveView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(responses=HealthSerializer, auth=[], summary="Liveness probe")
    def get(self, request):
        return Response({"status": "ok"})


class HealthReadyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(
        responses={200: HealthSerializer, 503: OpenApiResponse(response=HealthSerializer)},
        auth=[],
        summary="Readiness probe",
    )
    def get(self, request):
        if database_ready():
            return Response({"status": "ok"})
        return Response({"status": "unavailable"}, status=503)
