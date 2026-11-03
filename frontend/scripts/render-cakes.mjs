#!/usr/bin/env node
/**
 * Photographs every procedural cake for the catalogue.
 *
 * Usage (with `npm run dev` running):
 *   node scripts/render-cakes.mjs [--out ./renders] [--slugs a,b] [--base http://localhost:3000]
 *
 * Writes transparent PNGs: <slug>.png (hero angle), <slug>-2.png (slice lifted, three-quarter view).
 * `backend/scripts/compose_product_photos.py` turns them into the WebP catalogue photographs.
 */
import { access, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const args = Object.fromEntries(
  process.argv
    .slice(2)
    .reduce(
      (pairs, value, index, all) =>
        value.startsWith("--")
          ? [...pairs, [value.slice(2), all[index + 1]]]
          : pairs,
      [],
    ),
);
const base = args.base ?? "http://localhost:3000";
const out = path.resolve(args.out ?? "renders");
const ALL = [
  "chocolate-truffle",
  "belgian-chocolate",
  "black-forest",
  "red-velvet",
  "butterscotch-crunch",
  "rasmalai-tres-leches",
  "vanilla-berry",
  "pistachio-rose",
  "mango-passionfruit",
  "lemon-blueberry",
  "vanilla-bloom-two-tier",
  "gilded-three-tier",
  "bento-hearts",
  "biscoff-bento",
];
const slugs = args.slugs ? args.slugs.split(",") : ALL;
const width = Number(args.width ?? 1200);
const height = Number(args.height ?? 1500);

const shots = (slug) => {
  const tiered = slug.includes("tier");
  return [
    { file: `${slug}.png`, query: { slug, angle: -0.55, elevation: 0.34 } },
    {
      file: `${slug}-2.png`,
      query: tiered
        ? { slug, angle: 2.3, elevation: 0.5 }
        : { slug, angle: -0.35, elevation: 0.5, slice: 0.62 },
    },
  ];
};

await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  args: [
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--ignore-gpu-blocklist",
  ],
});
const page = await browser.newPage({
  viewport: { width, height },
  deviceScaleFactor: 1,
});
page.on("pageerror", (error) => console.error("page error:", error.message));
for (const slug of slugs) {
  for (const shot of shots(slug)) {
    const target = path.join(out, shot.file);
    if (
      !args.force &&
      (await access(target).then(
        () => true,
        () => false,
      ))
    ) {
      console.log("exists", shot.file);
      continue;
    }
    const query = new URLSearchParams(
      Object.entries(shot.query).map(([k, v]) => [k, String(v)]),
    );
    for (let attempt = 1; ; attempt += 1) {
      try {
        await page.goto(`${base}/studio/render?${query}`, {
          waitUntil: "load",
        });
        await page.waitForFunction(() => window.__cakeReady === true, null, {
          timeout: 180_000,
        });
        break;
      } catch (error) {
        if (attempt >= 3) throw error;
        console.warn(`retrying ${shot.file}: ${error.message}`);
      }
    }
    await page.screenshot({ path: target, omitBackground: true });
    console.log("rendered", shot.file);
  }
}
await browser.close();
