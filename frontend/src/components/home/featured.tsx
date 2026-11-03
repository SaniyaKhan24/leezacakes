"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ProductCard, Skeleton } from "@/components/commerce-ui";
import { FadeIn, SplitText } from "@/components/motion";
import { api } from "@/lib/api";

export function Featured() {
  const { data: products, isLoading } = useQuery({
    queryKey: ["products", "all"],
    queryFn: () => api.products("?page_size=100"),
  });
  const featured = (products ?? []).filter((p) => p.is_featured);
  return (
    <section className="section shell" aria-labelledby="featured-title">
      <div className="section-head">
        <div>
          <FadeIn>
            <p className="eyebrow">Most ordered</p>
          </FadeIn>
          <SplitText text="The ones people *come back* for." />
        </div>
        <FadeIn delay={0.2}>
          <Link href="/shop" className="text-link">
            See every cake
          </Link>
        </FadeIn>
      </div>
      <div className="rail" data-lenis-prevent-wheel="false">
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="rail-skeleton" />
            ))
          : featured.map((product, i) => (
              <ProductCard key={product.id} product={product} index={i} />
            ))}
      </div>
    </section>
  );
}
