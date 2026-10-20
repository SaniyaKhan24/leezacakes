from django.contrib.auth.models import Permission
from django.test import override_settings
from rest_framework.test import APIClient

from apps.payments.models import Payment

from .test_models import image_upload, order  # noqa: F401


@override_settings(PAYMENT_EVIDENCE_STORAGE_ROOT="C:/tmp/leeza-payment-view-tests")
def test_customer_submission_and_staff_review_api(order):  # noqa: F811
    payment = Payment.objects.create(order=order, user=order.user, amount_due=order.grand_total)
    client = APIClient()
    client.force_authenticate(user=order.user)
    assert client.get(f"/api/v1/payments/{payment.id}/").status_code == 200
    uploaded = client.post(
        f"/api/v1/payments/{payment.id}/submissions/",
        {"evidence": image_upload()},
        format="multipart",
    )
    assert uploaded.status_code == 201
    submission_id = uploaded.data["id"]
    assert client.get(f"/api/v1/payments/{payment.id}/submissions/").status_code == 200
    reviewer = type(order.user).objects.create_user(email="api-reviewer@example.com", is_staff=True)
    reviewer.user_permissions.add(Permission.objects.get(codename="verify_payment"))
    client.force_authenticate(user=reviewer)
    assert client.get("/api/v1/payments/staff/").status_code == 200
    reviewed = client.post(
        f"/api/v1/payments/staff/{payment.id}/submissions/{submission_id}/review/",
        {"decision": "accept"},
        format="json",
    )
    assert reviewed.status_code == 200
    verified = client.post(
        f"/api/v1/payments/staff/{payment.id}/verify/",
        {"submission_id": submission_id, "verified_amount": "100.00"},
        format="json",
    )
    assert verified.status_code == 200
