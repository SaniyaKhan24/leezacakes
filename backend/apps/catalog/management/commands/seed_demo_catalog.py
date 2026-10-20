from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.catalog.models import Category, Product, ProductVariant


class Command(BaseCommand):
    help = "Seed the local development catalog with safe, image-free demo cakes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow seeding when DEBUG is false. Use only for an explicitly disposable environment.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to seed a non-debug environment without --force.")

        categories = {}
        for name, slug, description, sort_order in (
            ("Celebration Cakes", "celebration-cakes", "Cakes for birthdays and milestones.", 1),
            ("Chocolate Cakes", "chocolate-cakes", "Deep, rich chocolate favourites.", 2),
            ("Fruit Cakes", "fruit-cakes", "Light cakes finished with bright fruit.", 3),
        ):
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "description": description, "sort_order": sort_order, "is_active": True},
            )
            categories[slug] = category

        products = (
            ("Chocolate Truffle", "chocolate-truffle", "A dark cocoa sponge layered with silky chocolate truffle.", "Rich chocolate layers with a glossy finish.", "chocolate-cakes", "850.00", True),
            ("Belgian Chocolate", "belgian-chocolate", "Velvety Belgian chocolate cream over tender cocoa sponge.", "A refined chocolate celebration cake.", "chocolate-cakes", "950.00", True),
            ("Red Velvet", "red-velvet", "Soft red velvet sponge with a smooth cream cheese frosting.", "A timeless red velvet classic.", "celebration-cakes", "800.00", True),
            ("Vanilla Berry", "vanilla-berry", "Vanilla bean sponge, berry compote, and softly whipped cream.", "Light, floral, and finished with berries.", "fruit-cakes", "780.00", False),
            ("Butterscotch Crunch", "butterscotch-crunch", "Butterscotch cream, caramel drizzle, and delicate praline crunch.", "Golden caramel sweetness with a little crunch.", "celebration-cakes", "820.00", False),
            ("Black Forest", "black-forest", "Cocoa sponge with cherry compote and chocolate shavings.", "A nostalgic cherry and chocolate favourite.", "chocolate-cakes", "760.00", False),
        )
        for name, slug, description, short_description, category_slug, price, featured in products:
            product, _ = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "short_description": short_description,
                    "category": categories[category_slug],
                    "status": Product.PUBLISHED,
                    "is_available": True,
                    "is_featured": featured,
                    "base_price": price,
                    "currency": Product.CURRENCY,
                    "weight_description": "Serves 6–8",
                    "preparation_time": 1440,
                    "published_at": timezone.now(),
                },
            )
            ProductVariant.objects.update_or_create(
                product=product,
                name="6–8 servings",
                defaults={"price": price, "currency": Product.CURRENCY, "is_active": True, "sort_order": 1},
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(products)} development catalog products."))
