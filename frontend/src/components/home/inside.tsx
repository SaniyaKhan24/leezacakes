"use client";

import {
  motion,
  useMotionValueEvent,
  useScroll,
  useTransform,
  type MotionValue,
} from "motion/react";
import { useRef } from "react";
import { LazyCake } from "@/components/cake/lazy-cake";

const STEPS = [
  {
    eyebrow: "01 — The sponge",
    title: "Buttermilk, *beaten slow.*",
    copy: "Every sponge is mixed the morning it's baked, so the crumb stays tender and a little damp — the way a layer cake should be.",
  },
  {
    eyebrow: "02 — The layers",
    title: "Cream cheese, *edge to edge.*",
    copy: "Four layers, each filled right to the rim. Cut a slice and you get the same ratio of sponge to cream from the first bite to the last.",
  },
  {
    eyebrow: "03 — The finish",
    title: "Piped *by hand.*",
    copy: "Velvet crumb pressed onto the sides, a crown of piped kisses on top. Ask for a message and we write it in the same hand.",
  },
];

function Step({
  progress,
  index,
}: {
  progress: MotionValue<number>;
  index: number;
}) {
  const start = index / STEPS.length;
  const end = (index + 1) / STEPS.length;
  const opacity = useTransform(
    progress,
    [start, start + 0.06, end - 0.06, end],
    index === 0
      ? [1, 1, 1, 0]
      : index === STEPS.length - 1
        ? [0, 1, 1, 1]
        : [0, 1, 1, 0],
  );
  const y = useTransform(
    progress,
    [start, start + 0.08, end - 0.08, end],
    index === 0
      ? [0, 0, 0, -40]
      : [40, 0, 0, index === STEPS.length - 1 ? 0 : -40],
  );
  const step = STEPS[index];
  return (
    <motion.div className="inside-step" style={{ opacity, y }}>
      <p className="eyebrow">{step.eyebrow}</p>
      <h2
        dangerouslySetInnerHTML={{
          __html: step.title.replace(/\*([^*]+)\*/g, "<em>$1</em>"),
        }}
      />
      <p>{step.copy}</p>
    </motion.div>
  );
}

function Bar({
  progress,
  index,
}: {
  progress: MotionValue<number>;
  index: number;
}) {
  const scaleX = useTransform(
    progress,
    [index / STEPS.length, (index + 1) / STEPS.length],
    [0, 1],
  );
  return (
    <span>
      <motion.i style={{ scaleX }} />
    </span>
  );
}

/** A pinned cake that turns and lifts out a slice as you scroll through its story. */
export function Inside() {
  const track = useRef<HTMLDivElement>(null);
  const slice = useRef(0);
  const rotation = useRef(0);
  const { scrollYProgress } = useScroll({
    target: track,
    offset: ["start start", "end end"],
  });
  useMotionValueEvent(scrollYProgress, "change", (p) => {
    slice.current = Math.min(1, Math.max(0, (p - 0.22) / 0.3));
    rotation.current = p * Math.PI * 0.55;
  });
  return (
    <section className="inside" aria-label="Inside a Leeza cake">
      <div ref={track} className="inside-track">
        <div className="inside-sticky shell">
          <div className="inside-stage" data-cursor="Scroll">
            <LazyCake
              slug="red-velvet"
              poster="/images/cakes/red-velvet.webp"
              slice={slice}
              rotation={rotation}
              autoRotate={false}
              initialRotation={-0.9}
            />
          </div>
          <div>
            <div className="inside-copy">
              {STEPS.map((_, i) => (
                <Step key={i} progress={scrollYProgress} index={i} />
              ))}
            </div>
            <div className="inside-progress" aria-hidden="true">
              {STEPS.map((_, i) => (
                <Bar key={i} progress={scrollYProgress} index={i} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
