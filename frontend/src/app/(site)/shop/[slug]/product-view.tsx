"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  OptionFields,
  SizePicker,
  useCakeBuilder,
} from "@/components/cake-builder";
import { LazyCake } from "@/components/cake/lazy-cake";
import {
  Button,
  CakePhoto,
  EmptyState,
  Notice,
  ProductCard,
  Skeleton,
  Stepper,
} from "@/components/commerce-ui";
import { EASE, FadeIn, RollingNumber, SplitText } from "@/components/motion";
import { useCart } from "@/components/providers";
import { api } from "@/lib/api";
import { leadTime, money } from "@/lib/format";

type View = "3d" | "inside" | "photos";

export function ProductView({ slug }: { slug: string }) {
  const product = useQuery({
    queryKey: ["product", slug],
    queryFn: () => api.product(slug),
  });
  const all = useQuery({
    queryKey: ["products", "all"],
    queryFn: () => api.products("?page_size=100"),
  });
  const builder = useCakeBuilder(product.data);
  const { add, setDrawerOpen } = useCart();
  const [view, setView] = useState<View>("3d");
  const [photo, setPhoto] = useState(0);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const slice = useRef(0);
  useEffect(() => {
    slice.current = view === "inside" ? 1 : 0;
  }, [view]);

  if (product.isError) {
    return (
      <main className="page shell">
        <EmptyState
          title="That cake isn't on the menu."
          copy="It may have been retired for the season. Everything currently available is in the shop."
          href="/shop"
          label="Back to the shop"
        />
      </main>
    );
  }
  const p = product.data;
  const photos = [...(p?.images ?? [])].sort(
    (a, b) =>
      Number(b.is_primary) - Number(a.is_primary) ||
      a.sort_order - b.sort_order,
  );
  const related = (all.data ?? [])
    .filter((x) => x.slug !== slug && x.category.slug === p?.category.slug)
    .slice(0, 3);
  const notice = leadTime(p?.preparation_time);

  const addToBag = async () => {
    if (!p) return;
    setError("");
    if (builder.missing.length) {
      setError(
        `Please choose: ${builder.missing.map((m) => m.option.name.toLowerCase()).join(", ")}.`,
      );
      return;
    }
    setAdding(true);
    try {
      await add({
        product_id: p.id,
        variant_id: builder.variant?.id ?? null,
        quantity: builder.quantity,
        selections: builder.selections,
      });
      toast.success(`${p.name} is in your bag.`);
      setDrawerOpen(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAdding(false);
    }
  };

  return (
    <main className="page shell">
      <FadeIn>
        <Link
          href={p ? `/shop?category=${p.category.slug}` : "/shop"}
          className="text-link"
          style={{ marginBottom: 36 }}
        >
          <ArrowLeft size={14} /> {p?.category.name ?? "Shop"}
        </Link>
      </FadeIn>
      <div className="pdp">
        <div className="pdp-media">
          <div
            className="pdp-stage"
            data-cursor={view === "photos" ? undefined : "Drag"}
          >
            <LayoutGroup id="view">
              <div
                className="view-toggle"
                role="tablist"
                aria-label="Choose a view"
              >
                {(
                  [
                    ["3d", "3D"],
                    ["inside", "Inside"],
                    ["photos", "Photos"],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={view === key}
                    className={view === key ? "is-active" : ""}
                    onClick={() => setView(key)}
                  >
                    {view === key && (
                      <motion.span
                        layoutId="view-bg"
                        className="chip-bg"
                        transition={{
                          type: "spring",
                          stiffness: 400,
                          damping: 34,
                        }}
                      />
                    )}
                    {label}
                  </button>
                ))}
              </div>
            </LayoutGroup>
            <AnimatePresence mode="wait">
              {view === "photos" ? (
                <motion.div
                  key="photos"
                  style={{ position: "absolute", inset: 0 }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.5, ease: EASE }}
                >
                  <AnimatePresence mode="popLayout">
                    <motion.div
                      key={photo}
                      style={{ position: "absolute", inset: 0 }}
                      initial={{ opacity: 0, scale: 1.04 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.7, ease: EASE }}
                    >
                      <CakePhoto
                        src={photos[photo]?.url}
                        alt={photos[photo]?.alt_text ?? p?.name ?? ""}
                        priority
                      />
                    </motion.div>
                  </AnimatePresence>
                </motion.div>
              ) : (
                <motion.div
                  key="stage"
                  style={{ position: "absolute", inset: 0 }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.5 }}
                >
                  {p && (
                    <LazyCake
                      slug={p.slug}
                      poster={`/images/cakes/${p.slug}.webp`}
                      extras={builder.extras}
                      slice={slice}
                      interactive
                      autoRotate={view === "3d"}
                      initialRotation={-0.5}
                    />
                  )}
                </motion.div>
              )}
            </AnimatePresence>
            {view !== "photos" && (
              <span className="pdp-stage-hint">
                {view === "inside"
                  ? "The layers inside"
                  : "Drag to turn · Changes show live"}
              </span>
            )}
          </div>
          {view === "photos" && photos.length > 1 && (
            <div className="pdp-thumbs">
              {photos.map((img, i) => (
                <button
                  key={img.id}
                  type="button"
                  className={photo === i ? "is-active" : ""}
                  onClick={() => setPhoto(i)}
                  aria-label={`Photo ${i + 1}`}
                >
                  <CakePhoto src={img.url} alt="" />
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="pdp-info">
          {!p ? (
            <div style={{ display: "grid", gap: 16 }}>
              <Skeleton className="sk-title" />
              <Skeleton className="sk-line" />
              <Skeleton className="sk-block" />
            </div>
          ) : (
            <>
              <FadeIn>
                <p className="eyebrow">{p.category.name}</p>
              </FadeIn>
              <SplitText as="h1" text={p.name} key={p.slug} />
              <FadeIn delay={0.2}>
                {p.short_description && (
                  <p className="pdp-short">{p.short_description}</p>
                )}
                <p className="pdp-desc">{p.description}</p>
                <div className="pdp-price" aria-live="polite">
                  <RollingNumber
                    value={builder.unit * builder.quantity}
                    format={(n) => money(n)}
                  />
                  {builder.quantity > 1 && (
                    <small className="tabular">
                      {money(builder.unit)} each
                    </small>
                  )}
                </div>
                <ul className="pdp-meta">
                  {notice && <li>Needs {notice}</li>}
                  <li>Pickup only</li>
                  <li>Can be made eggless</li>
                </ul>
              </FadeIn>
              <FadeIn delay={0.3}>
                <SizePicker builder={builder} />
                {builder.options.isLoading ? (
                  <Skeleton className="sk-block" />
                ) : (
                  <OptionFields builder={builder} />
                )}
                <div className="pdp-buy">
                  <Stepper
                    value={builder.quantity}
                    onChange={builder.setQuantity}
                    max={10}
                  />
                  <Button
                    onClick={addToBag}
                    loading={adding}
                    disabled={!builder.variant && !p.base_price}
                  >
                    Add to bag —{" "}
                    <span className="tabular">
                      {money(builder.unit * builder.quantity)}
                    </span>
                  </Button>
                </div>
                {error && <Notice tone="error">{error}</Notice>}
                <div className="pdp-assurance">
                  <p style={{ margin: 0 }}>
                    <strong>Baked for your pickup time.</strong> You&apos;ll
                    choose a day and hour at checkout
                    {notice ? ` — this cake needs ${notice}` : ""}.
                  </p>
                  <p style={{ margin: 0 }}>
                    <strong>Pay by UPI after ordering.</strong> Scan the QR on
                    your order page, upload the screenshot, and we confirm it by
                    hand.
                  </p>
                </div>
                <details className="accordion" style={{ marginTop: 26 }}>
                  <summary>Storage &amp; serving</summary>
                  <p>
                    Keep refrigerated and bring to room temperature for 30–40
                    minutes before serving. Best within two days.
                  </p>
                </details>
                <details className="accordion">
                  <summary>Allergens</summary>
                  <p>
                    Made in a kitchen that handles wheat, dairy, eggs, nuts and
                    soy. Choose eggless above if you need it; tell us about
                    other allergies in the order note.
                  </p>
                </details>
              </FadeIn>
            </>
          )}
        </div>
      </div>

      {related.length > 0 && (
        <section className="related">
          <div className="section-head">
            <SplitText text="More from the *same shelf.*" />
          </div>
          <div className="product-grid">
            {related.map((r, i) => (
              <ProductCard key={r.id} product={r} index={i} />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
