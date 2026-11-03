"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { ContactShadows } from "@react-three/drei";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { CakeModel } from "@/components/cake/cake-model";
import { frame, StudioLights } from "@/components/cake/cake-stage";
import { designFor } from "@/components/cake/designs";

declare global {
  interface Window {
    __cakeReady?: boolean;
  }
}

function Shot({
  slug,
  angle,
  elevation,
  sliceOpen,
  zoom,
}: {
  slug: string;
  angle: number;
  elevation: number;
  sliceOpen: number;
  zoom: number;
}) {
  const design = designFor(slug);
  const { camera, size } = useThree();
  const slice = useRef(sliceOpen);
  const frames = useRef(0);
  const f = useMemo(() => frame(design), [design]);
  useEffect(() => {
    const persp = camera as THREE.PerspectiveCamera;
    const aspect = size.width / size.height;
    const span =
      Math.max(f.height * 1.3, (f.width * 1.12) / Math.min(aspect, 1.4)) / zoom;
    const d = span / (2 * Math.tan(THREE.MathUtils.degToRad(persp.fov) / 2));
    persp.position.set(
      0,
      f.target.y + Math.sin(elevation) * d,
      Math.cos(elevation) * d,
    );
    persp.lookAt(f.target.x, f.target.y - f.height * 0.04, f.target.z);
    persp.updateProjectionMatrix();
  }, [camera, size, f, elevation, zoom]);
  useFrame(() => {
    frames.current += 1;
    // Give textures, fonts and the environment map time to settle before capture.
    if (frames.current === 10) window.__cakeReady = true;
  });
  return (
    <group rotation={[0, angle, 0]}>
      <CakeModel
        design={design}
        slice={sliceOpen > 0 ? slice : undefined}
        sliceImmediate
      />
    </group>
  );
}

export function StudioRender() {
  const params = useSearchParams();
  const slug = params.get("slug") ?? "red-velvet";
  const angle = Number(params.get("angle") ?? -0.5);
  const elevation = Number(params.get("elevation") ?? 0.36);
  const sliceOpen = Number(params.get("slice") ?? 0);
  const zoom = Number(params.get("zoom") ?? 1);
  const backdrop = params.get("bg");
  useEffect(() => {
    window.__cakeReady = false;
    document.documentElement.style.background = backdrop
      ? `#${backdrop}`
      : "transparent";
    document.body.style.background = backdrop ? `#${backdrop}` : "transparent";
  }, [backdrop]);
  return (
    <div style={{ position: "fixed", inset: 0 }}>
      <Canvas
        shadows
        dpr={1}
        camera={{ fov: 26, near: 0.1, far: 60 }}
        gl={{ antialias: true, alpha: true, preserveDrawingBuffer: true }}
        onCreated={({ gl }) => {
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.05;
          gl.setClearColor(0x000000, 0);
        }}
      >
        <Suspense fallback={null}>
          <StudioLights />
          <Shot
            slug={slug}
            angle={angle}
            elevation={elevation}
            sliceOpen={sliceOpen}
            zoom={zoom}
          />
          <ContactShadows
            position={[0, 0.001, 0]}
            opacity={0.5}
            scale={9}
            blur={2.2}
            far={3.2}
            resolution={1024}
            color="#3a2216"
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
