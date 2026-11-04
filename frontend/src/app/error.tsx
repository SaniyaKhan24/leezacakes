"use client";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="not-found">
      <div>
        <p className="eyebrow">Something went wrong</p>
        <h2 style={{ fontSize: "clamp(56px, 8vw, 120px)" }}>
          A <em>sunken</em> sponge.
        </h2>
        <p className="lede" style={{ margin: "24px auto 36px" }}>
          That page didn&apos;t come out of the oven right. Please try again.
        </p>
        <button type="button" className="btn btn-dark" onClick={reset}>
          <span className="btn-label">Try again</span>
        </button>
      </div>
    </main>
  );
}
