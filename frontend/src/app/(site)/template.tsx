"use client";

import { motion, useReducedMotion } from "motion/react";
import { EASE, EASE_IN_OUT } from "@/components/motion";

/** Every navigation lifts a cream curtain off the incoming page. */
export default function Template({ children }: { children: React.ReactNode }) {
  const reduced = useReducedMotion();
  if (reduced) return <>{children}</>;
  return (
    <>
      <motion.div
        className="page-curtain"
        aria-hidden="true"
        initial={{ scaleY: 1 }}
        animate={{ scaleY: 0 }}
        transition={{ duration: 0.85, ease: EASE_IN_OUT, delay: 0.05 }}
      />
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: EASE, delay: 0.25 }}
      >
        {children}
      </motion.div>
    </>
  );
}
