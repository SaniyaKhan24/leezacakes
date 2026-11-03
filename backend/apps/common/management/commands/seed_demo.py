from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from apps.accounts.models import User
from apps.accounts.services import create_address
from apps.cart.models import Cart
from apps.cart.services.cart_service import add_item
from apps.catalog.management.commands.seed_demo_catalog import DEFAULT_ASSETS_DIR
from apps.catalog.models import Product
from apps.customization.models import ProductCustomization
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.services.checkout import create_order
from apps.orders.services.pickup import PickupConfig, cart_lead_time, first_available_slot
from apps.orders.services.transitions import transition_order
from apps.payments.models import Payment, PaymentStatusHistory, PaymentSubmission
from apps.payments.services import review_submission, submit_evidence, verify_payment

CUSTOMER = {
    "email": "demo@leezacakes.test",
    "password": "LeezaDemo!2026",  # nosec B105 - documented DEBUG-only demo credential
    "first_name": "Aanya",
    "last_name": "Rao",
    "phone_number": "+91 90000 00001",
}
STAFF = {
    "email": "studio@leezacakes.test",
    "password": "LeezaStudio!2026",  # nosec B105 - documented DEBUG-only demo credential
    "first_name": "Leeza",
    "last_name": "Studio",
}
SAMPLE_ADDRESS = {
    "label": "Home (sample)",
    "recipient_name": "Aanya Rao",
    "phone_number": "+91 90000 00001",
    "address_line_1": "Flat 4B, Sample Residency",
    "address_line_2": "12th Main Road",
    "locality": "Indiranagar",
    "city": "Bengaluru",
    "state": "Karnataka",
    "postal_code": "560038",
    "country_code": "IN",
}


def sample_proof_image(order_number, amount):
    """A small, obviously fake UPI receipt used as demo payment evidence."""
    image = Image.new("RGB", (420, 640), "#fbf7f2")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default(size=22)
        small = ImageFont.load_default(size=16)
    except TypeError:  # Pillow without scalable default font.
        font = small = ImageFont.load_default()
    draw.rectangle((0, 0, 420, 90), fill="#5b2b2b")
    draw.text((24, 30), "SAMPLE UPI RECEIPT", fill="white", font=font)
    lines = (
        ("Payment successful", font),
        (f"INR {amount}", font),
        ("To: Leeza Cakes (sample)", small),
        (f"Note: {order_number}", small),
        ("UTR: SAMPLE-000000000000", small),
        ("", small),
        ("Demo data - not a real transaction.", small),
    )
    y = 130
    for text, face in lines:
        draw.text((24, y), text, fill="#2b1d1d", font=face)
        y += 48
    stream = BytesIO()
    image.save(stream, format="PNG")
    return SimpleUploadedFile(
        f"upi-proof-{order_number}.png", stream.getvalue(), content_type="image/png"
    )


class Command(BaseCommand):
    help = (
        "Seed everything for a local demo: catalogue, customisation, demo customer and staff "
        "accounts, and sample orders in several states. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow seeding the catalogue when DEBUG is false. Accounts and orders are "
            "only ever seeded with DEBUG=True.",
        )
        parser.add_argument("--assets-dir", default=str(DEFAULT_ASSETS_DIR))
        parser.add_argument(
            "--reset-orders",
            action="store_true",
            help="Delete the demo customer's orders and recreate the sample orders.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to seed a non-debug environment without --force.")
        call_command(
            "seed_demo_catalog",
            force=options["force"],
            assets_dir=options["assets_dir"],
            stdout=self.stdout,
            stderr=self.stderr,
        )
        if not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING("DEBUG is false: skipped demo accounts and sample orders.")
            )
            return
        customer, staff = self.seed_users()
        self.seed_orders(customer, staff, reset=options["reset_orders"])
        self.stdout.write(
            self.style.SUCCESS(
                "\nDemo accounts (local development only):\n"
                f"  Customer: {CUSTOMER['email']} / {CUSTOMER['password']}\n"
                f"  Staff:    {STAFF['email']} / {STAFF['password']}  -> /admin/"
            )
        )

    # Accounts -------------------------------------------------------------------------------

    def _upsert_user(self, data, **flags):
        user = User.objects.filter(email=data["email"]).first() or User(email=data["email"])
        for key, value in data.items():
            if key not in {"email", "password"}:
                setattr(user, key, value)
        for key, value in flags.items():
            setattr(user, key, value)
        user.is_active = True
        user.is_email_verified = True
        user.set_password(data["password"])
        user.save()
        return user

    @transaction.atomic
    def seed_users(self):
        customer = self._upsert_user(CUSTOMER, is_staff=False, is_superuser=False)
        staff = self._upsert_user(STAFF, is_staff=True, is_superuser=True)
        if not customer.addresses.exists():
            create_address(customer, is_default=True, **SAMPLE_ADDRESS)
        return customer, staff

    # Orders ---------------------------------------------------------------------------------

    def seed_orders(self, customer, staff, reset):
        existing = Order.objects.filter(user=customer)
        if existing.exists() and not reset:
            self.stdout.write(
                f"Demo customer already has {existing.count()} order(s); skipping sample "
                "orders (use --reset-orders to recreate them)."
            )
            return
        if reset:
            self.delete_orders(existing)
        cart = Cart.objects.filter(user=customer, status=Cart.ACTIVE).first()
        if cart and cart.items.exists():
            self.stdout.write("Cleared the demo customer's active cart to place sample orders.")
            cart.items.all().delete()

        completed = self.place(
            customer,
            "seed-demo-completed",
            [("red-velvet", 1, 1, {"egg-preference": ["contains-egg"]}, "Happy 30th, Kabir")],
        )
        self.pay(completed, staff)
        for status in (Order.PREPARING, Order.READY, Order.COMPLETED):
            transition_order(completed, status, actor=staff, reason="Sample order.")
        days_ago = timezone.localtime() - timedelta(days=12)
        pickup = days_ago.replace(hour=17, minute=0, second=0, microsecond=0)
        self.backdate(completed, pickup - timedelta(days=2), pickup)
        self.retime(
            completed,
            {
                Order.PREPARING: pickup - timedelta(hours=6),
                Order.READY: pickup - timedelta(minutes=30),
                Order.COMPLETED: pickup + timedelta(minutes=20),
            },
        )

        ready = self.place(
            customer,
            "seed-demo-ready",
            [("pistachio-rose", 0, 1, {"egg-preference": ["eggless"]}, "")],
        )
        self.pay(ready, staff)
        for status in (Order.PREPARING, Order.READY):
            transition_order(ready, status, actor=staff, reason="Sample order.")
        soon = first_available_slot(timezone.now(), 60, PickupConfig.from_settings())
        self.backdate(ready, timezone.now() - timedelta(days=1), soon[0] if soon else None)
        now = timezone.now()
        self.retime(
            ready,
            {Order.PREPARING: now - timedelta(hours=3), Order.READY: now - timedelta(minutes=20)},
        )

        pending = self.place(
            customer,
            "seed-demo-pending",
            [
                (
                    "chocolate-truffle",
                    1,
                    1,
                    {
                        "egg-preference": ["contains-egg"],
                        "finishing-touches": ["gold-leaf", "macarons"],
                        "candles": ["number-candles"],
                    },
                    "Congratulations, Meera",
                )
            ],
        )
        payment = Payment.objects.get(order=pending)
        submit_evidence(
            payment, customer, sample_proof_image(pending.order_number, payment.amount_due)
        )
        self.backdate(pending, timezone.now() - timedelta(hours=2), None)

        awaiting = self.place(
            customer,
            "seed-demo-awaiting",
            [
                ("bento-hearts", 0, 1, {"egg-preference": ["eggless"]}, "Love you, Amma"),
                ("biscoff-bento", 0, 2, {"egg-preference": ["contains-egg"]}, ""),
            ],
        )
        for order in (completed, ready, pending, awaiting):
            order.refresh_from_db()
        self.stdout.write(
            self.style.SUCCESS(
                "Created sample orders: "
                f"{completed.order_number} (completed), {ready.order_number} (ready for "
                f"pickup), {pending.order_number} (payment proof awaiting review), "
                f"{awaiting.order_number} (awaiting payment)."
            )
        )

    def _selections(self, product, choices, message):
        configs = {
            config.option.slug: config
            for config in ProductCustomization.objects.filter(product=product, is_active=True)
            .select_related("option")
            .prefetch_related("choices__choice")
        }
        rows = []
        for option_slug, choice_slugs in choices.items():
            config = configs[option_slug]
            ids = [row.choice_id for row in config.choices.all() if row.choice.slug in choice_slugs]
            rows.append({"option_id": config.option_id, "choice_ids": ids})
        if message:
            rows.append({"option_id": configs["message-on-cake"].option_id, "text_value": message})
        return rows

    @transaction.atomic
    def place(self, customer, key, lines):
        cart, _ = Cart.objects.get_or_create(user=customer, status=Cart.ACTIVE)
        for slug, variant_index, quantity, choices, message in lines:
            product = Product.objects.get(slug=slug)
            variant = list(product.variants.filter(is_active=True).order_by("sort_order"))[
                variant_index
            ]
            add_item(
                cart, product.id, variant.id, quantity, self._selections(product, choices, message)
            )
        config = PickupConfig.from_settings()
        slot = first_available_slot(timezone.now(), cart_lead_time(cart, config), config)
        if slot is None:
            raise CommandError("No pickup slot is available for the sample orders.")
        order, _ = create_order(
            customer,
            {
                "customer_name": f"{customer.first_name} {customer.last_name}",
                "customer_phone": customer.phone_number,
                "customer_email": customer.email,
                "pickup_slot_start": slot[0],
                "pickup_slot_end": slot[1],
                "customer_note": "Sample order created by seed_demo.",
            },
            key,
        )
        return order

    @transaction.atomic
    def pay(self, order, staff):
        payment = Payment.objects.get(order=order)
        submission = submit_evidence(
            payment, order.user, sample_proof_image(order.order_number, payment.amount_due)
        )
        review_submission(payment, submission, staff, "accept")
        verify_payment(payment, submission, staff, payment.amount_due, reason="Sample order.")
        order.refresh_from_db()

    @transaction.atomic
    def backdate(self, order, created_at, pickup_start):
        """Shift an order's timeline so it reads naturally in the demo."""
        order.refresh_from_db()
        delta = created_at - order.created_at
        fields = {"created_at": F("created_at") + delta, "updated_at": F("updated_at") + delta}
        prefix, _, suffix = order.order_number.rpartition("-")
        if prefix.startswith("LZ-"):
            # Keep the order number's date in step with the shifted creation date.
            fields["order_number"] = f"LZ-{timezone.localtime(created_at):%Y%m%d}-{suffix}"
        for name in ("confirmed_at", "completed_at", "cancelled_at"):
            if getattr(order, name):
                fields[name] = F(name) + delta
        if pickup_start is not None:
            length = order.pickup_slot_end - order.pickup_slot_start
            fields["pickup_slot_start"] = pickup_start
            fields["pickup_slot_end"] = pickup_start + length
        Order.objects.filter(pk=order.pk).update(**fields)
        OrderStatusHistory.objects.filter(order=order).update(created_at=F("created_at") + delta)
        payment = Payment.objects.filter(order=order)
        payment.update(created_at=F("created_at") + delta, updated_at=F("updated_at") + delta)
        payment.filter(verified_at__isnull=False).update(verified_at=F("verified_at") + delta)
        submissions = PaymentSubmission.objects.filter(payment__order=order)
        submissions.update(submitted_at=F("submitted_at") + delta)
        submissions.filter(reviewed_at__isnull=False).update(reviewed_at=F("reviewed_at") + delta)
        PaymentStatusHistory.objects.filter(payment__order=order).update(
            created_at=F("created_at") + delta
        )

    @transaction.atomic
    def retime(self, order, moments):
        """Place lifecycle steps at realistic times relative to the pickup."""
        for status, moment in moments.items():
            OrderStatusHistory.objects.filter(order=order, to_status=status).update(
                created_at=moment
            )
        if Order.COMPLETED in moments:
            Order.objects.filter(pk=order.pk).update(
                completed_at=moments[Order.COMPLETED], updated_at=moments[Order.COMPLETED]
            )
        else:
            Order.objects.filter(pk=order.pk).update(updated_at=max(moments.values()))

    @transaction.atomic
    def delete_orders(self, orders):
        count = orders.count()
        PaymentStatusHistory.objects.filter(payment__order__in=orders).delete()
        for submission in PaymentSubmission.objects.filter(payment__order__in=orders):
            submission.evidence_file.delete(save=False)
            submission.delete()
        Payment.objects.filter(order__in=orders).delete()
        orders.delete()
        self.stdout.write(f"Deleted {count} existing demo order(s).")
