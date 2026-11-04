"use client";

import { ArrowDown, ArrowRight, Check, ChevronRight } from "lucide-react";
import {
  AnimatePresence,
  motion,
  useMotionValueEvent,
  useScroll,
} from "motion/react";
import Link from "next/link";
import { useRef, useState } from "react";
import { LazyCake } from "@/components/cake/lazy-cake";
import { EASE } from "@/components/motion";

/** Each flavour shows the matching cake from the menu, in 3D. */
const flavors = [
  {
    name: "Chocolate",
    note: "Rich, velvety and indulgent",
    tone: "chocolate",
    slug: "belgian-chocolate",
  },
  {
    name: "Vanilla",
    note: "Soft, fragrant and timeless",
    tone: "vanilla",
    slug: "vanilla-bloom-two-tier",
  },
  {
    name: "Strawberry",
    note: "Bright, fresh and delicate",
    tone: "strawberry",
    slug: "vanilla-berry",
  },
  {
    name: "Red Velvet",
    note: "Cocoa, cream and a little drama",
    tone: "velvet",
    slug: "red-velvet",
  },
];

export function HomeHero() {
  const [selectedFlavor, setSelectedFlavor] = useState(flavors[0]);
  const section = useRef<HTMLElement>(null);
  const rotation = useRef(0);
  // The cake keeps turning as the hero scrolls away.
  const { scrollYProgress } = useScroll({
    target: section,
    offset: ["start start", "end start"],
  });
  useMotionValueEvent(scrollYProgress, "change", (p) => {
    rotation.current = p * Math.PI * 0.9;
  });

  return (
    <>
      <section
        ref={section}
        className="hero-stage shell"
        aria-labelledby="hero-title"
      >
        <div className="hero-stage-copy">
          <p className="hero-eyebrow">Handcrafted for your moments</p>
          <span className="hero-rule" aria-hidden="true" />
          <h1 id="hero-title">
            A little sweetness.
            <br />
            <em>A lot of love.</em>
          </h1>
          <p className="hero-stage-intro">
            Cakes that make every celebration truly special. Thoughtfully
            crafted for your most cherished moments.
          </p>
          <div className="hero-stage-actions">
            <Link className="hero-primary-button" href="/shop">
              Explore Our Cakes <ArrowRight size={16} />
            </Link>
            <Link className="hero-secondary-button" href="/custom">
              Create a Custom Cake <ArrowRight size={16} />
            </Link>
          </div>
          <a className="hero-scroll" href="#perfect-cake">
            <span className="hero-scroll-icon">
              <ArrowDown size={15} />
            </span>
            <span>Scroll to explore</span>
          </a>
        </div>

        <div
          className={`hero-cake-placeholder hero-cake-${selectedFlavor.tone}`}
          role="img"
          aria-label={`A ${selectedFlavor.name.toLowerCase()} cake from the menu, shown in 3D`}
          data-cursor="Drag"
        >
          <div className="hero-cake-glow" aria-hidden="true" />
          <div
            className="hero-cake-confetti hero-confetti-one"
            aria-hidden="true"
          />
          <div
            className="hero-cake-confetti hero-confetti-two"
            aria-hidden="true"
          />
          <div
            className="hero-cake-confetti hero-confetti-three"
            aria-hidden="true"
          />
          <AnimatePresence mode="wait">
            <motion.div
              key={selectedFlavor.slug}
              className="hero-cake-3d"
              initial={{ opacity: 0, scale: 0.92, y: 24 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -16 }}
              transition={{ duration: 0.7, ease: EASE }}
            >
              <LazyCake
                slug={selectedFlavor.slug}
                poster={`/images/cakes/${selectedFlavor.slug}.webp`}
                interactive
                autoRotate
                initialRotation={-0.4}
                rotation={rotation}
                shadowOpacity={0.6}
              />
            </motion.div>
          </AnimatePresence>
          <p className="hero-placeholder-note">{selectedFlavor.note}</p>
        </div>

        <div className="hero-flavor-panel" aria-label="Choose a flavor">
          <p className="hero-flavor-label">Explore the edit</p>
          <div className="hero-flavor-list" role="list">
            {flavors.map((flavor) => {
              const selected = selectedFlavor.name === flavor.name;
              return (
                <button
                  className={`hero-flavor ${selected ? "is-selected" : ""}`}
                  key={flavor.name}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setSelectedFlavor(flavor)}
                >
                  <span
                    className={`flavor-swatch flavor-swatch-${flavor.tone}`}
                    aria-hidden="true"
                  >
                    {selected && <Check size={14} />}
                  </span>
                  <span className="hero-flavor-name">{flavor.name}</span>
                  <ChevronRight className="hero-flavor-arrow" size={16} />
                </button>
              );
            })}
          </div>
          <p className="hero-selected-note" aria-live="polite">
            {selectedFlavor.name} · {selectedFlavor.note}
          </p>
        </div>
      </section>

      <section
        className="perfect-cake-intro shell"
        id="perfect-cake"
        aria-labelledby="perfect-cake-title"
      >
        <div className="motif-divider" aria-hidden="true">
          <span />
          <span className="motif-leaf">✦</span>
          <span />
        </div>
        <p className="eyebrow">Find your moment</p>
        <h2 id="perfect-cake-title">Find Your Perfect Cake</h2>
        <p>Made for every kind of celebration.</p>
      </section>
    </>
  );
}
