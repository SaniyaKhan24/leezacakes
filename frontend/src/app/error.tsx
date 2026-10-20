"use client";
export default function ErrorPage({ reset }: { reset: () => void }) { return <main className="center-page"><p className="eyebrow">A small hiccup</p><h1>We couldn’t load this page.</h1><button className="shop-button" onClick={reset}>Try again</button></main>; }
