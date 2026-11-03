"use client";

import {
  motion,
  useMotionValueEvent,
  useScroll,
  useTransform,
} from "motion/react";
import { useRef } from "react";
import { ButtonLink } from "@/components/commerce-ui";
import { LazyCake } from "@/components/cake/lazy-cake";
import { EASE, FadeIn, Magnetic, SplitText } from "@/components/motion";

export function Hero() {
  const section = useRef<HTMLElement>(null);
  const rotation = useRef(0);
  // As the hero scrolls away the cake turns, sinks and steps back.
  const { scrollYProgress } = useScroll({
    target: section,
    offset: ["start start", "end start"],
  });
  useMotionValueEvent(scrollYProgress, "change", (p) => {
    rotation.current = p * Math.PI * 0.9;
  });
  const y = useTransform(scrollYProgress, [0, 1], [0, 220]);
  const scale = useTransform(scrollYProgress, [0, 1], [1, 0.78]);
  const opacity = useTransform(scrollYProgress, [0, 0.85], [1, 0.15]);
  return (
    <section ref={section} className="hero" aria-labelledby="hero-title">
      <div className="shell hero-grid">
        <div className="hero-copy">
          <FadeIn delay={0.35}>
            <p className="eyebrow">
              A small cake studio · Everything baked to order
            </p>
          </FadeIn>
          <SplitText
            as="h1"
            text={"Cakes worth\n*gathering* for."}
            delay={0.45}
            stagger={0.07}
            className="hero-title"
          />
          <FadeIn delay={0.95}>
            <p className="lede">
              Buttery sponges, fresh cream and patient piping — from a four-inch
              bento for two to a gilded three tier for the whole family. Choose
              a cake, pick a pickup time, and it&apos;s made for that day.
            </p>
          </FadeIn>
          <FadeIn delay={1.1} className="hero-actions">
            <Magnetic>
              <ButtonLink href="/shop">Order a cake</ButtonLink>
            </Magnetic>
            <Magnetic>
              <ButtonLink href="/custom" variant="line">
                Design your own
              </ButtonLink>
            </Magnetic>
          </FadeIn>
        </div>
        <motion.div
          className="hero-stage hero-stage-scroll"
          style={{ y, scale, opacity }}
        >
          <motion.div
            style={{ position: "absolute", inset: 0 }}
            data-cursor="Drag"
            initial={{ opacity: 0, scale: 0.92, y: 40 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 1.6, ease: EASE, delay: 0.3 }}
          >
            <LazyCake
              slug="gilded-three-tier"
              poster="/images/cakes/gilded-three-tier.webp"
              interactive
              autoRotate
              initialRotation={-0.4}
              rotation={rotation}
            />
            <div className="hero-caption">
              <span>Now baking</span>
              <strong>The Gilded Three Tier</strong>
              <span>Drag to turn it</span>
            </div>
          </motion.div>
        </motion.div>
      </div>
      <div className="shell hero-facts">
        {[
          [
            "01",
            "Baked for your date",
            "Nothing waits on a shelf. Your cake is made for the pickup slot you choose.",
          ],
          [
            "02",
            "Eggless, on request",
            "Every cake can be made eggless. Just choose it when you order.",
          ],
          [
            "03",
            "Pay by UPI",
            "Scan, pay, upload the screenshot. We confirm by hand, usually within the hour.",
          ],
        ].map(([n, title, copy], i) => (
          <FadeIn key={n} delay={1.2 + i * 0.1}>
            <span>{n}</span>
            <div>
              <strong>{title}</strong>
              {copy}
            </div>
          </FadeIn>
        ))}
      </div>
    </section>
  );
}
