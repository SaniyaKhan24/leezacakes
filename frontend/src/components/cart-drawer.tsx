"use client";

import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";
import { ButtonLink, CakePhoto, Stepper } from "@/components/commerce-ui";
import { EASE, EASE_IN_OUT, RollingNumber } from "@/components/motion";
import { useCart } from "@/components/providers";
import { api, type CartItem } from "@/lib/api";
import { money } from "@/lib/format";

export function useProductPhotos() {
  return useQuery({
    queryKey: ["catalog", "photos"],
    queryFn: async () => {
      const products = await api.products("?page_size=100");
      return Object.fromEntries(
        products.map((p) => [
          p.slug,
          p.primary_image?.url ?? p.images[0]?.url ?? null,
        ]),
      );
    },
    staleTime: 5 * 60_000,
  });
}

export function CartLine({
  item,
  photo,
  compact = false,
}: {
  item: CartItem;
  photo?: string | null;
  compact?: boolean;
}) {
  const { update, remove } = useCart();
  const change = async (quantity: number) => {
    try {
      await update(item.id, quantity);
    } catch (error) {
      toast.error((error as Error).message);
    }
  };
  return (
    <motion.li
      layout
      className={`cart-line ${compact ? "is-compact" : ""}`}
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -24, height: 0, paddingBlock: 0 }}
      transition={{ duration: 0.5, ease: EASE }}
    >
      <Link href={`/shop/${item.product.slug}`} className="cart-line-media">
        <CakePhoto src={photo} alt={item.product.name} />
      </Link>
      <div className="cart-line-body">
        <div className="cart-line-head">
          <Link href={`/shop/${item.product.slug}`}>
            <h3>{item.product.name}</h3>
          </Link>
          <strong className="tabular">{money(item.line_subtotal)}</strong>
        </div>
        {item.variant && <p className="cart-line-meta">{item.variant.name}</p>}
        {item.customizations.length > 0 && (
          <ul className="cart-line-options">
            {item.customizations.map((c, i) => (
              <li key={`${c.option_id}-${i}`}>
                <span>{c.option_name}</span>
                {c.choice_name ?? (c.text_value ? `“${c.text_value}”` : "")}
                {Number(c.price_adjustment) > 0 && (
                  <em> +{money(c.price_adjustment)}</em>
                )}
              </li>
            ))}
          </ul>
        )}
        <div className="cart-line-actions">
          <Stepper value={item.quantity} onChange={change} />
          <button
            type="button"
            className="link-button"
            onClick={() =>
              remove(item.id).catch((e) => toast.error((e as Error).message))
            }
          >
            Remove
          </button>
        </div>
        {item.price_confirmation_required && (
          <p className="cart-line-warning">
            The price changed since you added this. Review it in your bag.
          </p>
        )}
      </div>
    </motion.li>
  );
}

export function CartDrawer() {
  const { cart, count, drawerOpen, setDrawerOpen } = useCart();
  const pathname = usePathname();
  const { data: photos } = useProductPhotos();
  useEffect(() => setDrawerOpen(false), [pathname, setDrawerOpen]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) =>
      event.key === "Escape" && setDrawerOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setDrawerOpen]);
  const items = cart?.items ?? [];
  return (
    <AnimatePresence>
      {drawerOpen && (
        <>
          <motion.div
            className="drawer-scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setDrawerOpen(false)}
          />
          <motion.aside
            className="drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Your bag"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.75, ease: EASE_IN_OUT }}
            data-lenis-prevent
          >
            <header className="drawer-head">
              <h2>
                Your bag <sup className="tabular">{count}</sup>
              </h2>
              <button
                type="button"
                className="icon-button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close bag"
              >
                <X size={18} />
              </button>
            </header>
            {items.length === 0 ? (
              <div className="drawer-empty">
                <p>
                  Nothing here yet. The good news: everything is baked to order,
                  so there&apos;s always room.
                </p>
                <ButtonLink href="/shop">Browse the cakes</ButtonLink>
              </div>
            ) : (
              <>
                <ul className="drawer-lines">
                  <AnimatePresence initial={false}>
                    {items.map((item) => (
                      <CartLine
                        key={item.id}
                        item={item}
                        photo={photos?.[item.product.slug]}
                        compact
                      />
                    ))}
                  </AnimatePresence>
                </ul>
                <footer className="drawer-foot">
                  <div className="drawer-total">
                    <span>Subtotal</span>
                    <strong>
                      <RollingNumber
                        value={Number(cart?.subtotal ?? 0)}
                        format={(n) => money(n)}
                      />
                    </strong>
                  </div>
                  <p className="drawer-note">
                    Choose your pickup time at checkout. Pay by UPI once your
                    order is placed.
                  </p>
                  <ButtonLink href="/checkout" className="btn-block">
                    Checkout
                  </ButtonLink>
                  <Link href="/cart" className="text-link">
                    View bag
                  </Link>
                </footer>
              </>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
