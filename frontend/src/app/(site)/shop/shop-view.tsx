"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import {
  EmptyState,
  Notice,
  PageIntro,
  ProductCard,
  Skeleton,
} from "@/components/commerce-ui";
import { api } from "@/lib/api";

const SORTS = {
  featured: "Our picks first",
  "price-asc": "Price, low to high",
  "price-desc": "Price, high to low",
  name: "A to Z",
} as const;

export function ShopView() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const category = params.get("category") ?? "";
  const [query, setQuery] = useState(params.get("q") ?? "");
  const [sort, setSort] = useState<keyof typeof SORTS>("featured");
  const products = useQuery({
    queryKey: ["products", "all"],
    queryFn: () => api.products("?page_size=100"),
  });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: api.categories,
  });

  const setCategory = (slug: string) => {
    const next = new URLSearchParams(params.toString());
    if (slug) next.set("category", slug);
    else next.delete("category");
    router.replace(`${pathname}${next.size ? `?${next}` : ""}`, {
      scroll: false,
    });
  };

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const price = (p: {
      effective_price: string | null;
      base_price: string | null;
    }) => Number(p.effective_price ?? p.base_price ?? 0);
    const rows = (products.data ?? []).filter(
      (p) =>
        (!category || p.category.slug === category) &&
        (!needle ||
          `${p.name} ${p.short_description} ${p.description} ${p.category.name}`
            .toLowerCase()
            .includes(needle)),
    );
    return rows.sort((a, b) => {
      if (sort === "price-asc") return price(a) - price(b);
      if (sort === "price-desc") return price(b) - price(a);
      if (sort === "name") return a.name.localeCompare(b.name);
      return (
        Number(b.is_featured) - Number(a.is_featured) ||
        a.category.name.localeCompare(b.category.name)
      );
    });
  }, [products.data, category, query, sort]);

  const activeCategory = categories.data?.find((c) => c.slug === category);

  return (
    <>
      <PageIntro
        eyebrow={activeCategory ? "The menu" : "The whole menu"}
        title={
          activeCategory ? activeCategory.name : "Every cake, *baked to order.*"
        }
        copy={
          activeCategory?.description ||
          "Sizes, prices and finishing touches are on each cake's page. Everything can be made eggless."
        }
      />
      <div className="shop-toolbar">
        <LayoutGroup id="chips">
          <div className="chips" role="tablist" aria-label="Filter by category">
            {[{ slug: "", name: "All" }, ...(categories.data ?? [])].map(
              (c) => (
                <button
                  key={c.slug || "all"}
                  type="button"
                  role="tab"
                  aria-selected={category === c.slug}
                  className={`chip ${category === c.slug ? "is-active" : ""}`}
                  onClick={() => setCategory(c.slug)}
                >
                  {category === c.slug && (
                    <motion.span
                      layoutId="chip-bg"
                      className="chip-bg"
                      transition={{
                        type: "spring",
                        stiffness: 380,
                        damping: 32,
                      }}
                    />
                  )}
                  {c.name}
                </button>
              ),
            )}
          </div>
        </LayoutGroup>
        <div className="shop-search">
          <Search size={16} aria-hidden="true" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search — pistachio, eggless, tiered…"
            aria-label="Search cakes"
          />
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as keyof typeof SORTS)}
            aria-label="Sort"
          >
            {Object.entries(SORTS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>
      {products.isError && (
        <Notice tone="error">
          We couldn&apos;t load the menu just now. Please refresh in a moment.
        </Notice>
      )}
      {products.isLoading ? (
        <div className="product-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="card-skeleton" />
          ))}
        </div>
      ) : (
        <>
          <p className="shop-count tabular">
            {visible.length} {visible.length === 1 ? "cake" : "cakes"}
          </p>
          {visible.length === 0 ? (
            <EmptyState
              title="Nothing matches that."
              copy="Try a different word, or ask us — most flavours can be made to order."
              href="/contact"
              label="Ask the bakery"
            />
          ) : (
            <motion.div className="product-grid" layout>
              <AnimatePresence mode="popLayout">
                {visible.map((product, i) => (
                  <motion.div
                    key={product.id}
                    layout
                    initial={{ opacity: 0, scale: 0.96 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.96 }}
                    transition={{ duration: 0.5 }}
                  >
                    <ProductCard product={product} index={i} />
                  </motion.div>
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </>
      )}
    </>
  );
}
