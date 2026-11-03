import { notFound } from "next/navigation";
import { Suspense } from "react";
import { StudioRender } from "./studio-render";

/**
 * Development-only photo studio. `scripts/render-cakes.mjs` opens this page in a
 * headless browser to photograph each procedural cake for the catalogue seed.
 */
export default function StudioRenderPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return (
    <Suspense fallback={null}>
      <StudioRender />
    </Suspense>
  );
}
