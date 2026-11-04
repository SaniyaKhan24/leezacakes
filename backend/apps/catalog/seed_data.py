"""Demo catalogue for local development. Prices are in INR and GST-inclusive."""

from decimal import Decimal

SEED_ASSETS_DIR_NAME = "seed_assets"
LEGACY_CATEGORY_SLUGS = ("celebration-cakes", "chocolate-cakes", "fruit-cakes")

CATEGORIES = (
    ("signature", "Signature", "The cakes our regulars order again and again.", 1),
    ("chocolate", "Chocolate", "Dark, glossy, generous — for serious chocolate people.", 2),
    ("fruit-floral", "Fruit & Floral", "Seasonal fruit, fresh cream and petals.", 3),
    (
        "celebration",
        "Celebration & Tiered",
        "Tall, tiered centrepieces for weddings and milestones.",
        4,
    ),
    ("bento", "Bento & Petite", "Little lunchbox cakes for one or two.", 5),
)

STANDARD_SIZES = ("Half kilo · serves 4–6", "1 kg · serves 8–10", "1.5 kg · serves 12–15")


def _standard(*prices):
    return tuple(zip(STANDARD_SIZES, (Decimal(str(price)) for price in prices), strict=True))


PRODUCTS = (
    {
        "slug": "chocolate-truffle",
        "name": "Chocolate Truffle",
        "category": "chocolate",
        "featured": True,
        "prep": 1440,
        "sku": "CHT",
        "short": "Dark ganache, cocoa sponge, a little gold.",
        "description": (
            "Three layers of cocoa sponge brushed with vanilla syrup and filled with dark "
            "chocolate ganache that we whip by hand. The outside is poured glossy and finished "
            "with a few flecks of edible gold. It is the cake we bake most for birthdays, and "
            "it keeps beautifully overnight."
        ),
        "variants": _standard(850, 1550, 2250),
    },
    {
        "slug": "belgian-chocolate",
        "name": "Belgian Chocolate Drip",
        "category": "chocolate",
        "featured": True,
        "prep": 1440,
        "sku": "BEL",
        "short": "54% Belgian chocolate, poured warm.",
        "description": (
            "Moist chocolate sponge layered with a cream made from 54% Belgian couverture. We "
            "pour the drip while it is still warm, so every slice gets a bit of the glossy "
            "edge. Rich without being heavy, and a safe bet for a mixed crowd."
        ),
        "variants": _standard(950, 1750, 2550),
    },
    {
        "slug": "black-forest",
        "name": "Black Forest",
        "category": "chocolate",
        "featured": False,
        "prep": 1440,
        "sku": "BLF",
        "short": "Kirsch-free cherries, whipped cream, shavings.",
        "description": (
            "Chocolate sponge, softly whipped cream and dark cherries cooked down with lemon "
            "instead of kirsch, so the whole family can have a slice. Finished the "
            "old-fashioned way, with chocolate shavings pressed onto the sides."
        ),
        "variants": _standard(760, 1390, 1990),
    },
    {
        "slug": "red-velvet",
        "name": "Red Velvet",
        "category": "signature",
        "featured": True,
        "prep": 1440,
        "sku": "RV",
        "short": "Buttermilk crumb, cream cheese, velvet sides.",
        "description": (
            "A tender buttermilk crumb with a gentle cocoa note, layered with tangy cream "
            "cheese frosting that is not too sweet. We press red velvet crumbs onto the sides "
            "for that soft, velvety finish. Asked for at anniversaries and first birthdays alike."
        ),
        "variants": _standard(800, 1490, 2150),
    },
    {
        "slug": "butterscotch-crunch",
        "name": "Butterscotch Crunch",
        "category": "signature",
        "featured": False,
        "prep": 1440,
        "sku": "BSC",
        "short": "Burnt-sugar caramel and almond praline.",
        "description": (
            "Vanilla sponge brushed with caramel that we cook until it is deep amber. Between "
            "the layers sit whipped butterscotch cream and a crackly almond praline that stays "
            "crisp. Toasty, sweet, and the one children ask for by name."
        ),
        "variants": _standard(820, 1520, 2190),
    },
    {
        "slug": "rasmalai-tres-leches",
        "name": "Rasmalai Tres Leches",
        "category": "signature",
        "featured": True,
        "prep": 1440,
        "sku": "RTL",
        "short": "Saffron milk-soaked sponge, pistachio, rose.",
        "description": (
            "A soft sponge soaked overnight in saffron and cardamom milk, just like rasmalai. "
            "It is topped with lightly sweetened cream, chopped pistachio and a scatter of "
            "dried rose. Serve it chilled; it is especially good after a festive meal."
        ),
        "variants": _standard(990, 1850, 2690),
    },
    {
        "slug": "vanilla-berry",
        "name": "Vanilla Berry",
        "category": "fruit-floral",
        "featured": False,
        "prep": 1440,
        "sku": "VB",
        "short": "Vanilla bean, berry compote, softly whipped cream.",
        "description": (
            "Vanilla bean sponge layered with a tart mixed-berry compote and softly whipped "
            "cream. Light and not too sweet, topped with whichever berries look best at the "
            "market that week. A good choice for an afternoon party."
        ),
        "variants": _standard(780, 1450, 2090),
    },
    {
        "slug": "pistachio-rose",
        "name": "Pistachio Rose",
        "category": "fruit-floral",
        "featured": True,
        "prep": 1440,
        "sku": "PR",
        "short": "Pistachio sponge, rose cream, dried petals.",
        "description": (
            "A pistachio sponge made with plenty of ground nuts, so it stays moist and "
            "fragrant. Layered with a delicate rose cream and finished with dried petals and "
            "slivered pistachio. Pretty enough for an engagement, easy enough for a Sunday."
        ),
        "variants": _standard(1050, 1950, 2850),
    },
    {
        "slug": "mango-passionfruit",
        "name": "Alphonso Mango & Passionfruit",
        "category": "fruit-floral",
        "featured": False,
        "prep": 1440,
        "sku": "MP",
        "short": "Seasonal Alphonso, passionfruit curd.",
        "description": (
            "Vanilla sponge layered with ripe Alphonso mango, whipped cream and a sharp "
            "passionfruit curd that cuts through the sweetness. We make it while the mangoes "
            "are in season, and it tastes like the best part of summer."
        ),
        "variants": _standard(920, 1720, 2490),
    },
    {
        "slug": "lemon-blueberry",
        "name": "Lemon Blueberry",
        "category": "fruit-floral",
        "featured": False,
        "prep": 1440,
        "sku": "LB",
        "short": "Lemon curd, blueberry, Swiss meringue.",
        "description": (
            "Lemon sponge with a bright, buttery lemon curd and blueberries baked right in. It "
            "is covered in toasted Swiss meringue, so every slice has a soft, marshmallowy top. "
            "Fresh and zesty, and lovely with tea."
        ),
        "variants": _standard(880, 1640, 2390),
    },
    {
        "slug": "vanilla-bloom-two-tier",
        "name": "Vanilla Bloom, Two Tier",
        "category": "celebration",
        "featured": True,
        "prep": 2880,
        "sku": "VBT",
        "short": "Two tiers of vanilla, sugar flowers.",
        "description": (
            "Two tiers of vanilla bean sponge with Swiss meringue buttercream, smoothed to an "
            "ivory finish. Each cake is dressed with sugar flowers we shape by hand, so please "
            "order at least two days ahead. Made for weddings, naming ceremonies and big "
            "birthdays."
        ),
        "variants": (
            ("2 tiers · 2.5 kg · serves 25", Decimal("4800")),
            ("2 tiers · 3.5 kg · serves 35", Decimal("6600")),
        ),
    },
    {
        "slug": "gilded-three-tier",
        "name": "The Gilded Three Tier",
        "category": "celebration",
        "featured": False,
        "prep": 4320,
        "sku": "G3T",
        "short": "Three tiers, gold leaf, hand-piped pearls.",
        "description": (
            "Three tiers of vanilla and dark chocolate sponge, finished with gold leaf and "
            "rows of hand-piped sugar pearls. It takes us three days to build, so plan a "
            "little ahead. For the weddings and anniversaries people talk about afterwards."
        ),
        "variants": (
            ("3 tiers · 4 kg · serves 40", Decimal("8900")),
            ("3 tiers · 6 kg · serves 60", Decimal("12900")),
        ),
    },
    {
        "slug": "bento-hearts",
        "name": "Bento Hearts",
        "category": "bento",
        "featured": False,
        "prep": 360,
        "sku": "BH",
        "short": "A four-inch lunchbox cake with piped hearts.",
        "description": (
            "A four-inch vanilla cake in a little takeaway box, piped with hearts in pastel "
            "buttercream. Just right for two people, a desk surprise or no reason at all. Add "
            "a short message and we will pipe it on top."
        ),
        "variants": (("4 inch · serves 1–2", Decimal("450")),),
    },
    {
        "slug": "biscoff-bento",
        "name": "Biscoff Bento",
        "category": "bento",
        "featured": False,
        "prep": 360,
        "sku": "BB",
        "short": "Speculoos cream and cookie crumb, small and mighty.",
        "description": (
            "Brown-sugar sponge layered with Biscoff cream and topped with crushed speculoos "
            "crumb. It is small, but every bite tastes of caramelised spice. Comes in a "
            "lunchbox, ready to share (or not)."
        ),
        "variants": (("4 inch · serves 1–2", Decimal("490")),),
    },
)

# Customisation options: slug -> (name, input_type, description, sort_order, choices)
# where choices are (slug, name) tuples. Prices are set per product below.
OPTIONS = {
    "egg-preference": (
        "Egg preference",
        "single_choice",
        "Every cake can be baked eggless.",
        1,
        (("contains-egg", "Contains egg"), ("eggless", "Eggless")),
    ),
    "message-on-cake": (
        "Message on the cake",
        "text",
        "A short message piped on top. Around 32 characters fits neatly.",
        2,
        (),
    ),
    "finishing-touches": (
        "Finishing touches",
        "multiple_choice",
        "Choose up to three.",
        3,
        (
            ("fresh-flowers", "Fresh flowers"),
            ("gold-leaf", "Gold leaf"),
            ("macarons", "Macarons (4)"),
            ("chocolate-shards", "Chocolate shards"),
            ("happy-birthday-topper", "Happy Birthday topper"),
        ),
    ),
    "candles": (
        "Candles",
        "single_choice",
        "",
        4,
        (
            ("no-candles", "No candles"),
            ("number-candles", "Number candles"),
            ("sparkler-candles", "Sparkler candles"),
        ),
    ),
}

FINISHING_TOUCH_PRICES = {
    "fresh-flowers": Decimal("250"),
    "gold-leaf": Decimal("300"),
    "macarons": Decimal("240"),
    "chocolate-shards": Decimal("150"),
    "happy-birthday-topper": Decimal("120"),
}
CANDLE_PRICES = {
    "no-candles": Decimal("0"),
    "number-candles": Decimal("60"),
    "sparkler-candles": Decimal("90"),
}


def eggless_price(category_slug):
    if category_slug == "bento":
        return Decimal("40")
    if category_slug == "celebration":
        return Decimal("400")
    return Decimal("80")


def product_customizations(product_spec):
    """Return {option_slug: (is_required, min, max, {choice_slug: price})} for a product."""
    config = {
        "egg-preference": (
            True,
            1,
            1,
            {
                "contains-egg": Decimal("0"),
                "eggless": eggless_price(product_spec["category"]),
            },
        ),
        "message-on-cake": (False, None, None, {}),
        "candles": (False, None, 1, dict(CANDLE_PRICES)),
    }
    if product_spec["category"] != "bento":
        config["finishing-touches"] = (False, None, 3, dict(FINISHING_TOUCH_PRICES))
    return config


def image_alt_text(product_spec, second=False):
    if second:
        return f"{product_spec['name']} cake, seen from another angle"
    return f"{product_spec['name']} cake: {product_spec['short'].rstrip('.').lower()}"
