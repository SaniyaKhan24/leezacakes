import type { Metadata } from "next";
import { Suspense } from "react";
import { ShopView } from "./shop-view";

export const metadata: Metadata = { title: "Shop the cakes" };

export default function ShopPage() {
  return (
    <main className="page shell">
      <Suspense fallback={null}>
        <ShopView />
      </Suspense>
    </main>
  );
}
