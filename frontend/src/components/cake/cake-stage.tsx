"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  ContactShadows,
  Environment,
  Lightformer,
  OrbitControls,
} from "@react-three/drei";
import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
  type ReactNode,
} from "react";
import * as THREE from "three";
import { CakeModel, cakeHeight } from "./cake-model";
import { designFor, type CakeDesign, type CakeExtras } from "./designs";

/** Soft studio lighting built from light-formers, so no HDR files are fetched. */
export function StudioLights({ intensity = 1 }: { intensity?: number }) {
  return (
    <>
      <ambientLight intensity={0.25 * intensity} color="#fff3e6" />
      <directionalLight
        position={[3.2, 6.5, 4.2]}
        intensity={2.1 * intensity}
        color="#fff1df"
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.0004}
        shadow-normalBias={0.02}
        shadow-camera-left={-3}
        shadow-camera-right={3}
        shadow-camera-top={4}
        shadow-camera-bottom={-1}
      />
      <directionalLight
        position={[-4, 2.5, -2]}
        intensity={0.55 * intensity}
        color="#ffd9c7"
      />
      <Environment resolution={256} frames={1}>
        <Lightformer
          form="rect"
          intensity={2.4}
          color="#fff4e8"
          scale={[6, 3, 1]}
          position={[0, 5, 3]}
          rotation-x={-Math.PI / 2.6}
        />
        <Lightformer
          form="rect"
          intensity={1.4}
          color="#ffe6d6"
          scale={[3, 5, 1]}
          position={[-5, 2, 1]}
          rotation-y={Math.PI / 2}
        />
        <Lightformer
          form="rect"
          intensity={1.1}
          color="#fff8f0"
          scale={[3, 5, 1]}
          position={[5, 2, -1]}
          rotation-y={-Math.PI / 2}
        />
        <Lightformer
          form="ring"
          intensity={0.8}
          color="#ffcfae"
          scale={4}
          position={[0, 1, -6]}
        />
        <Lightformer
          form="rect"
          intensity={0.5}
          color="#e9cdb4"
          scale={[10, 10, 1]}
          position={[0, -2, 0]}
          rotation-x={Math.PI / 2}
        />
      </Environment>
    </>
  );
}

export function frame(design: CakeDesign, scale = 1) {
  const height = cakeHeight(design) * scale;
  const width =
    (design.tiers[0].radius + (design.board === "stand" ? 0.45 : 0.3)) *
    2 *
    scale;
  return { height, width, target: new THREE.Vector3(0, height * 0.46, 0) };
}

function Rig({
  design,
  scale,
  autoRotate,
  interactive,
  distance,
}: {
  design: CakeDesign;
  scale: number;
  autoRotate: boolean;
  interactive: boolean;
  distance?: number;
}) {
  const { camera, size } = useThree();
  const f = useMemo(() => frame(design, scale), [design, scale]);
  useEffect(() => {
    const persp = camera as THREE.PerspectiveCamera;
    const aspect = size.width / Math.max(1, size.height);
    const fitHeight = f.height * 1.25;
    const fitWidth = (f.width * 1.18) / Math.min(aspect, 1.6);
    const span = Math.max(fitHeight, fitWidth);
    const d =
      distance ??
      span / (2 * Math.tan(THREE.MathUtils.degToRad(persp.fov) / 2));
    const elevation = 0.42;
    persp.position.set(
      0,
      f.target.y + Math.sin(elevation) * d,
      Math.cos(elevation) * d,
    );
    persp.lookAt(f.target);
    persp.updateProjectionMatrix();
  }, [camera, size, f, distance]);
  return (
    <>
      {interactive && (
        <OrbitControls
          target={f.target}
          enablePan={false}
          enableZoom={false}
          autoRotate={autoRotate}
          autoRotateSpeed={0.7}
          enableDamping
          dampingFactor={0.06}
          minPolarAngle={Math.PI * 0.2}
          maxPolarAngle={Math.PI * 0.47}
        />
      )}
    </>
  );
}

function Spin({
  children,
  autoRotate,
  pointerTilt,
  interactive,
  initial = 0,
  rotation,
}: {
  children: ReactNode;
  autoRotate: boolean;
  pointerTilt: boolean;
  interactive: boolean;
  initial?: number;
  rotation?: MutableRefObject<number>;
}) {
  const group = useRef<THREE.Group>(null);
  useFrame(({ pointer }, delta) => {
    const g = group.current;
    if (!g) return;
    if (rotation)
      g.rotation.y = THREE.MathUtils.damp(
        g.rotation.y,
        initial + rotation.current,
        4,
        delta,
      );
    else if (autoRotate && !interactive) g.rotation.y += delta * 0.16;
    if (pointerTilt) {
      g.rotation.x = THREE.MathUtils.damp(
        g.rotation.x,
        -pointer.y * 0.05,
        2.5,
        delta,
      );
      g.rotation.z = THREE.MathUtils.damp(
        g.rotation.z,
        pointer.x * 0.035,
        2.5,
        delta,
      );
    }
  });
  return (
    <group ref={group} rotation={[0, initial, 0]}>
      {children}
    </group>
  );
}

/** Renders only while visible on screen, so off-screen cakes cost nothing. */
function useInView<T extends Element>() {
  const ref = useRef<T>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { rootMargin: "120px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return [ref, visible] as const;
}

export type CakeStageProps = {
  slug: string;
  design?: CakeDesign;
  extras?: CakeExtras;
  slice?: MutableRefObject<number>;
  autoRotate?: boolean;
  interactive?: boolean;
  pointerTilt?: boolean;
  initialRotation?: number;
  className?: string;
  shadowOpacity?: number;
  /** Extra Y rotation (radians) driven from outside, e.g. by scroll progress. */
  rotation?: MutableRefObject<number>;
  onReady?: () => void;
};

export function CakeStage({
  slug,
  design: given,
  extras,
  slice,
  autoRotate = true,
  interactive = false,
  pointerTilt = false,
  initialRotation = -0.5,
  className,
  shadowOpacity = 0.42,
  rotation,
  onReady,
}: CakeStageProps) {
  const design = given ?? designFor(slug);
  const [ref, visible] = useInView<HTMLDivElement>();
  const reduced = usePrefersReducedMotion();
  const scale = extras?.scale ?? 1;
  return (
    <div
      ref={ref}
      className={className}
      style={{ position: "relative", width: "100%", height: "100%" }}
    >
      <Canvas
        shadows
        dpr={[1, 1.5]}
        frameloop={visible ? (reduced ? "demand" : "always") : "never"}
        camera={{ fov: 28, near: 0.1, far: 60 }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
        }}
        onCreated={({ gl }) => {
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = 1.05;
          onReady?.();
        }}
        style={{ touchAction: interactive ? "pan-y" : "auto" }}
      >
        <Suspense fallback={null}>
          <StudioLights />
          <Rig
            design={design}
            scale={scale}
            autoRotate={autoRotate && interactive && !reduced}
            interactive={interactive}
          />
          <Spin
            autoRotate={autoRotate && !reduced}
            pointerTilt={pointerTilt && !reduced}
            interactive={interactive}
            initial={initialRotation}
            rotation={rotation}
          >
            <CakeModel design={design} extras={extras} slice={slice} />
          </Spin>
          <ContactShadows
            position={[0, 0.001, 0]}
            opacity={shadowOpacity}
            scale={8}
            blur={2.4}
            far={3}
            resolution={512}
            color="#3a2216"
            frames={slice ? Infinity : 30}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return reduced;
}
