import Link from "next/link";
export default function NotFound() { return <main className="center-page"><p className="eyebrow">404</p><h1>That page has gone missing.</h1><p>Let’s get you back to the good stuff.</p><Link className="shop-button" href="/shop">Browse cakes</Link></main>; }
