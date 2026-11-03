"use client";

import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";
import { useProductPhotos } from "@/components/cart-drawer";
import {
  Button,
  CakePhoto,
  EmptyState,
  Field,
  Notice,
  PageIntro,
  Skeleton,
  TextArea,
  firstError,
} from "@/components/commerce-ui";
import { EASE, FadeIn } from "@/components/motion";
import { useAuth, useCart } from "@/components/providers";
import { SignInForm } from "@/app/(site)/auth/login/sign-in-form";
import { api, type ApiError, type PickupSlot } from "@/lib/api";
import {
  dayParts,
  money,
  newIdempotencyKey,
  slotDay,
  slotRange,
} from "@/lib/format";

export default function CheckoutPage() {
  const { user, loading: authLoading } = useAuth();
  const { cart, loading: cartLoading, reload } = useCart();
  const router = useRouter();
  const { data: photos } = useProductPhotos();
  const items = cart?.items ?? [];
  const slots = useQuery({
    queryKey: ["pickup-slots", user?.id, cart?.id, items.length],
    queryFn: api.pickupSlots,
    enabled: Boolean(user && items.length),
  });
  const [pickedDay, setDay] = useState<string | null>(null);
  const [slot, setSlot] = useState<PickupSlot | null>(null);
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);

  const openDays = useMemo(
    () =>
      (slots.data?.days ?? []).filter((d) => d.slots.some((s) => s.available)),
    [slots.data],
  );
  const day = pickedDay ?? openDays[0]?.date ?? null;
  const selectedDay = slots.data?.days.find((d) => d.date === day);

  if (authLoading || cartLoading) {
    return (
      <main className="page shell">
        <Skeleton className="sk-block" />
      </main>
    );
  }
  if (!items.length) {
    return (
      <main className="page shell">
        <PageIntro eyebrow="Checkout" title="Your bag is *empty.*" />
        <EmptyState
          title="Nothing to check out."
          copy="Add a cake first, then come back to choose your pickup time."
          href="/shop"
          label="Browse the cakes"
        />
      </main>
    );
  }
  if (!user) {
    return (
      <main className="page shell">
        <PageIntro
          eyebrow="Checkout"
          title="First, *who's it for?*"
          copy="Sign in so your order, payment and pickup details stay together. Your bag comes with you."
        />
        <div className="auth-gate">
          <div className="auth-card">
            <h2>Sign in</h2>
            <SignInForm onDone={() => undefined} />
          </div>
          <div className="auth-card">
            <h2>New here?</h2>
            <p>
              Create an account in a minute. We&apos;ll email a link to confirm
              it&apos;s you, then bring you straight back here.
            </p>
            <Link className="btn btn-line" href="/auth/register?next=/checkout">
              <span className="btn-label">Create an account</span>
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const place = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!slot) {
      setError(
        Object.assign(new Error("Choose a pickup time first."), {
          fields: {},
        }) as ApiError,
      );
      return;
    }
    const form = new FormData(event.currentTarget);
    setPlacing(true);
    setError(null);
    try {
      const order = await api.createOrder(
        {
          customer_name: String(form.get("name") ?? ""),
          customer_phone: String(form.get("phone") ?? ""),
          customer_email: String(form.get("email") ?? ""),
          pickup_slot_start: slot.start,
          pickup_slot_end: slot.end,
          customer_note: String(form.get("note") ?? ""),
        },
        key,
      );
      await reload();
      router.push(`/orders/${order.id}?placed=1`);
    } catch (e) {
      setError(e as ApiError);
      if ((e as ApiError).fields?.pickup_slot) void slots.refetch();
      setPlacing(false);
    }
  };

  return (
    <main className="page shell">
      <PageIntro eyebrow="Checkout" title="When shall we *have it ready?*" />
      <form className="checkout-layout" onSubmit={place}>
        <div>
          <FadeIn className="checkout-step">
            <div className="checkout-step-head">
              <span>i.</span>
              <h2>Your details</h2>
            </div>
            <div className="form-grid">
              <Field
                label="Name for the order"
                name="name"
                required
                defaultValue={`${user.first_name} ${user.last_name}`.trim()}
                autoComplete="name"
                error={firstError(error?.fields, "customer_name")}
              />
              <Field
                label="Phone"
                name="phone"
                type="tel"
                required
                defaultValue={user.phone_number}
                autoComplete="tel"
                placeholder="+91 98xxx xxxxx"
                error={firstError(error?.fields, "customer_phone")}
                hint="We'll call only if something needs your attention."
              />
              <Field
                label="Email"
                name="email"
                type="email"
                defaultValue={user.email}
                autoComplete="email"
                className="span-2"
                error={firstError(error?.fields, "customer_email")}
              />
            </div>
          </FadeIn>

          <FadeIn className="checkout-step" delay={0.1}>
            <div className="checkout-step-head">
              <span>ii.</span>
              <h2>Pickup time</h2>
            </div>
            {slots.isLoading ? (
              <Skeleton className="sk-line" />
            ) : slots.isError ? (
              <Notice tone="error">
                We couldn&apos;t load pickup times. Please refresh.
              </Notice>
            ) : (
              <>
                <LayoutGroup id="days">
                  <div
                    className="day-strip"
                    aria-label="Pickup day"
                    data-lenis-prevent
                  >
                    {(slots.data?.days ?? []).map((d) => {
                      const parts = dayParts(d.date);
                      const open = d.slots.some((s) => s.available);
                      return (
                        <button
                          key={d.date}
                          type="button"
                          className={`day ${day === d.date ? "is-selected" : ""}`}
                          disabled={!open}
                          onClick={() => {
                            setDay(d.date);
                            setSlot(null);
                          }}
                          aria-pressed={day === d.date}
                          title={
                            open ? undefined : "No pickup times left this day"
                          }
                        >
                          {day === d.date && (
                            <motion.span
                              layoutId="day-bg"
                              className="day-bg"
                              transition={{
                                type: "spring",
                                stiffness: 380,
                                damping: 32,
                              }}
                            />
                          )}
                          <small>{parts.weekday}</small>
                          <strong>{parts.day}</strong>
                          <small>{parts.month}</small>
                        </button>
                      );
                    })}
                  </div>
                </LayoutGroup>
                <AnimatePresence mode="wait">
                  <motion.div
                    key={day ?? "none"}
                    className="slots"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.35, ease: EASE }}
                  >
                    {selectedDay?.slots.map((s) => (
                      <button
                        key={s.start}
                        type="button"
                        className={`slot ${slot?.start === s.start ? "is-selected" : ""}`}
                        disabled={!s.available}
                        onClick={() => setSlot(s)}
                      >
                        {slotRange(s.start, s.end)}
                      </button>
                    ))}
                  </motion.div>
                </AnimatePresence>
                {slots.data && (
                  <p className="lead-note">
                    Your bag needs at least{" "}
                    {Math.round(slots.data.lead_time_minutes / 60)} hours&apos;
                    notice, so earlier times are greyed out.
                  </p>
                )}
                {firstError(error?.fields, "pickup_slot") && (
                  <Notice tone="error">
                    {firstError(error?.fields, "pickup_slot")}
                  </Notice>
                )}
              </>
            )}
          </FadeIn>

          <FadeIn className="checkout-step" delay={0.2}>
            <div className="checkout-step-head">
              <span>iii.</span>
              <h2>Anything we should know?</h2>
            </div>
            <TextArea
              label="Order note (optional)"
              name="note"
              maxLength={1000}
              placeholder="Allergies, a surprise to keep quiet, who's collecting…"
            />
          </FadeIn>
        </div>

        <aside className="summary">
          <h2>Your order</h2>
          <ul className="summary-items">
            {items.map((item) => (
              <li key={item.id}>
                <div>
                  <CakePhoto src={photos?.[item.product.slug]} alt="" />
                </div>
                <div>
                  {item.quantity > 1 && (
                    <span className="tabular">{item.quantity} × </span>
                  )}
                  {item.product.name}
                  <small>
                    {[
                      item.variant?.name,
                      ...item.customizations.map(
                        (c) =>
                          c.choice_name ??
                          (c.text_value ? `“${c.text_value}”` : null),
                      ),
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </small>
                </div>
                <strong className="tabular">{money(item.line_subtotal)}</strong>
              </li>
            ))}
          </ul>
          <div className="summary-row">
            <span>Pickup</span>
            <strong>
              {slot
                ? `${slotDay(slot.start)}, ${slotRange(slot.start, slot.end)}`
                : "Choose a time"}
            </strong>
          </div>
          <div className="summary-total">
            <span>Total</span>
            <strong className="tabular">{money(cart?.subtotal)}</strong>
          </div>
          <p className="drawer-note" style={{ textAlign: "left" }}>
            Your order page shows the final total and a UPI QR code. Pay there,
            upload the screenshot, and we confirm once we see it.
          </p>
          {error && !firstError(error.fields, "pickup_slot") && (
            <Notice tone="error">{error.message}</Notice>
          )}
          <Button
            type="submit"
            loading={placing}
            className="btn-block"
            disabled={!slot}
          >
            Place order
          </Button>
        </aside>
      </form>
    </main>
  );
}
