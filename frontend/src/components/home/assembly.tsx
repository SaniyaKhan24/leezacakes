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
    eyebrow: "Tier one",
    title: "A *steady* foundation.",
    copy: "The bottom tier carries everything, so it gets the densest vanilla sponge and a crumb coat that's chilled before the final finish goes on.",
  },
  {
    eyebrow: "Tier two",
    title: "Combed, *not* smoothed.",
    copy: "The middle tier is finished with a ridged comb in one slow turn of the turntable. It catches the light differently from every angle.",
  },
  {
    eyebrow: "Tier three",
    title: "Lifted *into place.*",
    copy: "Each tier stands on its own hidden supports, so the cake travels well and cuts cleanly at the table.",
  },
  {
    eyebrow: "The finish",
    title: "Pearls, gold, *roses.*",
    copy: "Hand-rolled sugar pearls at every seam, gold leaf pressed on by hand, and sugar roses that take a week to make. Then it's yours.",
  },
];

/**
 * Scroll ranges for each step, matched to when its tier lands in CakeModel's
 * assembly timeline (board 0–0.1, tiers across 0.1–0.72, decorations 0.76–0.96).
 */
const BOUNDS = [0, 0.2, 0.38, 0.59, 1];
const toAssembly = (p: number) => Math.min(1, Math.max(0, 0.08 + p / 0.86));

function Step({
  progress,
  index,
}: {
  progress: MotionValue<number>;
  index: number;
}) {
  const start = BOUNDS[index];
  const end = BOUNDS[index + 1];
  const first = index === 0;
  const last = index === STEPS.length - 1;
  const opacity = useTransform(
    progress,
    [start, start + 0.05, end - 0.05, end],
    [first ? 1 : 0, 1, 1, last ? 1 : 0],
  );
  const y = useTransform(
    progress,
    [start, start + 0.06, end - 0.06, end],
    [first ? 0 : 50, 0, 0, last ? 0 : -50],
  );
  const step = STEPS[index];
  return (
    <motion.div className="inside-step" style={{ opacity, y }}>
      <p className="eyebrow">
        0{index + 1} — {step.eyebrow}
      </p>
      <h2
        dangerouslySetInnerHTML={{
          __html: step.title.replace(/\*([^*]+)\*/g, "<em>$1</em>"),
        }}
      />
      <p>{step.copy}</p>
    </motion.div>
  );
}

function Counter({ progress }: { progress: MotionValue<number> }) {
  const width = useTransform(progress, [0, 1], ["0%", "100%"]);
  return (
    <div className="assembly-meter" aria-hidden="true">
      <span>Board</span>
      <div>
        <motion.i style={{ width }} />
      </div>
      <span>Finished</span>
    </div>
  );
}

/**
 * A pinned scene: scroll down and the three-tier cake is built in front of you,
 * board first, then each tier set down in turn, then the decorations.
 */
export function Assembly() {
  const track = useRef<HTMLDivElement>(null);
  const assembly = useRef(toAssembly(0));
  const rotation = useRef(0);
  const { scrollYProgress } = useScroll({
    target: track,
    offset: ["start start", "end end"],
  });
  useMotionValueEvent(scrollYProgress, "change", (p) => {
    // The board is already set at the top; the finished cake holds for the last stretch.
    assembly.current = toAssembly(p);
    rotation.current = p * Math.PI * 1.1;
  });
  return (
    <section className="assembly" aria-label="How a tiered cake is built">
      <div ref={track} className="assembly-track">
        <div className="inside-sticky shell assembly-sticky">
          <div>
            <div className="inside-copy">
              {STEPS.map((_, i) => (
                <Step key={i} progress={scrollYProgress} index={i} />
              ))}
            </div>
            <Counter progress={scrollYProgress} />
          </div>
          <div className="assembly-stage" data-cursor="Scroll">
            <LazyCake
              slug="gilded-three-tier"
              assembly={assembly}
              rotation={rotation}
              autoRotate={false}
              initialRotation={-0.6}
              shadowOpacity={0.5}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
