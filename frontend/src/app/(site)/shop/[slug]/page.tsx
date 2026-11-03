import { Suspense } from "react";
import { ProductView } from "./product-view";

async function Product({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <ProductView slug={slug} />;
}

export default function ProductPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  return (
    <Suspense fallback={<main className="page shell" />}>
      <Product params={params} />
    </Suspense>
  );
}
