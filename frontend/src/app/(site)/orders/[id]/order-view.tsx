"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, UploadCloud } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import QRCode from "qrcode";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useProductPhotos } from "@/components/cart-drawer";
import {
  CakePhoto,
  EmptyState,
  Notice,
  Skeleton,
} from "@/components/commerce-ui";
import { EASE, FadeIn, SplitText } from "@/components/motion";
import { useAuth } from "@/components/providers";
import { WhatsAppCta } from "@/components/whatsapp";
import { api, type Order, type Payment } from "@/lib/api";
import { orderEnquiryText } from "@/lib/whatsapp";
import {
  ORDER_STEPS,
  money,
  shortDate,
  slotDay,
  slotRange,
  statusLabel,
} from "@/lib/format";

const LIVE = (status?: string) =>
  status !== "completed" && status !== "cancelled";

export function OrderView({ id }: { id: string }) {
  const { user, loading } = useAuth();
  const params = useSearchParams();
  const placed = params.get("placed") === "1";
  const order = useQuery({
    queryKey: ["order", id],
    queryFn: () => api.order(id),
    enabled: Boolean(user),
    refetchInterval: (q) => (LIVE(q.state.data?.status) ? 12_000 : false),
  });
  const payment = useQuery({
    queryKey: ["payment", id],
    queryFn: () => api.paymentByOrder(id),
    enabled: Boolean(user),
    refetchInterval: (q) =>
      q.state.data?.status !== "verified" ? 12_000 : false,
  });

  if (!loading && !user) {
    return (
      <main className="page shell">
        <EmptyState
          title="Sign in to see this order."
          copy="Orders are private to the account that placed them."
          href={`/auth/login?next=/orders/${id}`}
          label="Sign in"
        />
      </main>
    );
  }
  if (order.isError) {
    return (
      <main className="page shell">
        <EmptyState
          title="We couldn't find that order."
          copy="It may belong to a different account. Your orders are all listed in your account."
          href="/account"
          label="Your account"
        />
      </main>
    );
  }
  const o = order.data;
  return (
    <main className="page shell">
      {!o ? (
        <Skeleton className="sk-block" />
      ) : (
        <>
          <header className="order-hero">
            <div>
              <FadeIn>
                <p className="eyebrow">
                  {placed
                    ? "Order placed"
                    : `Ordered ${shortDate(o.created_at)}`}
                </p>
              </FadeIn>
              <SplitText
                as="h1"
                text={
                  placed
                    ? `Thank you, *${(o.customer?.name ?? "").split(" ")[0] || "friend"}.*`
                    : statusHeadline(o)
                }
              />
            </div>
            <FadeIn delay={0.2} className="order-number">
              {o.order_number}
            </FadeIn>
          </header>
          <Timeline order={o} />
          <div className="order-grid">
            <div>
              <ul className="order-items">
                <OrderItems order={o} />
              </ul>
              <dl className="detail-list">
                <div>
                  <dt>Pickup</dt>
                  <dd>
                    {o.pickup
                      ? `${slotDay(o.pickup.slot_start)}, ${slotRange(o.pickup.slot_start, o.pickup.slot_end)}`
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt>For</dt>
                  <dd>
                    {o.customer?.name}
                    <br />
                    <small style={{ fontSize: 14, color: "var(--muted)" }}>
                      {o.customer?.phone}
                    </small>
                  </dd>
                </div>
                {o.customer_note && (
                  <div style={{ gridColumn: "1 / -1" }}>
                    <dt>Your note</dt>
                    <dd style={{ fontSize: 18 }}>{o.customer_note}</dd>
                  </div>
                )}
              </dl>
            </div>
            <aside style={{ display: "grid", gap: 20 }}>
              <PaymentPanel
                order={o}
                payment={payment.data}
                loading={payment.isLoading}
              />
              <Totals order={o} />
            </aside>
          </div>
        </>
      )}
    </main>
  );
}

function statusHeadline(o: Order) {
  switch (o.status) {
    case "pending_payment_verification":
      return "Waiting on *payment.*";
    case "confirmed":
      return "Confirmed. *It's happening.*";
    case "preparing":
      return "In the *oven.*";
    case "ready_for_pickup":
      return "Ready when *you are.*";
    case "completed":
      return "Collected. *Enjoy it.*";
    default:
      return "This order was *cancelled.*";
  }
}

function Timeline({ order }: { order: Order }) {
  if (order.status === "cancelled")
    return (
      <Notice tone="error">
        This order was cancelled. If you&apos;ve already paid, we&apos;ll be in
        touch about a refund.
      </Notice>
    );
  const index = ORDER_STEPS.findIndex((s) => s.key === order.status);
  return (
    <div
      className="timeline"
      aria-label={`Status: ${statusLabel(order.status)}`}
    >
      <div className="timeline-line">
        <motion.i
          initial={{ scaleX: 0 }}
          animate={{ scaleX: index / (ORDER_STEPS.length - 1) }}
          transition={{ duration: 1.4, ease: EASE, delay: 0.4 }}
        />
      </div>
      {ORDER_STEPS.map((step, i) => (
        <motion.div
          key={step.key}
          className={`timeline-step ${i <= index ? "is-done" : ""} ${i === index ? "is-current" : ""}`}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 + i * 0.12, duration: 0.6, ease: EASE }}
        >
          <span className="timeline-dot" />
          <span>{step.label}</span>
        </motion.div>
      ))}
    </div>
  );
}

function OrderItems({ order }: { order: Order }) {
  const { data: products } = useQuery({
    queryKey: ["products", "all"],
    queryFn: () => api.products("?page_size=100"),
  });
  const { data: photos } = useProductPhotos();
  const slugFor = (name: string) =>
    products?.find((p) => p.name === name)?.slug;
  return (
    <>
      {order.items.map((item) => {
        const slug = slugFor(item.product_name_snapshot);
        return (
          <li key={item.id}>
            <div className="cart-line-media">
              <CakePhoto src={slug ? photos?.[slug] : null} alt="" />
            </div>
            <div>
              <h3>
                {item.quantity > 1 && (
                  <span className="tabular">{item.quantity} × </span>
                )}
                {item.product_name_snapshot}
              </h3>
              <p>
                {[
                  item.variant_name_snapshot,
                  ...item.customizations.map((c) =>
                    c.value_snapshot
                      ? `“${c.value_snapshot}”`
                      : c.choice_name_snapshot,
                  ),
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
            <strong className="tabular">{money(item.line_total)}</strong>
          </li>
        );
      })}
    </>
  );
}

function Totals({ order }: { order: Order }) {
  return (
    <div className="summary" style={{ position: "static" }}>
      <div className="summary-row">
        <span>Subtotal</span>
        <strong className="tabular">{money(order.subtotal, true)}</strong>
      </div>
      {Number(order.discount_total) > 0 && (
        <div className="summary-row">
          <span>Discount</span>
          <strong className="tabular">
            −{money(order.discount_total, true)}
          </strong>
        </div>
      )}
      {Number(order.tax_total ?? 0) > 0 && (
        <div className="summary-row">
          <span>{order.prices_include_tax ? "Taxes (included)" : "Taxes"}</span>
          <strong className="tabular">{money(order.tax_total, true)}</strong>
        </div>
      )}
      <div className="summary-total">
        <span>Total</span>
        <strong className="tabular">{money(order.grand_total, true)}</strong>
      </div>
      {order.prices_include_tax && (
        <p className="drawer-note" style={{ textAlign: "left", margin: 0 }}>
          Prices include all taxes.
        </p>
      )}
    </div>
  );
}

function QR({ value }: { value: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    QRCode.toDataURL(value, {
      margin: 0,
      width: 360,
      color: { dark: "#351d18", light: "#ffffff" },
      errorCorrectionLevel: "M",
    }).then(setSrc, () => setSrc(null));
  }, [value]);
  return src ? (
    // A data-URL QR code: nothing for next/image to optimise.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="UPI payment QR code" />
  ) : (
    <Skeleton className="sk-square" />
  );
}

function PaymentPanel({
  order,
  payment,
  loading,
}: {
  order: Order;
  payment?: Payment;
  loading: boolean;
}) {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [copied, setCopied] = useState(false);
  if (loading || !payment) return <Skeleton className="sk-block" />;

  const upload = async (file: File | undefined) => {
    if (!file) return;
    if (!/^image\/(png|jpe?g|webp)$/.test(file.type)) {
      toast.error("Please upload a screenshot as PNG, JPG or WebP.");
      return;
    }
    setUploading(true);
    try {
      await api.submitEvidence(payment.id, file);
      toast.success("Got it — we'll check the payment shortly.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["payment", order.id] }),
        queryClient.invalidateQueries({ queryKey: ["order", order.id] }),
      ]);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const ins = payment.instructions;
  const verified = payment.status === "verified";
  return (
    <motion.div
      className="pay-card"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.9, ease: EASE, delay: 0.2 }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
        }}
      >
        <h2>{verified ? "Paid" : "Payment"}</h2>
        <span
          className={`status-pill ${verified ? "is-good" : payment.status === "rejected" ? "is-bad" : ""}`}
        >
          {
            {
              awaiting_payment: "Awaiting payment",
              pending_verification: "Checking",
              verified: "Verified",
              rejected: "Needs attention",
            }[payment.status]
          }
        </span>
      </div>
      <AnimatePresence mode="wait">
        {verified ? (
          <motion.p
            key="ok"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ margin: 0, color: "var(--muted)" }}
          >
            We received{" "}
            {money(payment.verified_amount ?? payment.amount_due, true)}. Thank
            you — your cake is on the schedule.
          </motion.p>
        ) : (
          <motion.div
            key="pay"
            style={{ display: "grid", gap: 20 }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {payment.status === "rejected" &&
              payment.latest_submission?.rejection_reason && (
                <Notice tone="error">
                  {payment.latest_submission.rejection_reason} Please upload a
                  new screenshot.
                </Notice>
              )}
            {payment.status === "pending_verification" && (
              <Notice>
                We have your screenshot and we&apos;re matching it to our
                account. This page updates by itself.
              </Notice>
            )}
            {ins ? (
              <div className="pay-qr">
                <div className="pay-qr-code">
                  <QR value={ins.upi_uri} />
                </div>
                <dl>
                  <div>
                    <dt>Amount</dt>
                    <dd
                      style={{
                        fontFamily: "var(--font-display)",
                        fontSize: 30,
                      }}
                    >
                      {money(ins.amount, true)}
                    </dd>
                  </div>
                  <div>
                    <dt>UPI ID</dt>
                    <dd>
                      {ins.upi_id}
                      <button
                        type="button"
                        className="copy-button"
                        onClick={async () => {
                          await navigator.clipboard
                            .writeText(ins.upi_id)
                            .catch(() => undefined);
                          setCopied(true);
                          window.setTimeout(() => setCopied(false), 1800);
                        }}
                      >
                        {copied ? <Check size={11} /> : <Copy size={11} />}
                      </button>
                    </dd>
                  </div>
                  <div>
                    <dt>Payment note</dt>
                    <dd>{order.order_number}</dd>
                  </div>
                </dl>
              </div>
            ) : (
              <Notice>
                We&apos;ll share payment details with you directly. You can
                still upload your receipt here once you&apos;ve paid.
              </Notice>
            )}
            {ins?.is_sample && (
              <span className="sample-tag" style={{ justifySelf: "start" }}>
                Sample UPI details — don&apos;t send real money
              </span>
            )}
            {ins && (
              <a
                className="btn btn-line btn-block mobile-only"
                href={ins.upi_uri}
              >
                <span className="btn-label">Open a UPI app</span>
              </a>
            )}
            {payment.can_submit_evidence && (
              <div
                className={`dropzone ${over ? "is-over" : ""}`}
                role="button"
                tabIndex={0}
                onClick={() => input.current?.click()}
                onKeyDown={(e) =>
                  (e.key === "Enter" || e.key === " ") && input.current?.click()
                }
                onDragOver={(e) => {
                  e.preventDefault();
                  setOver(true);
                }}
                onDragLeave={() => setOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setOver(false);
                  void upload(e.dataTransfer.files[0]);
                }}
              >
                <UploadCloud size={22} />
                <strong>
                  {uploading
                    ? "Uploading…"
                    : payment.latest_submission
                      ? "Upload a different screenshot"
                      : "Upload your payment screenshot"}
                </strong>
                <span>
                  Drop it here or tap to choose · PNG, JPG or WebP, up to 5 MB
                </span>
                <input
                  ref={input}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  hidden
                  onChange={(e) => void upload(e.target.files?.[0])}
                />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      <WhatsAppCta
        title="Questions about this order?"
        copy="Message us on WhatsApp — your order number is already in the message."
        label="WhatsApp us"
        text={orderEnquiryText(order.order_number)}
      />
      <Link
        href="/account"
        className="text-link"
        style={{ justifySelf: "start" }}
      >
        All your orders
      </Link>
    </motion.div>
  );
}
