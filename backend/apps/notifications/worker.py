"""Background delivery of queued notifications (the outbox worker).

Run alongside the web server:  python manage.py run_notification_worker

Each pass claims a batch of due deliveries under a short lease (with SKIP LOCKED on
PostgreSQL, so several workers can run side by side), sends them outside the
claiming transaction, and records the result. A worker that dies mid-send only
delays those rows until its lease expires.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from .models import DeliveryAttempt
from .services import deliver_attempt

logger = logging.getLogger(__name__)


def claim_due(batch_size):
    """Lease up to `batch_size` due deliveries and return their ids."""
    now = timezone.now()
    lease = now + timedelta(seconds=settings.NOTIFICATION_LEASE_SECONDS)
    with transaction.atomic():
        due = (
            DeliveryAttempt.objects.filter(next_attempt_at__lte=now)
            .filter(Q(locked_until__isnull=True) | Q(locked_until__lt=now))
            .order_by("next_attempt_at", "id")
        )
        if connection.features.has_select_for_update_skip_locked:
            due = due.select_for_update(skip_locked=True)
        else:  # SQLite (local development): one worker, the lease alone is enough.
            due = due.select_for_update()
        ids = list(due.values_list("id", flat=True)[:batch_size])
        DeliveryAttempt.objects.filter(id__in=ids).update(locked_until=lease)
    return ids


def process_due(batch_size=None):
    """Deliver everything currently due. Returns {"claimed": n, "sent": n, ...}."""
    batch_size = batch_size or settings.NOTIFICATION_WORKER_BATCH_SIZE
    counts = {"claimed": 0, DeliveryAttempt.SENT: 0, DeliveryAttempt.SKIPPED: 0}
    counts[DeliveryAttempt.FAILED] = 0
    ids = claim_due(batch_size)
    counts["claimed"] = len(ids)
    attempts = DeliveryAttempt.objects.select_related("notification__user").filter(id__in=ids)
    for attempt in attempts.order_by("next_attempt_at", "id"):
        try:
            attempt = deliver_attempt(attempt)
        except Exception:  # never let one bad row stop the worker
            logger.exception("Delivery %s crashed; it will be retried after its lease", attempt.pk)
            continue
        counts[attempt.status] = counts.get(attempt.status, 0) + 1
    return counts
