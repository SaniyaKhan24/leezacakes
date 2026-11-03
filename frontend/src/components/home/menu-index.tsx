"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight } from "lucide-react";
import {
  AnimatePresence,
  motion,
  useMotionValue,
  useSpring,
} from "motion/react";
import Link from "next/link";
import { useState } from "react";
import { FadeIn, SplitText } from "@/components/motion";
import { mediaUrl } from "@/components/commerce-ui";
import { api } from "@/lib/api";

/** The menu as a typographic index; a photograph trails the pointer across the rows. */
export function MenuIndex() {
  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: api.categories,
  });
  const [active, setActive] = useState<string | null>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 140, damping: 20, mass: 0.6 });
  const sy = useSpring(y, { stiffness: 140, damping: 20, mass: 0.6 });
  const activeCategory = categories.find((c) => c.slug === active);

  return (
    <section className="section shell" aria-labelledby="menu-title">
      <div className="section-head">
        <div>
          <FadeIn>
            <p className="eyebrow">The menu</p>
          </FadeIn>
          <SplitText text="Five ways to *celebrate.*" />
        </div>
        <FadeIn delay={0.2}>
          <p className="lede">
            Classic layer cakes, glossy chocolate, seasonal fruit, tall tiered
            centrepieces and little lunchbox bentos.
          </p>
        </FadeIn>
      </div>
      <div
        className="menu-index"
        onPointerMove={(event) => {
          x.set(event.clientX + 28);
          y.set(event.clientY - 160);
        }}
        onPointerLeave={() => setActive(null)}
      >
        {categories.map((category, i) => (
          <FadeIn key={category.id} delay={i * 0.06}>
            <Link
              href={`/shop?category=${category.slug}`}
              className="menu-row"
              onPointerEnter={() => setActive(category.slug)}
              onPointerMove={() =>
                active !== category.slug && setActive(category.slug)
              }
              data-cursor="Open"
            >
              <span className="menu-row-index">0{i + 1}</span>
              <h3>{category.name}</h3>
              <p>{category.description}</p>
              <ArrowUpRight
                className="menu-row-arrow"
                size={26}
                strokeWidth={1.2}
              />
            </Link>
          </FadeIn>
        ))}
      </div>
      <AnimatePresence>
        {activeCategory?.image && (
          <motion.div
            className="menu-float"
            style={{ x: sx, y: sy }}
            initial={{ opacity: 0, scale: 0.8, rotate: -4 }}
            animate={{ opacity: 1, scale: 1, rotate: 0 }}
            exit={{ opacity: 0, scale: 0.85 }}
            transition={{ duration: 0.4 }}
          >
            <AnimatePresence mode="popLayout">
              <motion.img
                key={activeCategory.slug}
                src={mediaUrl(activeCategory.image) ?? undefined}
                alt=""
                initial={{ opacity: 0, scale: 1.15 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5 }}
              />
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
