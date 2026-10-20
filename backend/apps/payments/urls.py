from django.urls import path

from .views import (
    CustomerPaymentByOrderView,
    CustomerPaymentView,
    CustomerSubmissionDetailView,
    CustomerSubmissionListCreateView,
    StaffEvidenceView,
    StaffPaymentDetailView,
    StaffPaymentListView,
    StaffSubmissionListView,
    StaffSubmissionReviewView,
    StaffVerifyPaymentView,
)

urlpatterns = [
    path("orders/<uuid:order_id>/", CustomerPaymentByOrderView.as_view()),
    path("staff/", StaffPaymentListView.as_view()),
    path("staff/<uuid:payment_id>/", StaffPaymentDetailView.as_view()),
    path("staff/<uuid:payment_id>/submissions/", StaffSubmissionListView.as_view()),
    path("staff/<uuid:payment_id>/verify/", StaffVerifyPaymentView.as_view()),
    path(
        "staff/<uuid:payment_id>/submissions/<uuid:submission_id>/review/",
        StaffSubmissionReviewView.as_view(),
    ),
    path(
        "staff/<uuid:payment_id>/submissions/<uuid:submission_id>/evidence/",
        StaffEvidenceView.as_view(),
    ),
    path("<uuid:payment_id>/", CustomerPaymentView.as_view()),
    path("<uuid:payment_id>/submissions/", CustomerSubmissionListCreateView.as_view()),
    path(
        "<uuid:payment_id>/submissions/<uuid:submission_id>/",
        CustomerSubmissionDetailView.as_view(),
    ),
]
