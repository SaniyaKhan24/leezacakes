import * as THREE from "three";
import type { CakeDesign } from "./designs";

/**
 * Procedural textures painted onto canvases at runtime. No image downloads,
 * so the 3D scenes stay light and every product can have its own crumb.
 */

const cache = new Map<string, THREE.Texture>();

export function rng(seed: number) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

export function seedOf(value: string) {
  let h = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    h ^= value.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function canvas(size: number) {
  const c = document.createElement("canvas");
  c.width = size;
  c.height = size;
  return c;
}

function shade(hex: string, amount: number) {
  const color = new THREE.Color(hex);
  const hsl = { h: 0, s: 0, l: 0 };
  color.getHSL(hsl);
  color.setHSL(hsl.h, hsl.s, Math.max(0, Math.min(1, hsl.l + amount)));
  return `#${color.getHexString()}`;
}

function finalize(texture: THREE.Texture, color: boolean) {
  if (color) texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  texture.needsUpdate = true;
  return texture;
}

function speckle(
  ctx: CanvasRenderingContext2D,
  size: number,
  random: () => number,
  colors: string[],
  count: number,
  maxRadius: number,
) {
  for (let i = 0; i < count; i += 1) {
    ctx.fillStyle = colors[Math.floor(random() * colors.length)];
    ctx.globalAlpha = 0.25 + random() * 0.5;
    ctx.beginPath();
    ctx.arc(
      random() * size,
      random() * size,
      0.4 + random() * maxRadius,
      0,
      Math.PI * 2,
    );
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

/** The inside of the cake: alternating sponge and cream, wrapped in frosting. */
export function crossSectionTexture(design: CakeDesign) {
  const key = `section:${design.slug}:${design.sponge}:${design.cream}:${design.frosting}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const size = 512;
  const c = canvas(size);
  const ctx = c.getContext("2d")!;
  const random = rng(seedOf(key));
  const coat = design.finish === "semi-naked" ? 0.012 : 0.05;
  const topCoat = 0.06;
  ctx.fillStyle = design.frosting;
  ctx.fillRect(0, 0, size, size);
  const inner = size * (1 - coat);
  const usable = size * (1 - topCoat);
  const creamShare = 0.28;
  const unit = usable / (design.layers + (design.layers - 1) * creamShare);
  let y = size;
  for (let i = 0; i < design.layers; i += 1) {
    const h = unit;
    const grad = ctx.createLinearGradient(0, y - h, 0, y);
    grad.addColorStop(0, shade(design.sponge, 0.04));
    grad.addColorStop(1, shade(design.sponge, -0.05));
    ctx.fillStyle = grad;
    ctx.fillRect(0, y - h, inner, h);
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, y - h, inner, h);
    ctx.clip();
    speckle(
      ctx,
      size,
      random,
      [shade(design.sponge, -0.14), shade(design.sponge, 0.1)],
      900,
      2.2,
    );
    ctx.restore();
    y -= h;
    if (i < design.layers - 1) {
      const ch = unit * creamShare;
      ctx.fillStyle = design.cream;
      ctx.beginPath();
      ctx.moveTo(0, y);
      for (let x = 0; x <= inner; x += 16)
        ctx.lineTo(x, y - ch + Math.sin(x * 0.05 + i) * 2.5);
      ctx.lineTo(inner, y);
      ctx.closePath();
      ctx.fill();
      ctx.fillRect(0, y - ch + 2, inner, ch - 2);
      y -= ch;
    }
  }
  return cache.set(key, finalize(new THREE.CanvasTexture(c), true)).get(key)!;
}

/** Side wrap for finishes that are not a clean coat of buttercream. */
export function sideTexture(design: CakeDesign, finish = design.finish) {
  const key = `side:${design.slug}:${finish}:${design.frosting}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const w = 1024;
  const h = 512;
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d")!;
  const random = rng(seedOf(key));
  if (finish === "semi-naked") {
    // Sponge bands showing through a scraped cream coat.
    ctx.fillStyle = design.cream;
    ctx.fillRect(0, 0, w, h);
    const bands = design.layers;
    for (let i = 0; i < bands; i += 1) {
      const y0 = h * 0.06 + (i * h * 0.92) / bands;
      const bh = (h * 0.92) / bands - 22;
      for (let x = 0; x < w; x += 3) {
        const exposure =
          0.35 +
          0.45 * Math.abs(Math.sin(x * 0.011 + i * 1.7)) +
          random() * 0.15;
        ctx.globalAlpha = Math.min(0.95, exposure);
        ctx.fillStyle =
          random() > 0.5 ? design.sponge : shade(design.sponge, -0.06);
        ctx.fillRect(x, y0 + random() * 4, 3, bh - random() * 6);
      }
    }
    ctx.globalAlpha = 1;
    speckle(ctx, w, random, [design.cream], 1800, 3);
  } else if (finish === "velvet") {
    ctx.fillStyle = design.frosting;
    ctx.fillRect(0, 0, w, h);
    speckle(
      ctx,
      w,
      random,
      [
        shade(design.frosting, -0.1),
        shade(design.frosting, 0.08),
        shade(design.frosting, -0.18),
      ],
      26000,
      2.6,
    );
  } else {
    ctx.fillStyle = design.frosting;
    ctx.fillRect(0, 0, w, h);
  }
  return cache.set(key, finalize(new THREE.CanvasTexture(c), true)).get(key)!;
}

/** Fine buttercream/ganache imperfection, used as a bump map. */
export function bumpTexture(
  kind: "buttercream" | "ridged" | "crumb" | "glossy",
) {
  const key = `bump:${kind}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const size = 512;
  const c = canvas(size);
  const ctx = c.getContext("2d")!;
  const random = rng(seedOf(key));
  ctx.fillStyle = "#808080";
  ctx.fillRect(0, 0, size, size);
  if (kind === "ridged") {
    for (let y = 0; y < size; y += 1) {
      const v = 128 + Math.sin((y / size) * Math.PI * 2 * 18) * 70;
      ctx.fillStyle = `rgb(${v},${v},${v})`;
      ctx.fillRect(0, y, size, 1);
    }
    speckle(ctx, size, random, ["#9a9a9a", "#6a6a6a"], 1600, 2);
  } else if (kind === "crumb") {
    speckle(ctx, size, random, ["#ffffff", "#000000", "#b0b0b0"], 16000, 2.4);
  } else {
    // Long soft palette-knife strokes.
    for (let i = 0; i < (kind === "glossy" ? 40 : 160); i += 1) {
      ctx.strokeStyle = random() > 0.5 ? "#909090" : "#707070";
      ctx.globalAlpha = 0.18;
      ctx.lineWidth = 4 + random() * 18;
      ctx.beginPath();
      const y = random() * size;
      ctx.moveTo(-20, y);
      ctx.bezierCurveTo(
        size * 0.3,
        y + random() * 20 - 10,
        size * 0.6,
        y + random() * 20 - 10,
        size + 20,
        y + random() * 16 - 8,
      );
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
  const texture = finalize(new THREE.CanvasTexture(c), false);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  return cache.set(key, texture).get(key)!;
}

/** Thin twisted stripes for the candles. */
export function candleTexture(color: string) {
  const key = `candle:${color}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const c = canvas(128);
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = "#fbf7f0";
  ctx.fillRect(0, 0, 128, 128);
  ctx.strokeStyle = color;
  ctx.lineWidth = 14;
  for (let i = -128; i < 256; i += 36) {
    ctx.beginPath();
    ctx.moveTo(i, 128);
    ctx.lineTo(i + 128, 0);
    ctx.stroke();
  }
  const texture = finalize(new THREE.CanvasTexture(c), true);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  return cache.set(key, texture).get(key)!;
}

/** Lemon wheel face. */
export function citrusTexture() {
  const key = "citrus";
  const hit = cache.get(key);
  if (hit) return hit;
  const s = 256;
  const c = canvas(s);
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = "#e9c63a";
  ctx.beginPath();
  ctx.arc(s / 2, s / 2, s / 2, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#fbf3cf";
  ctx.beginPath();
  ctx.arc(s / 2, s / 2, s / 2 - 10, 0, Math.PI * 2);
  ctx.fill();
  for (let i = 0; i < 9; i += 1) {
    const a0 = (i / 9) * Math.PI * 2 + 0.05;
    const a1 = ((i + 1) / 9) * Math.PI * 2 - 0.05;
    ctx.fillStyle = "#f4dd5e";
    ctx.beginPath();
    ctx.moveTo(s / 2, s / 2);
    ctx.arc(s / 2, s / 2, s / 2 - 18, a0, a1);
    ctx.closePath();
    ctx.fill();
  }
  return cache.set(key, finalize(new THREE.CanvasTexture(c), true)).get(key)!;
}
