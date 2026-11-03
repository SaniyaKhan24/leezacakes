"""Turn transparent 3D cake renders into catalogue photographs.

The frontend renders each procedural cake with `frontend/scripts/render-cakes.mjs`
(transparent PNGs). This script places them on a soft studio backdrop in the
cake's own colour and writes:

* backend/apps/catalog/seed_assets/products/<slug>.webp and <slug>-2.webp
* backend/apps/catalog/seed_assets/categories/<category>.webp
* frontend/public/images/cakes/<slug>.webp          (transparent poster for the 3D stage)
* frontend/public/images/cakes/<slug>-studio.webp   (backdrop version for editorial pages)

Usage:  python scripts/compose_product_photos.py <renders-dir>
"""

import random
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
DESIGNS = ROOT / "frontend/src/components/cake/designs.ts"
SEED = ROOT / "backend/apps/catalog/seed_assets"
POSTERS = ROOT / "frontend/public/images/cakes"
CATEGORY_HEROES = {
    "signature": "red-velvet",
    "chocolate": "chocolate-truffle",
    "fruit-floral": "vanilla-berry",
    "celebration": "gilded-three-tier",
    "bento": "bento-hearts",
}


def backdrops():
    """Read each design's backdrop colour from the frontend art direction."""
    source = DESIGNS.read_text()
    found = {}
    starts = [(m.group(1), m.end()) for m in re.finditer(r'^  "([a-z0-9-]+)": \{$', source, re.M)]
    for slug, start in starts:
        match = re.compile(r'backdrop: "(#[0-9a-f]{6})"').search(source, start)
        if match:
            found[slug] = match.group(1)
    if not found:
        raise SystemExit(f"No backdrops found in {DESIGNS}")
    return found


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def studio(size, colour, seed):
    """A seamless paper sweep: lighter behind the cake, settling darker at the floor."""
    w, h = size
    base = hex_rgb(colour)
    light = mix(base, (255, 252, 247), 0.45)
    floor = mix(base, (60, 34, 24), 0.08)
    canvas = Image.new("RGB", size)
    draw = ImageDraw.Draw(canvas)
    for y in range(h):
        t = y / (h - 1)
        draw.line([(0, y), (w, y)], fill=mix(light, floor, t**1.6))
    glow = Image.new("L", size, 0)
    ImageDraw.Draw(glow).ellipse([w * 0.08, h * 0.12, w * 0.92, h * 0.78], fill=150)
    glow = glow.filter(ImageFilter.GaussianBlur(w * 0.16))
    canvas = Image.composite(Image.new("RGB", size, mix(base, (255, 255, 255), 0.6)), canvas, glow)
    # A whisper of film grain so the sweep reads as paper, not a flat fill.
    random.seed(seed)
    noise = Image.effect_noise(size, 18).point(lambda p: 128 + (p - 128) // 3).convert("RGB")
    return ImageChops.overlay(canvas, noise)


def compose(render: Path, colour: str, out: Path):
    cake = Image.open(render).convert("RGBA")
    photo = studio(cake.size, colour, render.name).convert("RGBA")
    photo.alpha_composite(cake)
    out.parent.mkdir(parents=True, exist_ok=True)
    photo.convert("RGB").save(out, "WEBP", quality=84, method=6)
    return photo


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    renders = Path(sys.argv[1])
    colours = backdrops()
    POSTERS.mkdir(parents=True, exist_ok=True)
    missing = []
    for slug, colour in colours.items():
        for suffix in ("", "-2"):
            render = renders / f"{slug}{suffix}.png"
            if not render.exists():
                missing.append(render.name)
                continue
            compose(render, colour, SEED / "products" / f"{slug}{suffix}.webp")
        primary = renders / f"{slug}.png"
        if primary.exists():
            poster = Image.open(primary).convert("RGBA")
            poster.thumbnail((800, 1000))
            poster.save(POSTERS / f"{slug}.webp", "WEBP", quality=82, method=6)
            studio_photo = compose(primary, colour, POSTERS / f"{slug}-studio.webp")
            studio_photo.convert("RGB").resize((800, 1000)).save(
                POSTERS / f"{slug}-studio.webp", "WEBP", quality=80, method=6
            )
    for category, slug in CATEGORY_HEROES.items():
        source = SEED / "products" / f"{slug}.webp"
        if source.exists():
            target = SEED / "categories" / f"{category}.webp"
            target.parent.mkdir(parents=True, exist_ok=True)
            Image.open(source).resize((640, 800)).save(target, "WEBP", quality=82, method=6)
    if missing:
        raise SystemExit(f"Missing renders: {', '.join(missing)}")
    print(f"Composed {len(colours)} cakes into {SEED} and {POSTERS}")


if __name__ == "__main__":
    main()
