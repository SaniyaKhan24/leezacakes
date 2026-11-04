"use client";

import { useEffect, useMemo, useState } from "react";
import { ButtonLink } from "@/components/commerce-ui";
import { LazyCake } from "@/components/cake/lazy-cake";
import type { CakeExtras } from "@/components/cake/designs";
import { FadeIn, Magnetic, SplitText } from "@/components/motion";

const SEQUENCE: { label: string; extras: CakeExtras }[] = [
  { label: "Plain & perfect", extras: {} },
  { label: "Fresh flowers", extras: { touches: ["Fresh flowers"] } },
  {
    label: "A message",
    extras: { touches: ["Fresh flowers"], message: "Happy 30th, Kabir" },
  },
  {
    label: "Gold leaf",
    extras: {
      touches: ["Fresh flowers", "Gold leaf"],
      message: "Happy 30th, Kabir",
    },
  },
  {
    label: "Candles",
    extras: {
      touches: ["Fresh flowers", "Gold leaf"],
      message: "Happy 30th, Kabir",
      candles: "number",
    },
  },
];

export function MakeYours() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = window.setInterval(
      () => setStep((s) => (s + 1) % SEQUENCE.length),
      2600,
    );
    return () => window.clearInterval(id);
  }, []);
  const extras = useMemo(() => SEQUENCE[step].extras, [step]);
  return (
    <section className="make" aria-labelledby="make-title">
      <div className="shell make-grid">
        <div>
          <FadeIn>
            <p className="eyebrow">The cake designer</p>
          </FadeIn>
          <SplitText text={"Make it\n*unmistakably* yours."} />
          <FadeIn delay={0.2}>
            <p className="lede">
              Pick a base, then add what matters: eggless sponge, a message in
              our hand, fresh flowers, gold leaf, candles. Watch it come
              together in 3D before you order.
            </p>
          </FadeIn>
          <FadeIn delay={0.3} className="make-chips">
            {SEQUENCE.map((s, i) => (
              <span key={s.label} className={i <= step ? "is-on" : ""}>
                {s.label}
              </span>
            ))}
          </FadeIn>
          <FadeIn delay={0.4}>
            <Magnetic>
              <ButtonLink href="/custom" variant="light">
                Open the designer
              </ButtonLink>
            </Magnetic>
          </FadeIn>
        </div>
        <div className="make-stage" data-cursor="Drag">
          <LazyCake
            slug="vanilla-berry"
            poster="/images/cakes/vanilla-berry.webp"
            extras={extras}
            interactive
            autoRotate
            shadowOpacity={0.6}
            initialRotation={-0.2}
          />
        </div>
      </div>
    </section>
  );
}
