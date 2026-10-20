from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination

from .models import Payment, PaymentSubmission
from .permissions import PaymentVerifierPermission
from .serializers import (
    EvidenceUploadSerializer,
    PaymentSerializer,
    ReviewSerializer,
    SubmissionSerializer,
    VerifySerializer,
)
from .services import review_submission, submit_evidence, verify_payment


def customer_payment(request, payment_id):
    return get_object_or_404(
        Payment.objects.prefetch_related("submissions"), pk=payment_id, user=request.user
    )


class CustomerPaymentByOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PaymentSerializer)
    def get(self, request, order_id):
        payment = get_object_or_404(Payment, order_id=order_id, user=request.user)
        return Response(PaymentSerializer(payment).data)


class CustomerPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PaymentSerializer)
    def get(self, request, payment_id):
        return Response(PaymentSerializer(customer_payment(request, payment_id)).data)


class CustomerSubmissionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=SubmissionSerializer(many=True))
    def get(self, request, payment_id):
        payment = customer_payment(request, payment_id)
        return Response(SubmissionSerializer(payment.submissions.all(), many=True).data)

    @extend_schema(request=EvidenceUploadSerializer, responses=SubmissionSerializer)
    def post(self, request, payment_id):
        payment = customer_payment(request, payment_id)
        serializer = EvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = submit_evidence(payment, request.user, serializer.validated_data["evidence"])
        return Response(SubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)


class CustomerSubmissionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=SubmissionSerializer)
    def get(self, request, payment_id, submission_id):
        payment = customer_payment(request, payment_id)
        submission = get_object_or_404(PaymentSubmission, payment=payment, pk=submission_id)
        return Response(SubmissionSerializer(submission).data)


class StaffPaymentListView(APIView):
    permission_classes = [PaymentVerifierPermission]

    @extend_schema(responses=PaymentSerializer(many=True))
    def get(self, request):
        queryset = Payment.objects.select_related("order", "user").prefetch_related("submissions")
        if request.query_params.get("status"):
            queryset = queryset.filter(status=request.query_params["status"])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(PaymentSerializer(page, many=True).data)


class StaffPaymentDetailView(APIView):
    permission_classes = [PaymentVerifierPermission]

    @extend_schema(responses=PaymentSerializer)
    def get(self, request, payment_id):
        return Response(PaymentSerializer(get_object_or_404(Payment, pk=payment_id)).data)


class StaffSubmissionListView(APIView):
    permission_classes = [PaymentVerifierPermission]

    @extend_schema(responses=SubmissionSerializer(many=True))
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id)
        return Response(SubmissionSerializer(payment.submissions.all(), many=True).data)


class StaffSubmissionReviewView(APIView):
    permission_classes = [PaymentVerifierPermission]

    @extend_schema(request=ReviewSerializer, responses=SubmissionSerializer)
    def post(self, request, payment_id, submission_id):
        payment = get_object_or_404(Payment, pk=payment_id)
        submission = get_object_or_404(PaymentSubmission, pk=submission_id, payment=payment)
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = review_submission(payment, submission, request.user, **serializer.validated_data)
        return Response(SubmissionSerializer(result).data)


class StaffVerifyPaymentView(APIView):
    permission_classes = [PaymentVerifierPermission]

    @extend_schema(request=VerifySerializer, responses=PaymentSerializer)
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id)
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission_id = serializer.validated_data.pop("submission_id")
        submission = get_object_or_404(PaymentSubmission, pk=submission_id, payment=payment)
        result = verify_payment(payment, submission, request.user, **serializer.validated_data)
        return Response(PaymentSerializer(result).data)


class StaffEvidenceView(APIView):
    permission_classes = [PaymentVerifierPermission]

    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, payment_id, submission_id):
        payment = get_object_or_404(Payment, pk=payment_id)
        submission = get_object_or_404(PaymentSubmission, pk=submission_id, payment=payment)
        if not submission.evidence_file:
            return Response({"detail": "Evidence is unavailable."}, status=404)
        try:
            file_handle = submission.evidence_file.open("rb")
        except Exception:
            return Response({"detail": "Evidence is unavailable."}, status=404)
        return FileResponse(file_handle, content_type=submission.content_type)
