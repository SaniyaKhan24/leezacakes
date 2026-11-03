"use client";

import type { ReactNode } from "react";
import { ImageReveal, SplitText, FadeIn } from "@/components/motion";

export function AuthShell({
  eyebrow,
  title,
  art = "pistachio-rose",
  caption,
  children,
}: {
  eyebrow: string;
  title: string;
  art?: string;
  caption?: string;
  children: ReactNode;
}) {
  return (
    <main className="auth-shell">
      <ImageReveal className="auth-art">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className="cake-photo"
          src={`/images/cakes/${art}-studio.webp`}
          alt=""
        />
        {caption && <p className="auth-art-caption">{caption}</p>}
      </ImageReveal>
      <div className="auth-panel">
        <FadeIn>
          <p className="eyebrow">{eyebrow}</p>
        </FadeIn>
        <SplitText as="h1" text={title} />
        <FadeIn delay={0.25}>{children}</FadeIn>
      </div>
    </main>
  );
}
