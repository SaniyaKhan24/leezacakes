"use client";

import { ReactLenis, useLenis } from "lenis/react";
import {
  animate,
  motion,
  useInView,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
  type MotionProps,
} from "motion/react";
import { usePathname } from "next/navigation";
import {
  Fragment,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type CSSProperties,
  type ElementType,
  type ReactNode,
} from "react";

export const EASE = [0.22, 1, 0.36, 1] as const;
export const EASE_IN_OUT = [0.76, 0, 0.24, 1] as const;

/** Buttery inertial scrolling; disabled for people who prefer reduced motion. */
export function SmoothScroll({ children }: { children: ReactNode }) {
  const reduced = useReducedMotion();
  if (reduced) return <>{children}</>;
  return (
    <ReactLenis
      root
      options={{ lerp: 0.085, wheelMultiplier: 0.95, smoothWheel: true }}
    >
      <ScrollReset />
      {children}
    </ReactLenis>
  );
}

function ScrollReset() {
  const lenis = useLenis();
  const pathname = usePathname();
  useEffect(() => {
    lenis?.scrollTo(0, { immediate: true });
  }, [pathname, lenis]);
  return null;
}

/**
 * Editorial heading that rises in word by word from behind a mask.
 * Wrap words in *asterisks* to set them in the italic accent.
 */
export function SplitText({
  text,
  as = "h2",
  className,
  delay = 0,
  stagger = 0.045,
  once = true,
}: {
  text: string;
  as?: ElementType;
  className?: string;
  delay?: number;
  stagger?: number;
  once?: boolean;
}) {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once, margin: "0px 0px -10% 0px" });
  const reduced = useReducedMotion();
  const parts = text.split(/(\*[^*]+\*)/g).filter(Boolean);
  let index = 0;
  const lines = parts.flatMap((part) => {
    const accent = part.startsWith("*") && part.endsWith("*");
    const clean = accent ? part.slice(1, -1) : part;
    return clean.split(/(\s+|\n)/).map((word) => ({ word, accent }));
  });
  const Tag = as;
  return (
    <Tag ref={ref} className={className} aria-label={text.replaceAll("*", "")}>
      {lines.map(({ word, accent }, i) => {
        if (word === "\n") return <br key={i} />;
        if (/^\s+$/.test(word)) return <Fragment key={i}> </Fragment>;
        const n = index++;
        const inner = (
          <motion.span
            className="split-word"
            initial={reduced ? false : { y: "108%", rotate: 4 }}
            animate={inView || reduced ? { y: "0%", rotate: 0 } : undefined}
            transition={{
              duration: 1.05,
              ease: EASE,
              delay: delay + n * stagger,
            }}
          >
            {accent ? <em>{word}</em> : word}
          </motion.span>
        );
        return (
          <span key={i} className="split-mask" aria-hidden="true">
            {inner}
          </span>
        );
      })}
    </Tag>
  );
}

export function FadeIn({
  children,
  className,
  delay = 0,
  y = 28,
  as = "div",
  style,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  y?: number;
  as?: "div" | "section" | "li" | "article" | "p" | "span";
  style?: CSSProperties;
}) {
  const reduced = useReducedMotion();
  const Comp = motion[as] as typeof motion.div;
  return (
    <Comp
      className={className}
      style={style}
      initial={reduced ? false : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "0px 0px -8% 0px" }}
      transition={{ duration: 1, ease: EASE, delay }}
    >
      {children}
    </Comp>
  );
}

/** Curtain-wipe reveal for photographs, with a slow settle of the image inside. */
export function ImageReveal({
  children,
  className,
  delay = 0,
  direction = "up",
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  direction?: "up" | "left";
}) {
  const reduced = useReducedMotion();
  const from =
    direction === "up" ? "inset(100% 0% 0% 0%)" : "inset(0% 100% 0% 0%)";
  return (
    <motion.div
      className={className}
      initial={reduced ? false : { clipPath: from }}
      whileInView={{ clipPath: "inset(0% 0% 0% 0%)" }}
      viewport={{ once: true, margin: "0px 0px -10% 0px" }}
      transition={{ duration: 1.3, ease: EASE_IN_OUT, delay }}
    >
      <motion.div
        style={{ width: "100%", height: "100%" }}
        initial={reduced ? false : { scale: 1.18 }}
        whileInView={{ scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.8, ease: EASE, delay }}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

/** Buttons that lean towards the pointer, then spring home. */
export function Magnetic({
  children,
  strength = 0.32,
  className,
}: {
  children: ReactNode;
  strength?: number;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const x = useSpring(0, { stiffness: 220, damping: 18, mass: 0.6 });
  const y = useSpring(0, { stiffness: 220, damping: 18, mass: 0.6 });
  return (
    <motion.span
      ref={ref}
      className={`magnetic ${className ?? ""}`}
      style={{ x, y, display: "inline-flex" }}
      onPointerMove={(event) => {
        if (event.pointerType !== "mouse" || !ref.current) return;
        const rect = ref.current.getBoundingClientRect();
        x.set((event.clientX - rect.left - rect.width / 2) * strength);
        y.set((event.clientY - rect.top - rect.height / 2) * strength);
      }}
      onPointerLeave={() => {
        x.set(0);
        y.set(0);
      }}
    >
      {children}
    </motion.span>
  );
}

export function Marquee({
  items,
  speed = 38,
  className,
}: {
  items: string[];
  speed?: number;
  className?: string;
}) {
  const row = [...items, ...items];
  return (
    <div className={`marquee ${className ?? ""}`} aria-hidden="true">
      <div className="marquee-track" style={{ animationDuration: `${speed}s` }}>
        {[0, 1].map((copy) => (
          <div className="marquee-group" key={copy}>
            {row.map((item, i) => (
              <span key={`${copy}-${i}`} className="marquee-item">
                {item}
                <svg
                  viewBox="0 0 24 24"
                  className="marquee-star"
                  aria-hidden="true"
                >
                  <path
                    d="M12 2l1.9 6.6L20 10l-6.1 1.4L12 18l-1.9-6.6L4 10l6.1-1.4z"
                    fill="currentColor"
                  />
                </svg>
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** A number that glides to its new value instead of snapping. */
export function RollingNumber({
  value,
  format,
}: {
  value: number;
  format: (n: number) => string;
}) {
  const motionValue = useMotionValue(value);
  const [display, setDisplay] = useState(format(value));
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      motionValue.set(value);
      setDisplay(format(value));
      return;
    }
    const controls = animate(motionValue, value, {
      duration: 0.7,
      ease: EASE,
      onUpdate: (latest) => setDisplay(format(Math.round(latest))),
    });
    return () => controls.stop();
  }, [value, format, motionValue]);
  return <span className="tabular">{display}</span>;
}

/** A small cursor companion that grows into a label over cards and 3D stages. */
export function Cursor() {
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const sx = useSpring(x, { stiffness: 500, damping: 40, mass: 0.4 });
  const sy = useSpring(y, { stiffness: 500, damping: 40, mass: 0.4 });
  const [label, setLabel] = useState<string | null>(null);
  const enabled = useSyncExternalStore(
    () => () => undefined,
    () =>
      window.matchMedia("(pointer: fine)").matches &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false,
  );
  useEffect(() => {
    if (!enabled) return;
    const move = (event: PointerEvent) => {
      x.set(event.clientX);
      y.set(event.clientY);
      const target = (event.target as HTMLElement | null)?.closest<HTMLElement>(
        "[data-cursor]",
      );
      setLabel(target?.dataset.cursor ?? null);
    };
    window.addEventListener("pointermove", move, { passive: true });
    return () => window.removeEventListener("pointermove", move);
  }, [enabled, x, y]);
  if (!enabled) return null;
  return (
    <motion.div
      className={`cursor ${label ? "cursor-label" : ""}`}
      style={{ x: sx, y: sy }}
      aria-hidden="true"
    >
      <motion.span
        animate={{ scale: label ? 1 : 0.18 }}
        transition={{ type: "spring", stiffness: 300, damping: 24 }}
        className="cursor-bubble"
      >
        <span className="cursor-text">{label}</span>
      </motion.span>
    </motion.div>
  );
}

/** Parallax helper: maps scroll progress of an element to a translateY range. */
export function useParallax(range = 80) {
  const ref = useRef<HTMLDivElement>(null);
  const progress = useMotionValue(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => {
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      progress.set(
        Math.min(1, Math.max(0, (vh - rect.top) / (vh + rect.height))),
      );
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [progress]);
  const y = useTransform(progress, [0, 1], [range, -range]);
  return { ref, y };
}

export type { MotionProps };
