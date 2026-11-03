import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { rng } from "./textures";

/** Shared, cached geometry for the procedural cakes. */

const cache = new Map<string, THREE.BufferGeometry>();
function memo(key: string, make: () => THREE.BufferGeometry) {
  const hit = cache.get(key);
  if (hit) return hit;
  const geometry = make();
  cache.set(key, geometry);
  return geometry;
}

/** Silhouette of one tier: flat base, straight wall, softly rounded top edge. */
export function tierProfile(radius: number, height: number) {
  const points: THREE.Vector2[] = [new THREE.Vector2(0.0001, 0)];
  const base = 0.012;
  const top = Math.min(0.07, height * 0.1);
  points.push(new THREE.Vector2(radius - base, 0));
  for (let i = 1; i <= 4; i += 1) {
    const a = (i / 4) * (Math.PI / 2);
    points.push(
      new THREE.Vector2(
        radius - base + Math.sin(a) * base,
        base - Math.cos(a) * base,
      ),
    );
  }
  const wallSteps = 18;
  for (let i = 1; i <= wallSteps; i += 1) {
    points.push(
      new THREE.Vector2(radius, base + ((height - top - base) * i) / wallSteps),
    );
  }
  for (let i = 1; i <= 10; i += 1) {
    const a = (i / 10) * (Math.PI / 2);
    points.push(
      new THREE.Vector2(
        radius - top + Math.cos(a) * top,
        height - top + Math.sin(a) * top,
      ),
    );
  }
  points.push(new THREE.Vector2(radius * 0.5, height));
  points.push(new THREE.Vector2(0.0001, height));
  return points;
}

export function tierGeometry(
  radius: number,
  height: number,
  phiStart = 0,
  phiLength = Math.PI * 2,
) {
  return memo(
    `tier:${radius}:${height}:${phiStart.toFixed(4)}:${phiLength.toFixed(4)}`,
    () => {
      const segments = Math.max(
        12,
        Math.round((phiLength / (Math.PI * 2)) * 128),
      );
      const geometry = new THREE.LatheGeometry(
        tierProfile(radius, height),
        segments,
        phiStart,
        phiLength,
      );
      geometry.computeVertexNormals();
      return geometry;
    },
  );
}

/** The exposed cut face, UV-mapped so (0,0) is the centre-bottom and (1,1) the outer top. */
export function capGeometry(radius: number, height: number) {
  return memo(`cap:${radius}:${height}`, () => {
    const shape = new THREE.Shape(
      tierProfile(radius, height).map((p) => new THREE.Vector2(p.x, p.y)),
    );
    const geometry = new THREE.ShapeGeometry(shape, 12);
    const pos = geometry.attributes.position;
    const uv = geometry.attributes.uv;
    for (let i = 0; i < pos.count; i += 1)
      uv.setXY(i, pos.getX(i) / radius, pos.getY(i) / height);
    uv.needsUpdate = true;
    return geometry;
  });
}

/** A piped star-tip "kiss": an eight-point star extruded upwards, twisted and tapered. */
export function kissGeometry(scale = 1) {
  return memo(`kiss:${scale}`, () => {
    const star = new THREE.Shape();
    const points = 8;
    for (let i = 0; i <= points * 2; i += 1) {
      const a = (i / (points * 2)) * Math.PI * 2;
      const r = (i % 2 === 0 ? 0.095 : 0.068) * scale;
      const x = Math.cos(a) * r;
      const y = Math.sin(a) * r;
      if (i === 0) star.moveTo(x, y);
      else star.lineTo(x, y);
    }
    const height = 0.16 * scale;
    const geometry = new THREE.ExtrudeGeometry(star, {
      depth: height,
      bevelEnabled: false,
      steps: 24,
      curveSegments: 2,
    });
    const pos = geometry.attributes.position;
    for (let i = 0; i < pos.count; i += 1) {
      const z = pos.getZ(i) / height;
      const taper =
        Math.pow(1 - z, 0.6) * (1 + 0.18 * Math.sin(z * Math.PI * 0.9));
      const twist = z * 1.6;
      const x = pos.getX(i);
      const y = pos.getY(i);
      pos.setXYZ(
        i,
        (x * Math.cos(twist) - y * Math.sin(twist)) * taper,
        (x * Math.sin(twist) + y * Math.cos(twist)) * taper,
        pos.getZ(i),
      );
    }
    geometry.rotateX(-Math.PI / 2);
    geometry.computeVertexNormals();
    return geometry;
  });
}

/** A wide, low swirl of whipped cream. */
export function rosetteGeometry() {
  return memo("rosette", () => {
    const geometry = kissGeometry(1.45).clone();
    geometry.scale(1, 0.72, 1);
    geometry.computeVertexNormals();
    return geometry;
  });
}

/** A single cupped petal; used for rose petals and assembled into sugar flowers. */
export function petalGeometry(width = 0.09, length = 0.12, cup = 0.035) {
  return memo(`petal:${width}:${length}:${cup}`, () => {
    const geometry = new THREE.PlaneGeometry(width, length, 8, 8);
    const pos = geometry.attributes.position;
    for (let i = 0; i < pos.count; i += 1) {
      const x = pos.getX(i) / (width / 2);
      const y = pos.getY(i) / (length / 2);
      const narrow =
        1 -
        Math.pow((y + 1) / 2, 2) * 0.15 -
        Math.pow(Math.max(0, -y), 2) * 0.55;
      pos.setX(i, pos.getX(i) * narrow);
      pos.setZ(i, x * x * cup + (y + 1) * 0.008);
    }
    geometry.translate(0, length / 2, 0);
    geometry.computeVertexNormals();
    return geometry;
  });
}

/** A sugar rose: concentric rings of cupped petals merged into one mesh. */
export function roseGeometry() {
  return memo("rose", () => {
    const parts: THREE.BufferGeometry[] = [];
    const rings = [
      { count: 3, size: 0.55, tilt: 0.2 },
      { count: 5, size: 0.8, tilt: 0.55 },
      { count: 7, size: 1.0, tilt: 0.95 },
      { count: 8, size: 1.12, tilt: 1.25 },
    ];
    rings.forEach((ring, r) => {
      for (let i = 0; i < ring.count; i += 1) {
        const petal = petalGeometry(0.1, 0.11, 0.05).clone();
        petal.scale(ring.size, ring.size, ring.size);
        petal.rotateX(-ring.tilt);
        petal.translate(0, 0, 0.012 * r);
        petal.rotateY((i / ring.count) * Math.PI * 2 + r * 0.6);
        parts.push(petal);
      }
    });
    const geometry = mergeGeometries(parts, false)!;
    geometry.computeVertexNormals();
    return geometry;
  });
}

export function shardGeometry(seed: number) {
  return memo(`shard:${seed}`, () => {
    const random = rng(seed);
    const shape = new THREE.Shape();
    const w = 0.16 + random() * 0.1;
    const h = 0.28 + random() * 0.16;
    shape.moveTo(0, 0);
    shape.lineTo(w * (0.7 + random() * 0.3), random() * 0.04);
    shape.lineTo(w * (0.8 + random() * 0.4), h * (0.5 + random() * 0.2));
    shape.lineTo(w * (0.3 + random() * 0.3), h);
    shape.lineTo(-w * 0.1, h * (0.55 + random() * 0.2));
    shape.closePath();
    const geometry = new THREE.ExtrudeGeometry(shape, {
      depth: 0.012,
      bevelEnabled: true,
      bevelSize: 0.004,
      bevelThickness: 0.004,
      bevelSegments: 1,
    });
    geometry.translate(-w / 2, 0, 0);
    geometry.computeVertexNormals();
    return geometry;
  });
}

export function flakeGeometry() {
  return memo("flake", () => {
    const random = rng(41);
    const shape = new THREE.Shape();
    const n = 7;
    for (let i = 0; i <= n; i += 1) {
      const a = (i / n) * Math.PI * 2;
      const r = 0.03 + random() * 0.03;
      if (i === 0) shape.moveTo(Math.cos(a) * r, Math.sin(a) * r);
      else shape.lineTo(Math.cos(a) * r, Math.sin(a) * r);
    }
    const geometry = new THREE.ShapeGeometry(shape);
    const pos = geometry.attributes.position;
    for (let i = 0; i < pos.count; i += 1)
      pos.setZ(i, Math.sin(pos.getX(i) * 60) * 0.003);
    geometry.computeVertexNormals();
    return geometry;
  });
}

export function heartGeometry() {
  return memo("heart", () => {
    const s = new THREE.Shape();
    s.moveTo(0, -0.06);
    s.bezierCurveTo(-0.02, -0.04, -0.075, -0.005, -0.065, 0.03);
    s.bezierCurveTo(-0.055, 0.065, -0.012, 0.07, 0, 0.04);
    s.bezierCurveTo(0.012, 0.07, 0.055, 0.065, 0.065, 0.03);
    s.bezierCurveTo(0.075, -0.005, 0.02, -0.04, 0, -0.06);
    const geometry = new THREE.ExtrudeGeometry(s, {
      depth: 0.025,
      bevelEnabled: true,
      bevelSize: 0.012,
      bevelThickness: 0.012,
      bevelSegments: 4,
      curveSegments: 18,
    });
    geometry.rotateX(-Math.PI / 2);
    geometry.computeVertexNormals();
    return geometry;
  });
}

export function strawberryGeometry() {
  return memo("strawberry", () => {
    const geometry = new THREE.SphereGeometry(0.075, 24, 18);
    const pos = geometry.attributes.position;
    for (let i = 0; i < pos.count; i += 1) {
      const y = pos.getY(i);
      const t = (y + 0.075) / 0.15;
      const squeeze =
        0.55 + 0.45 * Math.sin(Math.min(1, t * 1.15) * Math.PI * 0.62);
      pos.setX(i, pos.getX(i) * squeeze);
      pos.setZ(i, pos.getZ(i) * squeeze);
      pos.setY(i, y * 1.25);
    }
    geometry.computeVertexNormals();
    return geometry;
  });
}

export function leafGeometry() {
  return memo("leaf", () => {
    const geometry = petalGeometry(0.06, 0.11, 0.012).clone();
    geometry.computeVertexNormals();
    return geometry;
  });
}

export function roundedCube(size: number) {
  return memo(
    `rcube:${size}`,
    () => new RoundedBoxGeometry(size, size, size, 3, size * 0.22),
  );
}

export function cookieGeometry() {
  return memo(
    "cookie",
    () => new RoundedBoxGeometry(0.26, 0.17, 0.035, 3, 0.012),
  );
}

export function macaronGeometry() {
  return memo("macaron", () => {
    const shell = new THREE.SphereGeometry(
      0.075,
      28,
      14,
      0,
      Math.PI * 2,
      0,
      Math.PI / 2,
    );
    shell.scale(1, 0.42, 1);
    const top = shell.clone();
    top.translate(0, 0.024, 0);
    const bottom = shell.clone();
    bottom.rotateX(Math.PI);
    bottom.translate(0, -0.006, 0);
    const foot = new THREE.CylinderGeometry(0.073, 0.073, 0.016, 28);
    foot.translate(0, 0.009, 0);
    const geometry = mergeGeometries(
      [top.toNonIndexed(), bottom.toNonIndexed(), foot.toNonIndexed()],
      false,
    )!;
    geometry.computeVertexNormals();
    return geometry;
  });
}

export function curlGeometry() {
  return memo("curl", () => {
    const geometry = new THREE.TorusGeometry(
      0.026,
      0.009,
      6,
      14,
      Math.PI * 1.5,
    );
    geometry.scale(1, 1, 1.6);
    return geometry;
  });
}

/** A footed ceramic cake stand. */
export function standGeometry(radius: number) {
  return memo(`stand:${radius}`, () => {
    const r = radius;
    const pts = [
      [0.0001, 0],
      [r * 0.42, 0],
      [r * 0.45, 0.02],
      [r * 0.44, 0.05],
      [r * 0.2, 0.1],
      [r * 0.12, 0.16],
      [r * 0.1, 0.36],
      [r * 0.16, 0.42],
      [r * 0.95, 0.44],
      [r, 0.455],
      [r * 0.99, 0.48],
      [r * 0.96, 0.49],
      [0.0001, 0.49],
    ].map(([x, y]) => new THREE.Vector2(x, y));
    const geometry = new THREE.LatheGeometry(pts, 96);
    geometry.computeVertexNormals();
    return geometry;
  });
}

export function boardGeometry(radius: number) {
  return memo(`board:${radius}`, () => {
    const geometry = new THREE.CylinderGeometry(radius, radius, 0.045, 96);
    geometry.translate(0, 0.0225, 0);
    return geometry;
  });
}

export function capsule(radius: number, length: number) {
  return memo(
    `capsule:${radius}:${length}`,
    () => new THREE.CapsuleGeometry(radius, length, 6, 12),
  );
}
