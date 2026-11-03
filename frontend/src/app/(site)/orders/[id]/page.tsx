import { Suspense } from "react";
import { OrderView } from "./order-view";

async function Order({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <OrderView id={id} />;
}

export default function OrderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense fallback={<main className="page shell" />}>
      <Order params={params} />
    </Suspense>
  );
}
