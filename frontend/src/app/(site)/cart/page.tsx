"use client";

import { AnimatePresence } from "motion/react";
import Link from "next/link";
import { toast } from "sonner";
import { CartLine, useProductPhotos } from "@/components/cart-drawer";
import {
  Button,
  ButtonLink,
  EmptyState,
  Notice,
  PageIntro,
  Skeleton,
} from "@/components/commerce-ui";
import { RollingNumber } from "@/components/motion";
import { useCart } from "@/components/providers";
import { api } from "@/lib/api";
import { money } from "@/lib/format";

export default function CartPage() {
  const { cart, loading, reload } = useCart();
  const { data: photos } = useProductPhotos();
  const items = cart?.items ?? [];
  return (
    <main className="page shell">
      <PageIntro
        eyebrow="Your bag"
        title={items.length ? "Nearly *there.*" : "Your bag."}
      />
      {loading ? (
        <Skeleton className="sk-block" />
      ) : items.length === 0 ? (
        <EmptyState
          title="Nothing in here yet."
          copy="Every cake is baked for the day you pick it up — so there's always room for one more."
          href="/shop"
          label="Browse the cakes"
        />
      ) : (
        <div className="cart-layout">
          <ul className="cart-lines">
            <AnimatePresence initial={false}>
              {items.map((item) => (
                <CartLine
                  key={item.id}
                  item={item}
                  photo={photos?.[item.product.slug]}
                />
              ))}
            </AnimatePresence>
          </ul>
          <aside className="summary">
            <h2>Summary</h2>
            <div className="summary-row">
              <span>Cakes</span>
              <strong className="tabular">
                {items.reduce((s, i) => s + i.quantity, 0)}
              </strong>
            </div>
            <div className="summary-row">
              <span>Pickup</span>
              <strong>Free, from the studio</strong>
            </div>
            <div className="summary-total">
              <span>Subtotal</span>
              <strong>
                <RollingNumber
                  value={Number(cart?.subtotal ?? 0)}
                  format={(n) => money(n)}
                />
              </strong>
            </div>
            {cart?.price_confirmation_required && (
              <Notice tone="error">
                Some prices changed since you added them.{" "}
                <Button
                  variant="line"
                  onClick={async () => {
                    try {
                      await api.confirmPrices();
                      await reload();
                      toast.success("Prices updated.");
                    } catch (e) {
                      toast.error((e as Error).message);
                    }
                  }}
                >
                  Accept new prices
                </Button>
              </Notice>
            )}
            <ButtonLink href="/checkout" className="btn-block">
              Choose a pickup time
            </ButtonLink>
            <Link
              href="/shop"
              className="text-link"
              style={{ justifySelf: "center" }}
            >
              Keep browsing
            </Link>
          </aside>
        </div>
      )}
    </main>
  );
}
