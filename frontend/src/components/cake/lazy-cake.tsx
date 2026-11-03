"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type { CakeStageProps } from "./cake-stage";

/**
 * The WebGL stage loads after first paint. Until it has drawn (and wherever
 * WebGL is unavailable) a photograph of the very same cake holds its place.
 */
const Stage = dynamic(() => import("./cake-stage").then((m) => m.CakeStage), {
  ssr: false,
  loading: () => null,
});

export function LazyCake({
  poster,
  posterAlt = "",
  ...props
}: CakeStageProps & { poster?: string | null; posterAlt?: string }) {
  const [ready, setReady] = useState(false);
  return (
    <div
      className={`lazy-cake ${ready ? "is-ready" : ""}`}
      style={{ position: "relative", width: "100%", height: "100%" }}
    >
      {poster && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          className="lazy-cake-poster"
          src={poster}
          alt={posterAlt}
          aria-hidden={!posterAlt}
        />
      )}
      <div className="lazy-cake-canvas">
        <Stage
          {...props}
          onReady={() => {
            // Let the first frames land before the poster dissolves.
            window.setTimeout(() => setReady(true), 350);
            props.onReady?.();
          }}
        />
      </div>
    </div>
  );
}
