from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from PIL import Image

from apps.accounts.models import User
from apps.cart.models import Cart, CartItem
from apps.catalog.models import Category, Product, ProductImage, ProductVariant
from apps.customization.models import ProductCustomization, ProductCustomizationChoice
from apps.orders.models import Order
from apps.payments.models import Payment, PaymentSubmission


@pytest.fixture
def assets(tmp_path):
    root = tmp_path / "assets"
    (root / "products").mkdir(parents=True)
    (root / "categories").mkdir()
    for name in ("red-velvet.webp", "red-velvet-2.webp", "pistachio-rose.webp"):
        Image.new("RGB", (40, 50), "pink").save(root / "products" / name, "WEBP")
    Image.new("RGB", (40, 30), "brown").save(root / "categories" / "signature.webp", "WEBP")
    return root


def run(command, *args, **kwargs):
    out = StringIO()
    call_command(command, *args, stdout=out, stderr=StringIO(), **kwargs)
    return out.getvalue()


@pytest.mark.django_db
def test_seed_commands_refuse_non_debug_without_force(assets):
    with pytest.raises(CommandError):
        run("seed_demo_catalog", assets_dir=str(assets))
    with pytest.raises(CommandError):
        run("seed_demo", assets_dir=str(assets))


@pytest.mark.django_db
def test_forced_non_debug_seed_skips_accounts(assets):
    output = run("seed_demo", force=True, assets_dir=str(assets))
    assert Product.objects.count() == 14
    assert "skipped demo accounts" in output
    assert not User.objects.exists()


@pytest.mark.django_db
def test_catalog_seed_is_idempotent_and_reports_missing_assets(assets):
    legacy = Category.objects.create(name="Celebration Cakes", slug="celebration-cakes")
    old = Product.objects.create(
        name="Red Velvet",
        slug="red-velvet",
        description="old",
        category=legacy,
        status=Product.PUBLISHED,
        base_price="800.00",
    )
    referenced = ProductVariant.objects.create(product=old, name="6–8 servings", price="800.00")
    unused = Product.objects.create(
        name="Black Forest",
        slug="black-forest",
        description="old",
        category=legacy,
        base_price="760.00",
    )
    ProductVariant.objects.create(product=unused, name="6–8 servings", price="760.00")
    cart = Cart.objects.create(session_key="seed-test")
    CartItem.objects.create(cart=cart, product=old, variant=referenced, quantity=1)

    output = run("seed_demo_catalog", force=True, assets_dir=str(assets))
    assert "WARNING: 16 seed image(s) missing" in output  # 12 products + 4 categories
    assert "biscoff-bento.webp" in output and "categories/bento.webp" in output
    assert "optional second-angle" in output

    assert Category.objects.filter(is_active=True).count() == 5
    assert not Category.objects.get(slug="celebration-cakes").is_active
    red_velvet = Product.objects.get(slug="red-velvet")
    assert red_velvet.category.slug == "signature"
    assert red_velvet.base_price == 800
    assert red_velvet.weight_description == "Half kilo · serves 4–6"
    assert not ProductVariant.objects.get(pk=referenced.pk).is_active
    assert not ProductVariant.objects.filter(product__slug="black-forest", name="6–8 servings")
    assert list(red_velvet.variants.filter(is_active=True).values_list("sku", "price")) == [
        ("LZ-RV-1", 800),
        ("LZ-RV-2", 1490),
        ("LZ-RV-3", 2150),
    ]
    primary = red_velvet.images.get(is_primary=True)
    assert primary.sort_order == 0 and "Red Velvet" in primary.alt_text
    assert red_velvet.images.count() == 2
    assert Category.objects.get(slug="signature").image.name.endswith(".webp")

    egg = ProductCustomization.objects.get(
        product__slug="gilded-three-tier", option__slug="egg-preference"
    )
    assert egg.is_required
    assert (
        ProductCustomizationChoice.objects.get(
            product_customization=egg, choice__slug="eggless"
        ).price_adjustment
        == 400
    )
    bento_options = set(
        ProductCustomization.objects.filter(
            product__slug="bento-hearts", is_active=True
        ).values_list("option__slug", flat=True)
    )
    assert bento_options == {"egg-preference", "message-on-cake", "candles"}

    counts = (
        Product.objects.count(),
        ProductVariant.objects.count(),
        ProductImage.objects.count(),
        ProductCustomizationChoice.objects.count(),
    )
    run("seed_demo_catalog", force=True, assets_dir=str(assets))
    assert counts == (
        Product.objects.count(),
        ProductVariant.objects.count(),
        ProductImage.objects.count(),
        ProductCustomizationChoice.objects.count(),
    )
    assert red_velvet.images.get(is_primary=True).pk == primary.pk

    # A changed asset replaces the seeded image instead of adding another.
    Image.new("RGB", (60, 60), "red").save(assets / "products" / "red-velvet.webp", "WEBP")
    run("seed_demo_catalog", force=True, assets_dir=str(assets))
    assert red_velvet.images.count() == 2
    assert red_velvet.images.get(is_primary=True).pk != primary.pk


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_full_demo_seed_creates_accounts_and_orders(assets):
    output = run("seed_demo", assets_dir=str(assets))
    assert "demo@leezacakes.test / LeezaDemo!2026" in output
    assert "studio@leezacakes.test / LeezaStudio!2026" in output
    customer = User.objects.get(email="demo@leezacakes.test")
    assert customer.check_password("LeezaDemo!2026") and customer.is_email_verified
    assert customer.addresses.get().is_default
    staff = User.objects.get(email="studio@leezacakes.test")
    assert staff.is_staff and staff.is_superuser and staff.check_password("LeezaStudio!2026")

    orders = {order.status: order for order in Order.objects.filter(user=customer)}
    assert set(orders) == {
        Order.COMPLETED,
        Order.READY,
        Order.PENDING_PAYMENT,
    }
    assert Order.objects.filter(user=customer).count() == 4
    completed = orders[Order.COMPLETED]
    assert completed.created_at < completed.confirmed_at < completed.pickup_slot_start
    assert completed.pickup_slot_start < completed.completed_at
    history = list(completed.status_history.order_by("created_at").values_list("to_status"))
    assert [row[0] for row in history] == [
        Order.PENDING_PAYMENT,
        Order.CONFIRMED,
        Order.PREPARING,
        Order.READY,
        Order.COMPLETED,
    ]
    item = completed.items.get()
    assert item.variant_name_snapshot == "1 kg · serves 8–10"
    assert item.customizations.filter(value_snapshot="Happy 30th, Kabir").exists()
    ready_item = orders[Order.READY].items.get()
    assert ready_item.product_name_snapshot == "Pistachio Rose"
    assert ready_item.customizations.filter(choice_name_snapshot="Eggless").exists()
    statuses = sorted(Payment.objects.filter(user=customer).values_list("status", flat=True))
    assert statuses == ["awaiting_payment", "pending_verification", "verified", "verified"]
    assert PaymentSubmission.objects.filter(status=PaymentSubmission.PENDING_REVIEW).count() == 1

    rerun = run("seed_demo", assets_dir=str(assets))
    assert "skipping sample orders" in rerun
    assert Order.objects.filter(user=customer).count() == 4
    assert User.objects.filter(email=customer.email).count() == 1

    reset = run("seed_demo", assets_dir=str(assets), reset_orders=True)
    assert "Deleted 4 existing demo order(s)" in reset
    assert Order.objects.filter(user=customer).count() == 4
    assert Payment.objects.filter(user=customer).count() == 4
