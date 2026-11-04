"use client";

import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import { useLayoutEffect, useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";
import {
  applyExtras,
  hasBirthdayTopper,
  type CakeDesign,
  type CakeExtras,
  type ToppingKind,
} from "./designs";
import {
  boardGeometry,
  capGeometry,
  capsule,
  cookieGeometry,
  curlGeometry,
  flakeGeometry,
  heartGeometry,
  kissGeometry,
  leafGeometry,
  macaronGeometry,
  petalGeometry,
  roseGeometry,
  rosetteGeometry,
  roundedCube,
  shardGeometry,
  standGeometry,
  strawberryGeometry,
  tierGeometry,
} from "./geometry";
import {
  bumpTexture,
  candleTexture,
  citrusTexture,
  crossSectionTexture,
  rng,
  seedOf,
  sideTexture,
} from "./textures";

export const MESSAGE_FONT = "/fonts/cormorant-garamond-latin-500-italic.woff";

const SLICE = Math.PI / 4;
const SLICE_START = -SLICE / 2;

type Placement = {
  kind: ToppingKind | "drip";
  position: THREE.Vector3;
  rotation: THREE.Euler;
  scale: THREE.Vector3;
  color?: string;
  inSlice: boolean;
};

type Layout = {
  tierY: number[];
  baseHeight: number;
  placements: Placement[];
  top: { y: number; radius: number };
};

const SCATTER: ToppingKind[] = [
  "pistachio",
  "crumbs",
  "praline",
  "saffron",
  "shavings",
];

function inSliceAngle(angle: number) {
  const a = Math.atan2(Math.sin(angle), Math.cos(angle));
  return a > SLICE_START + 0.02 && a < SLICE_START + SLICE - 0.02;
}

function baseHeightFor(design: CakeDesign) {
  if (design.board === "stand") return 0.49;
  if (design.board === "bento") return 0.06;
  return 0.045;
}

function layout(
  design: CakeDesign,
  sliceEnabled: boolean,
  hasMessage: boolean,
): Layout {
  const random = rng(seedOf(design.slug));
  const baseHeight = baseHeightFor(design);
  const tierY: number[] = [];
  let y = baseHeight;
  for (const tier of design.tiers) {
    tierY.push(y);
    y += tier.height;
  }
  const placements: Placement[] = [];
  const topIndex = design.tiers.length - 1;
  const canSlice = sliceEnabled && design.tiers.length === 1;
  const add = (
    kind: Placement["kind"],
    position: THREE.Vector3,
    rotation: THREE.Euler,
    scale: number | THREE.Vector3,
    color?: string,
  ) => {
    const angle = Math.atan2(position.x, position.z);
    const radial = Math.hypot(position.x, position.z);
    placements.push({
      kind,
      position,
      rotation,
      scale:
        typeof scale === "number"
          ? new THREE.Vector3(scale, scale, scale)
          : scale,
      color,
      inSlice: canSlice && radial > 0.04 && inSliceAngle(angle),
    });
  };

  design.toppings.forEach((topping, index) => {
    const tierIndex = topping.tier ?? topIndex;
    const tier = design.tiers[tierIndex];
    const r = tier.radius;
    const topY = tierY[tierIndex] + tier.height;
    const count = topping.count ?? 8;
    const ring = topping.ring ?? 0.7;
    const phase = index * 0.37;
    const avoidFront = hasMessage && ring < 0.5 && tierIndex === topIndex;
    const angleFor = (k: number) => {
      if (ring >= 0.55)
        return (
          (k / count) * Math.PI * 2 +
          (["rosettes", "cherries"].includes(topping.kind) ? 0 : phase)
        );
      const base = random() * Math.PI * 2;
      return avoidFront ? Math.PI * 0.55 + random() * Math.PI * 0.9 : base;
    };
    const radiusFor = () =>
      ring >= 0.55
        ? ring * r * (1 + (random() - 0.5) * 0.04)
        : Math.sqrt(random()) * ring * r;
    const onTop = (angle: number, radius: number, lift: number) =>
      new THREE.Vector3(
        Math.sin(angle) * radius,
        topY + lift,
        Math.cos(angle) * radius,
      );

    if (SCATTER.includes(topping.kind)) {
      const sides = topping.kind === "shavings" ? count * 7 : 0;
      for (let k = 0; k < count; k += 1) {
        const angle = avoidFront
          ? Math.PI * 0.55 + random() * Math.PI * 0.9
          : random() * Math.PI * 2;
        const radius =
          ring >= 0.7
            ? (ring - 0.14 + random() * 0.2) * r
            : Math.sqrt(random()) * ring * r;
        const rot = new THREE.Euler(
          random() * Math.PI,
          random() * Math.PI,
          random() * Math.PI,
        );
        const size = 0.7 + random() * 0.7;
        const color =
          topping.kind === "pistachio"
            ? ["#8fae4b", "#a9bd5c", "#6f8f3a", "#c3cf7a"][
                Math.floor(random() * 4)
              ]
            : topping.kind === "praline"
              ? ["#c47a2c", "#d99a4e", "#a85f1f"][Math.floor(random() * 3)]
              : topping.kind === "saffron"
                ? "#c2341a"
                : topping.color;
        add(
          topping.kind,
          onTop(angle, Math.min(radius, r - 0.06), 0.012),
          rot,
          size,
          color,
        );
      }
      for (let k = 0; k < sides; k += 1) {
        const angle = random() * Math.PI * 2;
        const h =
          tierY[tierIndex] +
          0.03 +
          Math.pow(random(), 1.4) * (tier.height * 0.6);
        const pos = new THREE.Vector3(
          Math.sin(angle) * (r + 0.012),
          h,
          Math.cos(angle) * (r + 0.012),
        );
        add(
          topping.kind,
          pos,
          new THREE.Euler(random() * 3, angle, random() * 3),
          0.9 + random() * 0.6,
        );
      }
      return;
    }

    if (topping.kind === "gold-leaf") {
      for (let k = 0; k < count; k += 1) {
        const angle = random() * Math.PI * 2;
        const onSide = random() > 0.25;
        if (onSide) {
          const h = tierY[tierIndex] + 0.08 + random() * (tier.height - 0.2);
          const pos = new THREE.Vector3(
            Math.sin(angle) * (r + 0.003),
            h,
            Math.cos(angle) * (r + 0.003),
          );
          add(
            "gold-leaf",
            pos,
            new THREE.Euler(0, angle, random() * Math.PI),
            0.7 + random() * 0.9,
          );
        } else {
          add(
            "gold-leaf",
            onTop(angle, Math.sqrt(random()) * r * 0.85, 0.006),
            new THREE.Euler(-Math.PI / 2, 0, random() * Math.PI),
            0.6 + random() * 0.6,
          );
        }
      }
      return;
    }

    if (topping.kind === "flowers") {
      // A loose cascade of sugar roses sitting on the front-left shoulder.
      const centre = -0.65 + tierIndex * 1.4;
      for (let k = 0; k < count; k += 1) {
        const angle =
          centre + (k - (count - 1) / 2) * (0.42 / r) + (random() - 0.5) * 0.08;
        const radius = r * (0.84 + random() * 0.08);
        const lift = k % 2 === 0 ? 0.0 : -0.06;
        const pos = onTop(angle, radius, lift);
        const palette = ["#f7ebe4", "#efc8c1", "#e2a5a2", "#fbf5ef", "#d98b8f"];
        add(
          "flowers",
          pos,
          new THREE.Euler(
            0.35,
            angle + random(),
            0.25 * (random() - 0.5),
            "YXZ",
          ),
          1.9 + random() * 0.7,
          palette[Math.floor(random() * palette.length)],
        );
        if (k % 2 === 0) {
          const leafAngle = angle + 0.16;
          add(
            "mint",
            onTop(leafAngle, radius + 0.04, -0.01),
            new THREE.Euler(-1.1, leafAngle, 0),
            1.2,
            "#7d9465",
          );
        }
      }
      return;
    }

    for (let k = 0; k < count; k += 1) {
      const angle = angleFor(k);
      const radius = radiusFor();
      const jitter = () => (random() - 0.5) * 0.3;
      switch (topping.kind) {
        case "kisses":
          add(
            "kisses",
            onTop(angle, radius, -0.006),
            new THREE.Euler(0, random() * 6, 0),
            1,
            topping.color,
          );
          break;
        case "rosettes":
          add(
            "rosettes",
            onTop(angle, radius, -0.006),
            new THREE.Euler(0, random() * 6, 0),
            1,
            topping.color,
          );
          break;
        case "cherries":
          add(
            "cherries",
            onTop(angle, radius, 0.16),
            new THREE.Euler(jitter(), random() * 6, jitter()),
            1,
          );
          break;
        case "truffles":
          add(
            "truffles",
            onTop(angle, radius, 0.055),
            new THREE.Euler(random(), random(), random()),
            0.85 + random() * 0.35,
          );
          break;
        case "gilded-truffles":
          add(
            "gilded-truffles",
            onTop(angle, radius, 0.06),
            new THREE.Euler(random(), random(), random()),
            0.8 + random() * 0.25,
          );
          break;
        case "shards":
          add(
            "shards",
            onTop(angle, radius, -0.03),
            new THREE.Euler(jitter() * 1.2, random() * 6, jitter() * 1.2),
            0.8 + random() * 0.5,
          );
          break;
        case "strawberries":
          add(
            "strawberries",
            onTop(angle, radius, 0.075),
            new THREE.Euler(Math.PI + jitter() * 2, random() * 6, jitter() * 2),
            0.9 + random() * 0.3,
          );
          break;
        case "blueberries":
          add(
            "blueberries",
            onTop(angle, radius, 0.04 + random() * 0.05),
            new THREE.Euler(random(), random(), random()),
            0.85 + random() * 0.3,
          );
          break;
        case "mint":
          add(
            "mint",
            onTop(angle, radius, 0.12),
            new THREE.Euler(-1 + jitter(), random() * 6, jitter()),
            1.3,
            "#5d8c45",
          );
          break;
        case "mango":
          add(
            "mango",
            onTop(angle, radius, 0.06 + random() * 0.03),
            new THREE.Euler(random(), random(), random()),
            0.9 + random() * 0.3,
          );
          break;
        case "lemon":
          add(
            "lemon",
            onTop(angle, radius, 0.1),
            new THREE.Euler(
              Math.PI / 2 - 0.5 + jitter(),
              random() * 6,
              0,
              "YXZ",
            ),
            1,
          );
          break;
        case "petals":
          add(
            "petals",
            onTop(angle, radius, 0.012 + random() * 0.01),
            new THREE.Euler(
              -Math.PI / 2 + jitter() * 0.6,
              random() * 6,
              0,
              "YXZ",
            ),
            1.4 + random() * 0.6,
            topping.color,
          );
          break;
        case "hearts":
          add(
            "hearts",
            onTop((k / count) * Math.PI * 2 + 0.4, ring * r + 0.05, 0.015),
            new THREE.Euler(
              0,
              (k / count) * Math.PI * 2 + 0.4 + Math.PI + jitter(),
              0,
            ),
            1.5,
            topping.color,
          );
          break;
        case "cookies":
          add(
            "cookies",
            onTop(angle, radius, 0.08),
            new THREE.Euler(-0.35 + jitter(), angle + jitter(), jitter()),
            1,
          );
          break;
        case "macarons":
          add(
            "macarons",
            onTop(angle, radius, 0.075),
            new THREE.Euler(-1.15, angle, 0, "YXZ"),
            1,
            ["#e7b7bd", "#c9d7a8", "#f1d9a8", "#cbb7d9"][k % 4],
          );
          break;
        default:
          break;
      }
    }
  });

  if (design.pearls) {
    design.tiers.forEach((tier, i) => {
      const n = Math.floor((Math.PI * 2 * tier.radius) / 0.062);
      for (let k = 0; k < n; k += 1) {
        const a = (k / n) * Math.PI * 2;
        add(
          "pearls",
          new THREE.Vector3(
            Math.sin(a) * (tier.radius + 0.014),
            tierY[i] + 0.032,
            Math.cos(a) * (tier.radius + 0.014),
          ),
          new THREE.Euler(),
          1,
          design.pearls,
        );
      }
    });
  }

  if (design.drip) {
    const tier = design.tiers[topIndex];
    const topY = tierY[topIndex] + tier.height;
    const n = Math.round(tier.radius * 30);
    for (let k = 0; k < n; k += 1) {
      const a = (k / n) * Math.PI * 2 + (random() - 0.5) * 0.08;
      const stretch =
        (0.5 + Math.pow(random(), 1.6) * 2.3) *
        (design.drip.length ?? 1) *
        (tier.height / 0.95);
      const len = 0.2 * stretch;
      placements.push({
        kind: "drip",
        position: new THREE.Vector3(
          Math.sin(a) * (tier.radius + 0.006),
          topY - 0.035 - len / 2,
          Math.cos(a) * (tier.radius + 0.006),
        ),
        rotation: new THREE.Euler(),
        scale: new THREE.Vector3(1, stretch, 0.8),
        color: design.drip.color,
        inSlice: canSlice && inSliceAngle(a),
      });
    }
  }

  const top = design.tiers[topIndex];
  return {
    tierY,
    baseHeight,
    placements,
    top: { y: tierY[topIndex] + top.height, radius: top.radius },
  };
}

const materialCache = new Map<string, THREE.Material>();
function material(key: string, make: () => THREE.Material) {
  const hit = materialCache.get(key);
  if (hit) return hit;
  const m = make();
  materialCache.set(key, m);
  return m;
}

function frostingMaterial(
  design: CakeDesign,
  finish = design.finish,
  color = design.frosting,
) {
  return material(`frost:${design.slug}:${finish}:${color}`, () => {
    if (finish === "ganache") {
      return new THREE.MeshPhysicalMaterial({
        color,
        roughness: 0.2,
        clearcoat: 0.9,
        clearcoatRoughness: 0.12,
        bumpMap: bumpTexture("glossy"),
        bumpScale: 0.6,
      });
    }
    if (finish === "velvet") {
      return new THREE.MeshPhysicalMaterial({
        map: sideTexture(design, "velvet"),
        roughness: 0.96,
        bumpMap: bumpTexture("crumb"),
        bumpScale: 2.2,
        sheen: 0.4,
        sheenColor: new THREE.Color("#ffb3a8"),
      });
    }
    if (finish === "semi-naked") {
      return new THREE.MeshPhysicalMaterial({
        map: sideTexture(design, "semi-naked"),
        roughness: 0.72,
        bumpMap: bumpTexture("buttercream"),
        bumpScale: 1.4,
        sheen: 0.3,
        sheenColor: new THREE.Color("#fff6e8"),
      });
    }
    if (finish === "ridged") {
      const bump = bumpTexture("ridged").clone();
      bump.repeat.set(1, 1);
      bump.needsUpdate = true;
      return new THREE.MeshPhysicalMaterial({
        color,
        roughness: 0.55,
        bumpMap: bump,
        bumpScale: 3.2,
        sheen: 0.45,
        sheenColor: new THREE.Color("#fff8ee"),
      });
    }
    return new THREE.MeshPhysicalMaterial({
      color,
      roughness: 0.6,
      bumpMap: bumpTexture("buttercream"),
      bumpScale: 1.1,
      sheen: 0.5,
      sheenRoughness: 0.6,
      sheenColor: new THREE.Color("#fffaf2"),
    });
  });
}

function glossMaterial(color: string) {
  return material(
    `gloss:${color}`,
    () =>
      new THREE.MeshPhysicalMaterial({
        color,
        roughness: 0.14,
        clearcoat: 1,
        clearcoatRoughness: 0.08,
        bumpMap: bumpTexture("glossy"),
        bumpScale: 0.4,
      }),
  );
}

function toppingMaterial(kind: Placement["kind"]): THREE.Material {
  switch (kind) {
    case "truffles":
      return material(
        kind,
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#3a1f15",
            roughness: 0.95,
            bumpMap: bumpTexture("crumb"),
            bumpScale: 3,
          }),
      );
    case "gilded-truffles":
    case "gold-leaf":
      return material(
        "gold",
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#d4ac5e",
            metalness: 1,
            roughness: 0.28,
            side: THREE.DoubleSide,
            bumpMap: bumpTexture("crumb"),
            bumpScale: 0.6,
          }),
      );
    case "shards":
    case "shavings":
      return material(
        "choc",
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#2c160e",
            roughness: 0.3,
            clearcoat: 0.6,
            clearcoatRoughness: 0.3,
          }),
      );
    case "cherries":
      return material(
        kind,
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#6d0a14",
            roughness: 0.12,
            clearcoat: 1,
            clearcoatRoughness: 0.05,
          }),
      );
    case "strawberries":
      return material(
        kind,
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#c11f2d",
            roughness: 0.22,
            clearcoat: 1,
            clearcoatRoughness: 0.1,
            bumpMap: bumpTexture("crumb"),
            bumpScale: 1.2,
          }),
      );
    case "blueberries":
      return material(
        kind,
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#2c355a",
            roughness: 0.55,
            sheen: 1,
            sheenColor: new THREE.Color("#a4b0d6"),
            sheenRoughness: 0.4,
          }),
      );
    case "mango":
      return material(
        kind,
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#f4a21f",
            roughness: 0.18,
            clearcoat: 1,
            transmission: 0.15,
            thickness: 0.2,
          }),
      );
    case "lemon":
      return material(
        kind,
        () =>
          new THREE.MeshPhysicalMaterial({
            map: citrusTexture(),
            roughness: 0.3,
            clearcoat: 0.8,
          }),
      );
    case "cookies":
      return material(
        kind,
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#b0682d",
            roughness: 0.85,
            bumpMap: bumpTexture("crumb"),
            bumpScale: 2.5,
          }),
      );
    case "drip":
      return material(
        "drip",
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#ffffff",
            roughness: 0.14,
            clearcoat: 1,
            clearcoatRoughness: 0.08,
          }),
      );
    case "pearls":
      return material(
        "pearls",
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#ffffff",
            roughness: 0.25,
            metalness: 0.35,
            sheen: 1,
            sheenColor: new THREE.Color("#ffffff"),
            iridescence: 0.4,
          }),
      );
    case "kisses":
    case "rosettes":
      return material(
        "piped",
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#ffffff",
            roughness: 0.58,
            sheen: 0.6,
            sheenColor: new THREE.Color("#fffaf0"),
          }),
      );
    case "flowers":
    case "petals":
    case "mint":
      return material(
        "petal",
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#ffffff",
            roughness: 0.62,
            side: THREE.DoubleSide,
            sheen: 0.8,
            sheenColor: new THREE.Color("#ffffff"),
          }),
      );
    case "macarons":
      return material(
        kind,
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#ffffff",
            roughness: 0.5,
            bumpMap: bumpTexture("crumb"),
            bumpScale: 0.6,
          }),
      );
    case "hearts":
      return material(
        kind,
        () =>
          new THREE.MeshPhysicalMaterial({
            color: "#ffffff",
            roughness: 0.35,
            clearcoat: 0.6,
          }),
      );
    default:
      return material(
        "bits",
        () =>
          new THREE.MeshPhysicalMaterial({ color: "#ffffff", roughness: 0.6 }),
      );
  }
}

function toppingGeometry(
  kind: Placement["kind"],
  index: number,
): THREE.BufferGeometry {
  switch (kind) {
    case "kisses":
      return kissGeometry();
    case "rosettes":
      return rosetteGeometry();
    case "truffles":
      return memoSphere(0.068);
    case "gilded-truffles":
      return memoSphere(0.062);
    case "cherries":
      return memoSphere(0.058);
    case "blueberries":
      return memoSphere(0.042);
    case "pearls":
      return memoSphere(0.026);
    case "shards":
      return shardGeometry(index % 3);
    case "gold-leaf":
      return flakeGeometry();
    case "shavings":
      return curlGeometry();
    case "crumbs":
    case "pistachio":
    case "praline":
      return roundedCube(kind === "praline" ? 0.04 : 0.024);
    case "saffron":
      return capsule(0.0035, 0.06);
    case "strawberries":
      return strawberryGeometry();
    case "mint":
      return leafGeometry();
    case "mango":
      return roundedCube(0.1);
    case "lemon":
      return memoCylinder();
    case "petals":
      return petalGeometry(0.1, 0.12, 0.03);
    case "flowers":
      return roseGeometry();
    case "hearts":
      return heartGeometry();
    case "cookies":
      return cookieGeometry();
    case "macarons":
      return macaronGeometry();
    case "drip":
      return capsule(0.034, 0.2);
    default:
      return memoSphere(0.05);
  }
}

const spheres = new Map<number, THREE.BufferGeometry>();
function memoSphere(radius: number) {
  if (!spheres.has(radius))
    spheres.set(radius, new THREE.SphereGeometry(radius, 24, 16));
  return spheres.get(radius)!;
}
let lemonGeometry: THREE.BufferGeometry | null = null;
function memoCylinder() {
  if (!lemonGeometry)
    lemonGeometry = new THREE.CylinderGeometry(0.11, 0.11, 0.022, 40);
  return lemonGeometry;
}

/** One instanced mesh per topping kind keeps even the busiest cake to a few draw calls. */
function Instanced({
  kind,
  items,
  variant,
}: {
  kind: Placement["kind"];
  items: Placement[];
  variant: number;
}) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const geometry = toppingGeometry(kind, variant);
  const mat = toppingMaterial(kind);
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const color = new THREE.Color();
    items.forEach((item, i) => {
      q.setFromEuler(item.rotation);
      m.compose(item.position, q, item.scale);
      mesh.setMatrixAt(i, m);
      if (item.color) mesh.setColorAt(i, color.set(item.color));
      else if (mesh.instanceColor) mesh.setColorAt(i, color.set("#ffffff"));
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.computeBoundingSphere();
  }, [items]);
  return (
    <instancedMesh
      ref={ref}
      args={[geometry, mat, items.length]}
      castShadow
      receiveShadow
      frustumCulled={false}
    />
  );
}

function Toppings({ placements }: { placements: Placement[] }) {
  const groups = useMemo(() => {
    const map = new Map<string, Placement[]>();
    placements.forEach((p, i) => {
      const variant = p.kind === "shards" ? i % 3 : 0;
      const key = `${p.kind}:${variant}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(p);
    });
    return [...map.entries()];
  }, [placements]);
  return (
    <>
      {groups.map(([key, items]) => {
        const [kind, variant] = key.split(":");
        return (
          <Instanced
            key={key}
            kind={kind as Placement["kind"]}
            items={items}
            variant={Number(variant)}
          />
        );
      })}
    </>
  );
}

function glazeProfile(radius: number) {
  const pts = [new THREE.Vector2(0.0001, 0.022)];
  const steps = 10;
  for (let i = 0; i <= steps; i += 1) {
    const a = (i / steps) * (Math.PI / 2);
    pts.push(
      new THREE.Vector2(
        radius - 0.05 + Math.sin(a) * 0.062,
        -0.04 + Math.cos(a) * 0.062,
      ),
    );
  }
  pts.push(new THREE.Vector2(radius + 0.008, -0.07));
  pts.push(new THREE.Vector2(radius - 0.004, -0.075));
  // Lathe faces point outward only when the profile runs bottom-to-top.
  return pts.reverse();
}

function Glaze({
  radius,
  y,
  color,
  phiStart,
  phiLength,
}: {
  radius: number;
  y: number;
  color: string;
  phiStart: number;
  phiLength: number;
}) {
  const geometry = useMemo(() => {
    const g = new THREE.LatheGeometry(
      glazeProfile(radius),
      Math.max(12, Math.round((phiLength / (Math.PI * 2)) * 128)),
      phiStart,
      phiLength,
    );
    g.computeVertexNormals();
    return g;
  }, [radius, phiStart, phiLength]);
  return (
    <mesh
      geometry={geometry}
      material={glossMaterial(color)}
      position={[0, y, 0]}
      castShadow
      receiveShadow
    />
  );
}

function Cap({
  design,
  radius,
  height,
  phi,
}: {
  design: CakeDesign;
  radius: number;
  height: number;
  phi: number;
}) {
  const mat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        map: crossSectionTexture(design),
        roughness: 0.92,
        side: THREE.DoubleSide,
      }),
    [design],
  );
  return (
    <mesh
      geometry={capGeometry(radius, height)}
      material={mat}
      rotation={[0, phi - Math.PI / 2, 0]}
      receiveShadow
    />
  );
}

function Candles({
  kind,
  top,
}: {
  kind: "number" | "sparkler";
  top: { y: number; radius: number };
}) {
  const flames = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    flames.current?.children.forEach((child, i) => {
      const t = clock.elapsedTime * 9 + i * 1.7;
      child.scale.set(
        1 + Math.sin(t) * 0.08,
        1 + Math.sin(t * 1.3) * 0.18,
        1 + Math.cos(t) * 0.08,
      );
    });
  });
  const spots = kind === "number" ? [-0.12, 0.12] : [-0.22, 0, 0.22];
  const height = kind === "number" ? 0.34 : 0.55;
  const width = kind === "number" ? 0.035 : 0.012;
  const stripe = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        map: candleTexture(kind === "number" ? "#c9a14f" : "#b98572"),
        roughness: 0.4,
      }),
    [kind],
  );
  return (
    <group position={[0, top.y, -top.radius * 0.28]}>
      {spots.map((x) => (
        <mesh
          key={x}
          position={[x, height / 2, 0]}
          material={stripe}
          castShadow
        >
          <cylinderGeometry args={[width, width, height, 16]} />
        </mesh>
      ))}
      <group ref={flames}>
        {spots.map((x) => (
          <mesh key={x} position={[x, height + 0.05, 0]}>
            <sphereGeometry args={[0.025, 12, 12]} />
            <meshBasicMaterial
              color={kind === "sparkler" ? "#fff2c4" : "#ffb859"}
              toneMapped={false}
            />
          </mesh>
        ))}
      </group>
      <pointLight
        position={[0, height + 0.12, 0]}
        intensity={0.7}
        distance={1.6}
        color="#ffbe73"
      />
    </group>
  );
}

function Base({ design, radius }: { design: CakeDesign; radius: number }) {
  const mat = useMemo(() => {
    if (design.board === "bento") {
      return new THREE.MeshPhysicalMaterial({
        color: design.boardColor,
        roughness: 0.95,
        bumpMap: bumpTexture("crumb"),
        bumpScale: 1.5,
      });
    }
    if (design.boardMetal)
      return new THREE.MeshPhysicalMaterial({
        color: design.boardColor,
        metalness: 0.9,
        roughness: 0.32,
      });
    return new THREE.MeshPhysicalMaterial({
      color: design.boardColor,
      roughness: 0.22,
      clearcoat: 0.7,
      clearcoatRoughness: 0.2,
      sheen: 0.2,
    });
  }, [design]);
  if (design.board === "stand")
    return (
      <mesh
        geometry={standGeometry(radius + 0.42)}
        material={mat}
        castShadow
        receiveShadow
      />
    );
  if (design.board === "bento") {
    const size = radius * 2 + 0.34;
    return (
      <group>
        <mesh material={mat} position={[0, 0.03, 0]} castShadow receiveShadow>
          <boxGeometry args={[size, 0.06, size]} />
        </mesh>
        <mesh
          material={mat}
          position={[0, 0.04 + size * 0.24, -size / 2 - 0.16]}
          rotation={[-0.62, 0, 0]}
          castShadow
          receiveShadow
        >
          <boxGeometry args={[size, size * 0.55, 0.03]} />
        </mesh>
      </group>
    );
  }
  return (
    <mesh
      geometry={boardGeometry(radius + 0.24)}
      material={mat}
      castShadow
      receiveShadow
    />
  );
}

export type CakeModelProps = {
  design: CakeDesign;
  extras?: CakeExtras;
  /** 0 = closed, 1 = slice fully lifted out. Read every frame, so pass a ref for animation. */
  slice?: MutableRefObject<number>;
  /** Jump straight to the slice position instead of easing (used for still photography). */
  sliceImmediate?: boolean;
  /**
   * 0 = an empty board, 1 = the finished cake. Tiers drop into place one by one,
   * then the decorations settle on top. Read every frame; drive it from scroll.
   */
  assembly?: MutableRefObject<number>;
};

const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
const easeOut = (t: number) => 1 - Math.pow(1 - clamp01(t), 3);
/** A soft landing with the smallest overshoot, like a tier being set down by hand. */
const settle = (t: number) => {
  const x = clamp01(t);
  const c = 1.25;
  return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2);
};

export function CakeModel({
  design: baseDesign,
  extras,
  slice,
  sliceImmediate = false,
  assembly,
}: CakeModelProps) {
  const design = useMemo(
    () => applyExtras(baseDesign, extras),
    [baseDesign, extras],
  );
  const message = extras?.message?.trim() ?? "";
  const sliceEnabled = Boolean(slice);
  const plan = useMemo(
    () => layout(design, sliceEnabled, Boolean(message)),
    [design, sliceEnabled, message],
  );
  const canSlice = sliceEnabled && design.tiers.length === 1;
  const sliceGroup = useRef<THREE.Group>(null);
  const caps = useRef<THREE.Group>(null);
  const current = useRef(0);
  const baseGroup = useRef<THREE.Group>(null);
  const tierGroups = useRef<(THREE.Group | null)[]>([]);
  const decor = useRef<THREE.Group>(null);
  const built = useRef(assembly ? assembly.current : 1);

  useFrame((_, delta) => {
    if (!assembly) return;
    built.current = THREE.MathUtils.damp(
      built.current,
      assembly.current,
      6,
      delta,
    );
    const p = built.current;
    const n = design.tiers.length;
    const span = 0.62 / n;
    if (baseGroup.current) {
      const b = easeOut(p / 0.1);
      baseGroup.current.scale.set(0.6 + 0.4 * b, b || 0.0001, 0.6 + 0.4 * b);
      baseGroup.current.visible = b > 0.001;
    }
    tierGroups.current.forEach((group, i) => {
      if (!group) return;
      const start = 0.1 + i * span;
      const t = settle((p - start) / span);
      group.position.y = plan.tierY[i] + (1 - t) * 3.4;
      group.rotation.y = (1 - t) * 1.6;
      group.visible = p > start;
    });
    if (decor.current) {
      const t = settle((p - 0.76) / 0.2);
      decor.current.position.y = (1 - t) * 1.4;
      decor.current.visible = p > 0.76;
    }
  });

  useFrame((_, delta) => {
    if (!canSlice || !sliceGroup.current || !slice) return;
    current.current = sliceImmediate
      ? slice.current
      : THREE.MathUtils.damp(current.current, slice.current, 5, delta);
    const t = current.current;
    const reach = design.tiers[0].radius;
    sliceGroup.current.position.set(0, t * 0.18 * reach, t * 1.05 * reach);
    sliceGroup.current.rotation.set(t * 0.08, 0, 0);
    if (caps.current) caps.current.visible = t > 0.002;
  });

  const main = plan.placements.filter((p) => !p.inSlice);
  const sliced = plan.placements.filter((p) => p.inSlice);
  const top = design.tiers.length - 1;
  const scale = extras?.scale ?? 1;

  return (
    <group scale={scale}>
      <group ref={baseGroup}>
        <Base design={design} radius={design.tiers[0].radius} />
      </group>
      {design.tiers.map((tier, i) => {
        const y = plan.tierY[i];
        const mat = frostingMaterial(
          design,
          tier.finish ?? design.finish,
          tier.frosting ?? design.frosting,
        );
        const cut = canSlice && i === 0;
        const phiStart = cut ? SLICE_START + SLICE : 0;
        const phiLength = cut ? Math.PI * 2 - SLICE : Math.PI * 2;
        return (
          <group
            key={i}
            position={[0, y, 0]}
            ref={(group) => {
              tierGroups.current[i] = group;
            }}
          >
            <mesh
              geometry={tierGeometry(
                tier.radius,
                tier.height,
                phiStart,
                phiLength,
              )}
              material={mat}
              castShadow
              receiveShadow
            />
            {cut && (
              <group ref={caps} visible={false}>
                <Cap
                  design={design}
                  radius={tier.radius}
                  height={tier.height}
                  phi={phiStart}
                />
                <Cap
                  design={design}
                  radius={tier.radius}
                  height={tier.height}
                  phi={phiStart + phiLength}
                />
              </group>
            )}
            {i === top && (design.drip || design.glaze) && (
              <Glaze
                radius={tier.radius}
                y={tier.height}
                color={design.drip?.color ?? design.glaze!}
                phiStart={phiStart}
                phiLength={phiLength}
              />
            )}
          </group>
        );
      })}
      <group ref={decor}>
        <Toppings placements={main} />
      </group>
      {canSlice && (
        <group ref={sliceGroup}>
          <group position={[0, plan.tierY[0], 0]}>
            <mesh
              geometry={tierGeometry(
                design.tiers[0].radius,
                design.tiers[0].height,
                SLICE_START,
                SLICE,
              )}
              material={frostingMaterial(design)}
              castShadow
              receiveShadow
            />
            <Cap
              design={design}
              radius={design.tiers[0].radius}
              height={design.tiers[0].height}
              phi={SLICE_START}
            />
            <Cap
              design={design}
              radius={design.tiers[0].radius}
              height={design.tiers[0].height}
              phi={SLICE_START + SLICE}
            />
            {(design.drip || design.glaze) && (
              <Glaze
                radius={design.tiers[0].radius}
                y={design.tiers[0].height}
                color={design.drip?.color ?? design.glaze!}
                phiStart={SLICE_START}
                phiLength={SLICE}
              />
            )}
          </group>
          {sliced.length > 0 && <Toppings placements={sliced} />}
        </group>
      )}
      {message && (
        <Text
          font={MESSAGE_FONT}
          position={[
            0,
            plan.top.y + (design.glaze || design.drip ? 0.03 : 0.008),
            plan.top.radius * 0.28,
          ]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.15 * Math.min(1, plan.top.radius)}
          maxWidth={plan.top.radius * 1.35}
          textAlign="center"
          anchorX="center"
          anchorY="middle"
          lineHeight={1}
          color={design.messageColor}
        >
          {message}
        </Text>
      )}
      {extras?.candles && extras.candles !== "none" && (
        <Candles kind={extras.candles} top={plan.top} />
      )}
      {hasBirthdayTopper(extras) && (
        <group position={[0, plan.top.y, -plan.top.radius * 0.45]}>
          <Text
            font={MESSAGE_FONT}
            position={[0, 0.48, 0]}
            fontSize={0.2}
            color="#c9a14f"
            anchorX="center"
            anchorY="middle"
          >
            Happy Birthday
          </Text>
          {[-0.32, 0.32].map((x) => (
            <mesh key={x} position={[x, 0.2, 0]}>
              <cylinderGeometry args={[0.006, 0.006, 0.42, 6]} />
              <meshStandardMaterial
                color="#c9a14f"
                metalness={1}
                roughness={0.3}
              />
            </mesh>
          ))}
        </group>
      )}
    </group>
  );
}

/** Overall height, so cameras can frame tall tiered cakes and petite bentos alike. */
export function cakeHeight(design: CakeDesign) {
  return (
    baseHeightFor(design) +
    design.tiers.reduce((sum, tier) => sum + tier.height, 0)
  );
}
