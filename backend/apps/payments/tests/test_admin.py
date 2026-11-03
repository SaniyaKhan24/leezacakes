from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.orders.models import Order
from apps.payments.admin import DEFAULT_REJECTION_REASON
from apps.payments.models import Payment, PaymentSubmission
from apps.payments.serializers import PaymentSerializer
from apps.payments.services import submit_evidence

from .test_models import image_upload, order  # noqa: F401

UPI = {
    "PAYMENT_UPI_ID": "shop.sample@example",
    "PAYMENT_UPI_PAYEE_NAME": "Leeza Cakes & Co",
    "PAYMENT_UPI_IS_SAMPLE": True,
}


@pytest.fixture
def payment(order):  # noqa: F811
    return Payment.objects.create(order=order, user=order.user, amount_due=order.grand_total)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="studio@example.com", password="Studio-pass-123!")


def messages_for(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


@override_settings(**UPI)
def test_customer_payment_includes_upi_instructions(payment):
    client = APIClient()
    client.force_authenticate(user=payment.user)
    data = client.get(f"/api/v1/payments/orders/{payment.order_id}/").data
    assert data["order_number"] == "LZ-TEST-1"
    instructions = data["instructions"]
    assert instructions["upi_id"] == "shop.sample@example"
    assert instructions["payee_name"] == "Leeza Cakes & Co"
    assert instructions["amount"] == "100.00"
    assert instructions["currency"] == "INR"
    assert instructions["is_sample"] is True
    assert "Do not send money" in instructions["note"]
    assert "LZ-TEST-1" in instructions["note"]
    uri = instructions["upi_uri"]
    assert uri.startswith("upi://pay?pa=shop.sample@example&pn=Leeza%20Cakes%20%26%20Co&")
    query = parse_qs(urlsplit(uri).query)
    assert query == {
        "pa": ["shop.sample@example"],
        "pn": ["Leeza Cakes & Co"],
        "am": ["100.00"],
        "cu": ["INR"],
        "tn": ["LZ-TEST-1"],
    }


@override_settings(PAYMENT_UPI_ID="shop@example", PAYMENT_UPI_PAYEE_NAME="")
def test_instructions_omit_blank_payee_and_sample_note(payment):
    instructions = PaymentSerializer(payment).data["instructions"]
    assert "pn=" not in instructions["upi_uri"]
    assert instructions["is_sample"] is False
    assert "Do not send money" not in instructions["note"]


def test_instructions_are_null_without_upi_id_but_upload_still_works(payment):
    assert settings.PAYMENT_UPI_ID == ""
    client = APIClient()
    client.force_authenticate(user=payment.user)
    assert client.get(f"/api/v1/payments/{payment.id}/").data["instructions"] is None
    uploaded = client.post(
        f"/api/v1/payments/{payment.id}/submissions/",
        {"evidence": image_upload()},
        format="multipart",
    )
    assert uploaded.status_code == 201


def test_evidence_is_stored_outside_the_repository(payment):
    submission = submit_evidence(payment, payment.user, image_upload())
    path = Path(submission.evidence_file.path)
    assert path.is_file()
    assert Path(settings.PAYMENT_EVIDENCE_STORAGE_ROOT) in path.parents
    assert Path(settings.BASE_DIR) not in path.parents


def test_staff_evidence_view_works_with_admin_session(payment, superuser, client):
    submission = submit_evidence(payment, payment.user, image_upload())
    url = f"/api/v1/payments/staff/{payment.id}/submissions/{submission.id}/evidence/"
    assert client.get(url).status_code in {401, 403}
    client.force_login(superuser)
    response = client.get(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert b"".join(response.streaming_content).startswith(b"\x89PNG")
    verifier = User.objects.create_user(email="verifier@example.com", is_staff=True)
    client.force_login(verifier)
    assert client.get(url).status_code == 403
    verifier.user_permissions.add(Permission.objects.get(codename="verify_payment"))
    verifier = User.objects.get(pk=verifier.pk)
    client.force_login(verifier)
    assert client.get(url).status_code == 200


def test_payment_admin_change_page_shows_evidence_link(payment, superuser, client):
    submission = submit_evidence(payment, payment.user, image_upload())
    client.force_login(superuser)
    page = client.get(f"/admin/payments/payment/{payment.id}/change/")
    assert page.status_code == 200
    assert (
        f"/api/v1/payments/staff/{payment.id}/submissions/{submission.id}/evidence/"
        in page.content.decode()
    )
    listing = client.get("/admin/payments/payment/")
    assert listing.status_code == 200
    assert "LZ-TEST-1" in listing.content.decode()


def test_admin_accept_and_verify_confirms_order(payment, superuser, client):
    submit_evidence(payment, payment.user, image_upload())
    client.force_login(superuser)
    response = client.post(
        "/admin/payments/payment/",
        {"action": "accept_and_verify", "_selected_action": [str(payment.id)]},
        follow=True,
    )
    assert response.status_code == 200
    assert any("Verified 1 payment" in text for text in messages_for(response))
    payment.refresh_from_db()
    assert payment.status == Payment.VERIFIED
    assert payment.verified_amount == payment.amount_due
    assert payment.verified_by == superuser
    confirmed = Order.objects.get(pk=payment.order_id)
    assert confirmed.status == Order.CONFIRMED
    assert confirmed.payment_status == Order.PAYMENT_VERIFIED
    assert payment.submissions.get().status == PaymentSubmission.ACCEPTED


def test_admin_accept_reports_missing_proof(payment, superuser, client):
    client.force_login(superuser)
    response = client.post(
        "/admin/payments/payment/",
        {"action": "accept_and_verify", "_selected_action": [str(payment.id)]},
        follow=True,
    )
    assert any("no payment proof" in text for text in messages_for(response))
    assert Payment.objects.get(pk=payment.pk).status == Payment.AWAITING


def test_admin_reject_latest_then_accept_reports_error(payment, superuser, client):
    submit_evidence(payment, payment.user, image_upload())
    client.force_login(superuser)
    response = client.post(
        "/admin/payments/payment/",
        {"action": "reject_latest", "_selected_action": [str(payment.id)]},
        follow=True,
    )
    assert any("Rejected 1 proof" in text for text in messages_for(response))
    submission = payment.submissions.get()
    assert submission.status == PaymentSubmission.REJECTED
    assert submission.rejection_reason == DEFAULT_REJECTION_REASON
    assert Payment.objects.get(pk=payment.pk).status == Payment.REJECTED
    again = client.post(
        "/admin/payments/payment/",
        {"action": "reject_latest", "_selected_action": [str(payment.id)]},
        follow=True,
    )
    assert any("no proof waiting" in text for text in messages_for(again))
    accept = client.post(
        "/admin/payments/payment/",
        {"action": "accept_and_verify", "_selected_action": [str(payment.id)]},
        follow=True,
    )
    assert any("accepted before verification" in text for text in messages_for(accept))
    assert Payment.objects.get(pk=payment.pk).status == Payment.REJECTED


def test_admin_payment_actions_require_verify_permission(payment, client):
    staff = User.objects.create_user(email="viewer@example.com", is_staff=True)
    staff.user_permissions.add(
        Permission.objects.get(codename="view_payment"),
        Permission.objects.get(codename="change_payment"),
    )
    submit_evidence(payment, payment.user, image_upload())
    client.force_login(staff)
    page = client.get("/admin/payments/payment/")
    assert page.status_code == 200
    assert "accept_and_verify" not in page.content.decode()
