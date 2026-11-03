import hashlib
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.catalog import seed_data
from apps.catalog.models import Category, Product, ProductImage, ProductVariant
from apps.customization.models import (
    CustomizationChoice,
    CustomizationOption,
    ProductCustomization,
    ProductCustomizationChoice,
)

DEFAULT_ASSETS_DIR = Path(__file__).resolve().parents[2] / seed_data.SEED_ASSETS_DIR_NAME
SEED_PREFIX = "seed-"


def _digest(handle):
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    handle.seek(0)
    return digest.hexdigest()


def _same_file(field_file, path):
    if not field_file or not field_file.storage.exists(field_file.name):
        return False
    with field_file.storage.open(field_file.name, "rb") as current, path.open("rb") as new:
        return _digest(current) == _digest(new)


class Command(BaseCommand):
    help = (
        "Seed the local development catalogue: categories, products, variants, images and "
        "customisation options. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow seeding when DEBUG is false. Use only for an explicitly disposable "
            "environment.",
        )
        parser.add_argument(
            "--assets-dir",
            default=str(DEFAULT_ASSETS_DIR),
            help="Directory holding products/<slug>.webp and categories/<slug>.webp.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to seed a non-debug environment without --force.")
        assets_dir = Path(options["assets_dir"])
        self.missing_required = []
        self.missing_optional = []
        with transaction.atomic():
            categories = self.seed_categories(assets_dir)
            products = self.seed_products(categories, assets_dir)
            self.retire_legacy_categories()
            self.seed_customizations(products)
        self.report(assets_dir, products)

    # Categories -----------------------------------------------------------------------------

    def seed_categories(self, assets_dir):
        categories = {}
        for slug, name, description, sort_order in seed_data.CATEGORIES:
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "sort_order": sort_order,
                    "is_active": True,
                    "parent": None,
                },
            )
            self.attach_category_image(category, assets_dir / "categories" / f"{slug}.webp")
            categories[slug] = category
        return categories

    def attach_category_image(self, category, path):
        if not path.is_file():
            self.missing_required.append(path)
            return
        if category.image and _same_file(category.image, path):
            return
        if category.image and Path(category.image.name).name.startswith(SEED_PREFIX):
            category.image.delete(save=False)
        with path.open("rb") as handle:
            category.image.save(f"{SEED_PREFIX}{category.slug}.webp", File(handle), save=True)

    def retire_legacy_categories(self):
        for category in Category.objects.filter(slug__in=seed_data.LEGACY_CATEGORY_SLUGS):
            if category.is_active and not category.products.exists():
                category.is_active = False
                category.save(update_fields=("is_active", "updated_at"))

    # Products -------------------------------------------------------------------------------

    def seed_products(self, categories, assets_dir):
        products = {}
        now = timezone.now()
        for spec in seed_data.PRODUCTS:
            smallest_name, smallest_price = spec["variants"][0]
            product, _ = Product.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "name": spec["name"],
                    "description": spec["description"],
                    "short_description": spec["short"],
                    "category": categories[spec["category"]],
                    "status": Product.PUBLISHED,
                    "is_available": True,
                    "is_featured": spec["featured"],
                    "base_price": smallest_price,
                    "currency": Product.CURRENCY,
                    "weight_description": smallest_name,
                    "preparation_time": spec["prep"],
                },
            )
            if product.published_at is None:
                product.published_at = now
                product.save(update_fields=("published_at", "updated_at"))
            self.seed_variants(product, spec)
            self.attach_product_images(product, spec, assets_dir / "products")
            products[spec["slug"]] = (product, spec)
        return products

    def seed_variants(self, product, spec):
        names = []
        for index, (name, price) in enumerate(spec["variants"], start=1):
            ProductVariant.objects.update_or_create(
                product=product,
                name=name,
                defaults={
                    "sku": f"LZ-{spec['sku']}-{index}",
                    "price": price,
                    "currency": Product.CURRENCY,
                    "is_active": True,
                    "sort_order": index,
                },
            )
            names.append(name)
        for variant in product.variants.exclude(name__in=names):
            if variant.cart_items.exists() or variant.orderitem_set.exists():
                if variant.is_active:
                    variant.is_active = False
                    variant.save(update_fields=("is_active", "updated_at"))
            else:
                variant.delete()

    def attach_product_images(self, product, spec, directory):
        slots = (
            (directory / f"{spec['slug']}.webp", True, 0, seed_data.image_alt_text(spec)),
            (
                directory / f"{spec['slug']}-2.webp",
                False,
                1,
                seed_data.image_alt_text(spec, second=True),
            ),
        )
        for path, is_primary, sort_order, alt_text in slots:
            if not path.is_file():
                (self.missing_required if is_primary else self.missing_optional).append(path)
                continue
            seeded = [
                image
                for image in product.images.filter(sort_order=sort_order)
                if Path(image.image.name).name.startswith(SEED_PREFIX)
            ]
            current = seeded[0] if seeded else None
            if current and _same_file(current.image, path):
                if is_primary and not current.is_primary:
                    product.images.filter(is_primary=True).update(is_primary=False)
                if current.alt_text != alt_text or current.is_primary != is_primary:
                    current.alt_text = alt_text
                    current.is_primary = is_primary
                    current.save(update_fields=("alt_text", "is_primary"))
                continue
            for image in seeded:
                image.image.delete(save=False)
                image.delete()
            if is_primary:
                product.images.filter(is_primary=True).update(is_primary=False)
            image = ProductImage(
                product=product, alt_text=alt_text, sort_order=sort_order, is_primary=is_primary
            )
            with path.open("rb") as handle:
                image.image.save(f"{SEED_PREFIX}{path.name}", File(handle), save=False)
            image.save()

    # Customisation --------------------------------------------------------------------------

    def seed_customizations(self, products):
        options, choices = {}, {}
        for slug, (
            name,
            input_type,
            description,
            sort_order,
            option_choices,
        ) in seed_data.OPTIONS.items():
            option, _ = CustomizationOption.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "input_type": input_type,
                    "description": description,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
            options[slug] = option
            for index, (choice_slug, choice_name) in enumerate(option_choices, start=1):
                choice, _ = CustomizationChoice.objects.update_or_create(
                    option=option,
                    slug=choice_slug,
                    defaults={"name": choice_name, "sort_order": index, "is_active": True},
                )
                choices[(slug, choice_slug)] = choice
        for product, spec in products.values():
            wanted = seed_data.product_customizations(spec)
            for option_slug, option in options.items():
                if option_slug not in wanted:
                    ProductCustomization.objects.filter(product=product, option=option).update(
                        is_active=False
                    )
                    continue
                required, minimum, maximum, prices = wanted[option_slug]
                config, _ = ProductCustomization.objects.update_or_create(
                    product=product,
                    option=option,
                    defaults={
                        "is_required": required,
                        "is_active": True,
                        "sort_order": option.sort_order,
                        "min_selections": minimum,
                        "max_selections": maximum,
                    },
                )
                for index, (choice_slug, price) in enumerate(prices.items(), start=1):
                    ProductCustomizationChoice.objects.update_or_create(
                        product_customization=config,
                        choice=choices[(option_slug, choice_slug)],
                        defaults={
                            "price_adjustment": price,
                            "currency": "INR",
                            "is_active": True,
                            "sort_order": index,
                        },
                    )

    # Output ---------------------------------------------------------------------------------

    def report(self, assets_dir, products):
        with_images = sum(1 for product, _ in products.values() if product.images.exists())
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(seed_data.CATEGORIES)} categories, {len(products)} products "
                f"({with_images} with images) and {len(seed_data.OPTIONS)} customisation options."
            )
        )
        if self.missing_required:
            listing = "\n".join(f"  - {path}" for path in self.missing_required)
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: {len(self.missing_required)} seed image(s) missing in "
                    f"{assets_dir}; those items have no photo:\n{listing}"
                )
            )
        if self.missing_optional:
            listing = "\n".join(f"  - {path}" for path in self.missing_optional)
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: {len(self.missing_optional)} optional second-angle image(s) "
                    f"missing:\n{listing}"
                )
            )
