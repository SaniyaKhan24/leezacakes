import signal
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.notifications.worker import process_due


class Command(BaseCommand):
    help = "Send queued notifications (email, WhatsApp) in the background."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process what is due, then exit.")
        parser.add_argument(
            "--interval",
            type=float,
            default=settings.NOTIFICATION_WORKER_INTERVAL,
            help="Seconds to wait when the queue is empty.",
        )
        parser.add_argument("--batch", type=int, default=settings.NOTIFICATION_WORKER_BATCH_SIZE)

    def handle(self, *args, once=False, interval=2.0, batch=20, **options):
        self.stopping = False

        def stop(signum, frame):
            self.stopping = True
            self.stdout.write("Stopping after the current batch…")

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        self.stdout.write(f"Notification worker started (batch {batch}, idle {interval}s).")
        while not self.stopping:
            # Long-running process: drop connections the database (or pooler) closed.
            close_old_connections()
            counts = process_due(batch)
            if counts["claimed"]:
                summary = ", ".join(f"{k} {v}" for k, v in counts.items() if v)
                self.stdout.write(f"Delivered batch: {summary}")
            if once:
                break
            if counts["claimed"] < batch:
                time.sleep(interval)
        close_old_connections()
