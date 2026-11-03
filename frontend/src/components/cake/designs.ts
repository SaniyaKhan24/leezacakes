/**
 * Art direction for every cake in the catalogue.
 *
 * Each design is a recipe the procedural 3D renderer turns into geometry and
 * materials. The same recipe drives the live 3D views (hero, product turntable,
 * configurator) and the still photographs rendered for the product catalogue,
 * so what customers see on a card is exactly what they can spin on the page.
 */

export type Finish = "smooth" | "ridged" | "ganache" | "velvet" | "semi-naked";

export type ToppingKind =
  | "truffles"
  | "gilded-truffles"
  | "shards"
  | "gold-leaf"
  | "kisses"
  | "rosettes"
  | "cherries"
  | "shavings"
  | "crumbs"
  | "praline"
  | "pistachio"
  | "petals"
  | "saffron"
  | "strawberries"
  | "blueberries"
  | "mint"
  | "mango"
  | "lemon"
  | "flowers"
  | "hearts"
  | "cookies"
  | "macarons"
  | "pearls";

export type Topping = {
  kind: ToppingKind;
  color?: string;
  count?: number;
  ring?: number;
  tier?: number;
};

export type Tier = {
  radius: number;
  height: number;
  finish?: Finish;
  frosting?: string;
};

export type CakeDesign = {
  slug: string;
  tiers: Tier[];
  finish: Finish;
  frosting: string;
  /** Cross-section colours, revealed when a slice is lifted out. */
  sponge: string;
  cream: string;
  layers: number;
  drip?: { color: string; length?: number };
  glaze?: string;
  toppings: Topping[];
  pearls?: string;
  board: "stand" | "board" | "bento";
  boardColor: string;
  /** Gilded cake boards read as metal rather than card. */
  boardMetal?: boolean;
  /** Seamless studio backdrop used for catalogue photography. */
  backdrop: string;
  messageColor: string;
};

const single = (radius = 1, height = 0.92): Tier[] => [{ radius, height }];

export const CAKE_DESIGNS: Record<string, CakeDesign> = {
  "chocolate-truffle": {
    slug: "chocolate-truffle",
    tiers: single(1, 0.9),
    finish: "ganache",
    frosting: "#3a1f16",
    sponge: "#4a2a1d",
    cream: "#2b160f",
    layers: 4,
    toppings: [
      { kind: "truffles", count: 7, ring: 0.42 },
      { kind: "shards", count: 6, ring: 0.18 },
      { kind: "gold-leaf", count: 22 },
    ],
    board: "board",
    boardColor: "#c9a46a",
    boardMetal: true,
    backdrop: "#e7d5c1",
    messageColor: "#d8b47a",
  },
  "belgian-chocolate": {
    slug: "belgian-chocolate",
    tiers: single(1, 1.0),
    finish: "ridged",
    frosting: "#7b4b31",
    sponge: "#4d2b1d",
    cream: "#8a5a3e",
    layers: 4,
    drip: { color: "#2a140d", length: 1 },
    toppings: [
      { kind: "kisses", color: "#5a3322", count: 9, ring: 0.74 },
      { kind: "gilded-truffles", count: 5, ring: 0.74 },
      { kind: "shards", count: 4, ring: 0.12 },
    ],
    board: "board",
    boardColor: "#efe6d8",
    backdrop: "#d8c0a5",
    messageColor: "#f1dfc4",
  },
  "black-forest": {
    slug: "black-forest",
    tiers: single(1, 0.95),
    finish: "smooth",
    frosting: "#f7f0e6",
    sponge: "#3f2219",
    cream: "#f8f1e7",
    layers: 5,
    toppings: [
      { kind: "rosettes", color: "#fbf6ef", count: 12, ring: 0.78 },
      { kind: "cherries", count: 12, ring: 0.78 },
      { kind: "shavings", count: 70, ring: 0.5 },
    ],
    board: "board",
    boardColor: "#2f1b14",
    backdrop: "#e4cfc4",
    messageColor: "#4a2118",
  },
  "red-velvet": {
    slug: "red-velvet",
    tiers: single(1, 0.95),
    finish: "velvet",
    frosting: "#8f1d24",
    sponge: "#8b1c22",
    cream: "#f4ede1",
    layers: 5,
    glaze: "#f3ece1",
    toppings: [
      { kind: "kisses", color: "#f6efe4", count: 14, ring: 0.8 },
      { kind: "crumbs", color: "#8f1d24", count: 90, ring: 0.45 },
    ],
    board: "board",
    boardColor: "#efe6d8",
    backdrop: "#ead3cc",
    messageColor: "#8f1d24",
  },
  "butterscotch-crunch": {
    slug: "butterscotch-crunch",
    tiers: single(1, 0.92),
    finish: "smooth",
    frosting: "#ecc99a",
    sponge: "#e2b874",
    cream: "#f2dcb6",
    layers: 4,
    drip: { color: "#b5651f", length: 0.85 },
    toppings: [
      { kind: "kisses", color: "#f1d6ad", count: 10, ring: 0.74 },
      { kind: "praline", count: 26, ring: 0.36 },
    ],
    board: "board",
    boardColor: "#f3ebdf",
    backdrop: "#eedac0",
    messageColor: "#8a4a17",
  },
  "rasmalai-tres-leches": {
    slug: "rasmalai-tres-leches",
    tiers: single(1, 0.9),
    finish: "smooth",
    frosting: "#f3e2b8",
    sponge: "#f0d79c",
    cream: "#fbf1d8",
    layers: 4,
    toppings: [
      { kind: "kisses", color: "#f7ebcc", count: 12, ring: 0.8 },
      { kind: "pistachio", count: 120, ring: 0.5 },
      { kind: "petals", color: "#d9667a", count: 14, ring: 0.34 },
      { kind: "saffron", count: 18, ring: 0.5 },
    ],
    board: "board",
    boardColor: "#d1b071",
    boardMetal: true,
    backdrop: "#efe1c6",
    messageColor: "#b4542c",
  },
  "vanilla-berry": {
    slug: "vanilla-berry",
    tiers: single(1, 1.0),
    finish: "semi-naked",
    frosting: "#fbf6ee",
    sponge: "#e7c68c",
    cream: "#fbf5ea",
    layers: 4,
    toppings: [
      { kind: "strawberries", count: 9, ring: 0.42 },
      { kind: "blueberries", count: 14, ring: 0.5 },
      { kind: "mint", count: 5, ring: 0.3 },
    ],
    board: "stand",
    boardColor: "#f4efe8",
    backdrop: "#e8ddd3",
    messageColor: "#9b2c3d",
  },
  "pistachio-rose": {
    slug: "pistachio-rose",
    tiers: single(1, 0.95),
    finish: "smooth",
    frosting: "#d6dbb4",
    sponge: "#b9bf7d",
    cream: "#f2d9dc",
    layers: 4,
    toppings: [
      { kind: "pistachio", count: 140, ring: 0.82 },
      { kind: "petals", color: "#e48aa0", count: 18, ring: 0.42 },
      { kind: "petals", color: "#b8334f", count: 9, ring: 0.26 },
    ],
    board: "board",
    boardColor: "#f2ece3",
    backdrop: "#e7d7d4",
    messageColor: "#7b8a3c",
  },
  "mango-passionfruit": {
    slug: "mango-passionfruit",
    tiers: single(1, 0.9),
    finish: "smooth",
    frosting: "#f8e7bd",
    sponge: "#f1d49a",
    cream: "#f6b54a",
    layers: 4,
    glaze: "#f2a636",
    drip: { color: "#f0a12f", length: 0.6 },
    toppings: [
      { kind: "mango", count: 11, ring: 0.45 },
      { kind: "mint", count: 3, ring: 0.2 },
    ],
    board: "board",
    boardColor: "#f4ede2",
    backdrop: "#efdcbd",
    messageColor: "#f4e6c4",
  },
  "lemon-blueberry": {
    slug: "lemon-blueberry",
    tiers: single(1, 0.95),
    finish: "ridged",
    frosting: "#f7f1db",
    sponge: "#f1dc93",
    cream: "#f6e27a",
    layers: 4,
    toppings: [
      { kind: "kisses", color: "#f4e6c5", count: 11, ring: 0.76 },
      { kind: "blueberries", count: 16, ring: 0.42 },
      { kind: "lemon", count: 4, ring: 0.3 },
    ],
    board: "stand",
    boardColor: "#e9ecea",
    backdrop: "#e2e2d5",
    messageColor: "#3d4f8a",
  },
  "vanilla-bloom-two-tier": {
    slug: "vanilla-bloom-two-tier",
    tiers: [
      { radius: 1.1, height: 1.0 },
      { radius: 0.74, height: 0.86 },
    ],
    finish: "smooth",
    frosting: "#f8f3ec",
    sponge: "#ead09a",
    cream: "#fbf6ee",
    layers: 4,
    pearls: "#f3ece2",
    toppings: [
      { kind: "flowers", count: 5, tier: 0 },
      { kind: "flowers", count: 3, tier: 1 },
    ],
    board: "stand",
    boardColor: "#f4efe8",
    backdrop: "#e7dbd2",
    messageColor: "#b98572",
  },
  "gilded-three-tier": {
    slug: "gilded-three-tier",
    tiers: [
      { radius: 1.2, height: 0.95 },
      { radius: 0.88, height: 0.85, finish: "ridged" },
      { radius: 0.6, height: 0.78 },
    ],
    finish: "smooth",
    frosting: "#f6f0e4",
    sponge: "#ead09a",
    cream: "#fbf6ee",
    layers: 4,
    pearls: "#d8b46a",
    toppings: [
      { kind: "gold-leaf", count: 34, tier: 0 },
      { kind: "flowers", count: 3, tier: 2 },
      { kind: "flowers", count: 2, tier: 1 },
    ],
    board: "stand",
    boardColor: "#efe9df",
    backdrop: "#e2d4c2",
    messageColor: "#b08a45",
  },
  "bento-hearts": {
    slug: "bento-hearts",
    tiers: single(0.62, 0.58),
    finish: "smooth",
    frosting: "#f2cac4",
    sponge: "#f0d9a5",
    cream: "#fbf2ee",
    layers: 3,
    toppings: [
      { kind: "kisses", color: "#fbeee9", count: 16, ring: 0.86 },
      { kind: "hearts", color: "#c2364c", count: 3, ring: 0.2 },
    ],
    board: "bento",
    boardColor: "#c9a77c",
    backdrop: "#ead4cd",
    messageColor: "#c2364c",
  },
  "biscoff-bento": {
    slug: "biscoff-bento",
    tiers: single(0.62, 0.6),
    finish: "smooth",
    frosting: "#e9d1ab",
    sponge: "#d7a867",
    cream: "#ecd2a7",
    layers: 3,
    drip: { color: "#a35f27", length: 0.7 },
    toppings: [
      { kind: "cookies", count: 3, ring: 0.3 },
      { kind: "crumbs", color: "#a8662d", count: 40, ring: 0.5 },
    ],
    board: "bento",
    boardColor: "#c9a77c",
    backdrop: "#e7d5bd",
    messageColor: "#6b3a17",
  },
};

const FALLBACK_PALETTES = [
  {
    frosting: "#f6efe4",
    sponge: "#ead09a",
    cream: "#fbf6ee",
    backdrop: "#e8dcd1",
    accent: "#b98572",
  },
  {
    frosting: "#ead1bf",
    sponge: "#8a5a3e",
    cream: "#f2dcc8",
    backdrop: "#e6d4c3",
    accent: "#6d3b26",
  },
  {
    frosting: "#efd6d3",
    sponge: "#efd8a4",
    cream: "#fbf0ec",
    backdrop: "#ead6d0",
    accent: "#b23a52",
  },
];

function hash(value: string) {
  let h = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    h ^= value.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Products created later in the admin still get a tasteful, stable cake. */
export function designFor(slug: string): CakeDesign {
  const known = CAKE_DESIGNS[slug];
  if (known) return known;
  const palette = FALLBACK_PALETTES[hash(slug) % FALLBACK_PALETTES.length];
  return {
    slug,
    tiers: single(1, 0.92),
    finish: "smooth",
    frosting: palette.frosting,
    sponge: palette.sponge,
    cream: palette.cream,
    layers: 4,
    toppings: [
      { kind: "kisses", color: palette.cream, count: 12, ring: 0.78 },
      { kind: "flowers", count: 2, tier: 0 },
    ],
    board: "board",
    boardColor: "#efe6d8",
    backdrop: palette.backdrop,
    messageColor: palette.accent,
  };
}

/** Choices a customer makes in the configurator, translated into decoration. */
export type CakeExtras = {
  message?: string;
  touches?: string[];
  candles?: "none" | "number" | "sparkler";
  candleNumber?: string;
  scale?: number;
};

export function applyExtras(
  design: CakeDesign,
  extras: CakeExtras = {},
): CakeDesign {
  const touches = (extras.touches ?? []).map((value) => value.toLowerCase());
  const added: Topping[] = [];
  const top = design.tiers.length - 1;
  if (touches.some((t) => t.includes("flower")))
    added.push({ kind: "flowers", count: 2, tier: top });
  if (touches.some((t) => t.includes("gold")))
    added.push({ kind: "gold-leaf", count: 18, tier: top });
  if (touches.some((t) => t.includes("macaron")))
    added.push({ kind: "macarons", count: 4, ring: 0.55, tier: top });
  if (touches.some((t) => t.includes("shard")))
    added.push({ kind: "shards", count: 5, ring: 0.2, tier: top });
  return { ...design, toppings: [...design.toppings, ...added] };
}

export function hasBirthdayTopper(extras: CakeExtras = {}) {
  return (extras.touches ?? []).some((value) =>
    value.toLowerCase().includes("topper"),
  );
}
