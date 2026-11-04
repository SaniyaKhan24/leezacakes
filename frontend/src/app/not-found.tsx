import Link from "next/link";

export default function NotFound() {
  return (
    <main className="not-found">
      <div>
        <p className="eyebrow">Page not found</p>
        <h1>
          4<em>0</em>4
        </h1>
        <p className="lede" style={{ margin: "24px auto 36px" }}>
          This page has been eaten. The cakes, happily, are all still here.
        </p>
        <Link href="/shop" className="btn btn-dark">
          <span className="btn-label">Back to the cakes</span>
        </Link>
      </div>
    </main>
  );
}
