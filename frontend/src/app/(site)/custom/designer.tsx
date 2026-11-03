"use client";

import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
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
  Notice,
  Skeleton,
  Stepper,
} from "@/components/commerce-ui";
import { EnquiryForm } from "@/components/enquiry-form";
import { EASE, FadeIn, RollingNumber, SplitText } from "@/components/motion";
import { useCart } from "@/components/providers";
import { api } from "@/lib/api";
import { leadTime, money } from "@/lib/format";

export function Designer() {
  const params = useSearchParams();
  const products = useQuery({
    queryKey: ["products", "all"],
    queryFn: () => api.products("?page_size=100"),
  });
  const list = products.data ?? [];
  const [chosen, setChosen] = useState<string | null>(params.get("cake"));
  const slug =
    chosen && list.some((p) => p.slug === chosen)
      ? chosen
      : (list.find((p) => p.slug === "vanilla-berry") ?? list[0])?.slug;
  const product = list.find((p) => p.slug === slug);
  const builder = useCakeBuilder(product);
  const { add, setDrawerOpen } = useCart();
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  const addToBag = async () => {
    if (!product) return;
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
        product_id: product.id,
        variant_id: builder.variant?.id ?? null,
        quantity: builder.quantity,
        selections: builder.selections,
      });
      toast.success("Your cake is in the bag.");
      setDrawerOpen(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAdding(false);
    }
  };

  return (
    <main>
      <section className="configurator">
        <div className="configurator-stage" data-cursor="Drag">
          <div className="configurator-stage-inner">
            <AnimatePresence mode="wait">
              {product && (
                <motion.div
                  key={product.slug}
                  style={{ position: "absolute", inset: 0 }}
                  initial={{ opacity: 0, scale: 0.94, y: 30 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.96, y: -20 }}
                  transition={{ duration: 0.8, ease: EASE }}
                >
                  <LazyCake
                    slug={product.slug}
                    poster={`/images/cakes/${product.slug}.webp`}
                    extras={builder.extras}
                    interactive
                    autoRotate
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <div className="configurator-name">
            <p className="eyebrow">
              {product?.category.name ?? "The designer"}
            </p>
            <AnimatePresence mode="wait">
              <motion.h2
                key={product?.slug ?? "none"}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.6, ease: EASE }}
              >
                {product?.name ?? " "}
              </motion.h2>
            </AnimatePresence>
          </div>
          <div className="configurator-total">
            <span>Your cake</span>
            <strong>
              <RollingNumber
                value={builder.unit * builder.quantity}
                format={(n) => money(n)}
              />
            </strong>
          </div>
        </div>

        <div className="configurator-panel">
          <FadeIn>
            <p className="eyebrow">The cake designer</p>
          </FadeIn>
          <SplitText as="h1" text="Build it, *watch it* come together." />
          <FadeIn delay={0.2}>
            <p className="lede" style={{ margin: "18px 0 30px" }}>
              Start from any cake on the menu, then make it yours. Everything
              you change appears on the cake as you go.
            </p>
          </FadeIn>
          <fieldset className="option-group">
            <legend>
              Start with <small>{list.length} cakes</small>
            </legend>
            {products.isLoading ? (
              <Skeleton className="sk-block" />
            ) : (
              <div className="base-picker">
                {list.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className={p.slug === slug ? "is-selected" : ""}
                    onClick={() => setChosen(p.slug)}
                    aria-pressed={p.slug === slug}
                  >
                    <div>
                      <CakePhoto src={p.primary_image?.url} alt="" />
                    </div>
                    {p.name}
                  </button>
                ))}
              </div>
            )}
          </fieldset>
          <SizePicker builder={builder} />
          <OptionFields builder={builder} />
          <div className="pdp-buy">
            <Stepper
              value={builder.quantity}
              onChange={builder.setQuantity}
              max={10}
            />
            <Button onClick={addToBag} loading={adding} disabled={!product}>
              Add to bag
            </Button>
          </div>
          {error && <Notice tone="error">{error}</Notice>}
          {product?.preparation_time ? (
            <p className="lead-note">
              This cake needs {leadTime(product.preparation_time)}. You&apos;ll
              pick a pickup time at checkout.
            </p>
          ) : null}
        </div>
      </section>

      <section
        className="shell bespoke"
        style={{ paddingBottom: "var(--section)" }}
      >
        <div>
          <FadeIn>
            <p className="eyebrow">Something bigger?</p>
          </FadeIn>
          <SplitText text="Weddings, milestones, *the impossible.*" />
          <FadeIn delay={0.2}>
            <p className="lede">
              For tall tiers, sculpted cakes or anything not on the menu, tell
              us what you&apos;re imagining. We&apos;ll come back with a sketch,
              a price and a date.
            </p>
          </FadeIn>
        </div>
        <FadeIn delay={0.15}>
          <EnquiryForm defaultKind="custom_cake" />
        </FadeIn>
      </section>
    </main>
  );
}
