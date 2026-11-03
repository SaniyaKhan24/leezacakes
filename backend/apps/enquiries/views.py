from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import EnquiryCreatedEnvelopeSerializer, EnquiryCreateSerializer
from .services import create_enquiry
from .throttles import EnquiryThrottle


class EnquiryCreateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [EnquiryThrottle]
    throttle_scope = "enquiry"

    @extend_schema(
        request=EnquiryCreateSerializer, responses={201: EnquiryCreatedEnvelopeSerializer}
    )
    def post(self, request):
        serializer = EnquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry = create_enquiry(**serializer.validated_data)
        return Response(
            {"data": {"id": str(enquiry.id), "reference": enquiry.reference}},
            status=status.HTTP_201_CREATED,
        )
