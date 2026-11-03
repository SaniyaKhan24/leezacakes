import type { Metadata } from "next";
import { Suspense } from "react";
import { Designer } from "./designer";

export const metadata: Metadata = { title: "Design a cake" };

export default function CustomPage() {
  return (
    <Suspense fallback={null}>
      <Designer />
    </Suspense>
  );
}
