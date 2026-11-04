"""The outbox worker: queued deliveries, leasing, retries with backoff, and the command."""

import io
import urllib.error
from datetime import timedelta

import pytest
from django.contrib.admin.sites import site
from django.core.management import call_command
from django.db import transaction
from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications import services
from apps.notifications.admin import DeliveryAttemptAdmin
from apps.notifications.channels import DeliveryResult
from apps.notifications.models import DeliveryAttempt, Notification
from apps.notifications.services import emit_event
from apps.notifications.tests.helpers import configure_whatsapp
from apps.notifications.worker import claim_due, process_due


@pytest.fixture
def email_only(settings):
    settings.EMAIL_PROVIDER_ENABLED = True
    settings.NOTIFICATION_MAX_ATTEMPTS = 3
    settings.NOTIFICATION_RETRY_DELAYS = [60, 300]
    settings.NOTIFICATION_LEASE_SECONDS = 120
    return settings


@pytest.fixture
def customer(db):
    return User.objects.create_user(email="queue@example.com", phone_number="")


def queue_order_created(user, key="order:q:created"):
    payload = {"order_id": "", "order_number": "LZ-QUEUE-1", "customer_name": "Q"}
    return emit_event("order_created", user=user, payload=payload, deduplication_key=key)


def email_attempt():
    return DeliveryAttempt.objects.get(channel="email")


def test_emitting_only_queues_and_the_worker_sends(email_only, customer, mailoutbox):
    queue_order_created(customer)
    attempt = email_attempt()
    assert attempt.status == DeliveryAttempt.PENDING
    assert attempt.next_attempt_at <= timezone.now()
    assert mailoutbox == []

    counts = process_due()

    assert counts["claimed"] == 2  # email + whatsapp (skipped: provider off)
    assert counts[DeliveryAttempt.SENT] == 1
    assert counts[DeliveryAttempt.SKIPPED] == 1
    assert [mail.to for mail in mailoutbox] == [["queue@example.com"]]
    attempt.refresh_from_db()
    assert attempt.status == DeliveryAttempt.SENT
    assert attempt.attempt_count == 1
    assert attempt.next_attempt_at is None
    assert attempt.locked_until is None
    assert attempt.last_attempt_at is not None
    # Nothing left to do: a second pass is a no-op and sends no duplicate.
    assert process_due()["claimed"] == 0
    assert len(mailoutbox) == 1


def test_rolled_back_transaction_queues_nothing(email_only, customer):
    with pytest.raises(RuntimeError), transaction.atomic():
        queue_order_created(customer)
        raise RuntimeError("checkout failed")
    assert not Notification.objects.exists()
    assert not DeliveryAttempt.objects.exists()


def test_transient_failure_backs_off_then_succeeds(email_only, customer, monkeypatch):
    queue_order_created(customer)
    outcomes = iter([DeliveryResult.failed("SMTP timeout"), DeliveryResult.sent("ok-1")])
    real = services._deliver
    monkeypatch.setattr(
        services,
        "_deliver",
        lambda channel, message, recipient: (
            next(outcomes) if channel == "email" else real(channel, message, recipient)
        ),
    )

    before = timezone.now()
    process_due()
    attempt = email_attempt()
    assert attempt.status == DeliveryAttempt.FAILED
    assert attempt.error_message == "SMTP timeout"
    assert attempt.next_attempt_at >= before + timedelta(seconds=60)
    # Not due yet, so the worker leaves it alone.
    assert process_due()["claimed"] == 0

    DeliveryAttempt.objects.filter(pk=attempt.pk).update(next_attempt_at=timezone.now())
    process_due()
    attempt.refresh_from_db()
    assert attempt.status == DeliveryAttempt.SENT
    assert attempt.provider_message_id == "ok-1"
    assert attempt.attempt_count == 2
    assert attempt.next_attempt_at is None


def test_gives_up_after_max_attempts(email_only, customer, monkeypatch):
    queue_order_created(customer)
    monkeypatch.setattr(services, "_deliver", lambda *args: DeliveryResult.failed("still down"))
    for _ in range(3):
        DeliveryAttempt.objects.update(next_attempt_at=timezone.now())
        process_due()
    attempt = email_attempt()
    assert attempt.attempt_count == 3
    assert attempt.status == DeliveryAttempt.FAILED
    assert attempt.next_attempt_at is None
    assert services.retry_delay(1) == 60
    assert services.retry_delay(5) == 300  # the last delay repeats


def test_permanent_whatsapp_rejection_is_not_retried(settings, db, monkeypatch):
    settings.EMAIL_PROVIDER_ENABLED = False
    configure_whatsapp(sending_enabled=True, access_token="secret-token", phone_number_id="12345")
    user = User.objects.create_user(email="wa@example.com", phone_number="+919876543210")
    payload = {"order_id": "", "order_number": "LZ-WA-1", "customer_name": "W"}
    emit_event("order_created", user=user, payload=payload, deduplication_key="wa:1")

    def rejected(request, timeout):
        body = io.BytesIO(b'{"error": {"message": "Template name does not exist"}}')
        raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, body)

    monkeypatch.setattr("urllib.request.urlopen", rejected)
    process_due()
    attempt = DeliveryAttempt.objects.get(channel="whatsapp")
    assert attempt.status == DeliveryAttempt.FAILED
    assert "Template name does not exist" in attempt.error_message
    assert "secret-token" not in attempt.error_message
    assert attempt.next_attempt_at is None


def test_rate_limited_whatsapp_is_retried(settings, db, monkeypatch):
    settings.EMAIL_PROVIDER_ENABLED = False
    configure_whatsapp(sending_enabled=True, access_token="secret-token", phone_number_id="12345")
    user = User.objects.create_user(email="wa2@example.com", phone_number="+919876543210")
    payload = {"order_id": "", "order_number": "LZ-WA-2", "customer_name": "W"}
    emit_event("order_created", user=user, payload=payload, deduplication_key="wa:2")

    def throttled(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many", {}, io.BytesIO(b"{}"))

    monkeypatch.setattr("urllib.request.urlopen", throttled)
    process_due()
    attempt = DeliveryAttempt.objects.get(channel="whatsapp")
    assert attempt.status == DeliveryAttempt.FAILED
    assert attempt.next_attempt_at is not None


def test_leased_rows_are_not_claimed_twice_until_the_lease_expires(email_only, customer):
    queue_order_created(customer)
    first = claim_due(10)
    assert len(first) == 2
    assert claim_due(10) == []  # another worker sees nothing while the lease holds
    DeliveryAttempt.objects.update(locked_until=timezone.now() - timedelta(seconds=1))
    assert sorted(claim_due(10)) == sorted(first)  # a crashed worker's rows come back


def test_a_crashing_row_does_not_stop_the_batch(email_only, db, monkeypatch, mailoutbox):
    users = [User.objects.create_user(email=f"c{i}@example.com") for i in range(2)]
    for i, user in enumerate(users):
        queue_order_created(user, key=f"order:crash:{i}")
    crash_for = "c0@example.com"
    real = services._deliver

    def flaky(channel, message, recipient):
        if recipient == crash_for:
            raise RuntimeError("boom")
        return real(channel, message, recipient)

    monkeypatch.setattr(services, "_deliver", flaky)
    process_due()
    assert [mail.to for mail in mailoutbox] == [["c1@example.com"]]
    # The crashed row keeps its lease and is picked up again once the lease expires.
    crashed = DeliveryAttempt.objects.get(recipient=crash_for)
    assert crashed.status == DeliveryAttempt.PENDING
    assert crashed.locked_until > timezone.now()
    assert crashed.id not in claim_due(10)
    DeliveryAttempt.objects.filter(pk=crashed.pk).update(locked_until=timezone.now())
    assert crashed.id in claim_due(10)


def test_worker_command_once(email_only, customer, mailoutbox):
    queue_order_created(customer)
    out = io.StringIO()
    call_command("run_notification_worker", "--once", stdout=out)
    assert "Delivered batch" in out.getvalue()
    assert len(mailoutbox) == 1


def test_admin_retry_now_requeues_unsent(email_only, customer, monkeypatch):
    queue_order_created(customer)
    monkeypatch.setattr(services, "_deliver", lambda *args: DeliveryResult.failed("x", False))
    process_due()
    assert DeliveryAttempt.objects.filter(next_attempt_at__isnull=True).count() == 2

    staff = User.objects.create_superuser(email="ops@example.com", password="Ops-pass-123!")
    request = RequestFactory().post("/admin/")
    request.user = staff
    model_admin = DeliveryAttemptAdmin(DeliveryAttempt, site)
    monkeypatch.setattr(model_admin, "message_user", lambda *args, **kwargs: None)
    model_admin.retry_now(request, DeliveryAttempt.objects.all())
    assert (
        DeliveryAttempt.objects.filter(
            status=DeliveryAttempt.PENDING, next_attempt_at__isnull=False
        ).count()
        == 2
    )
