"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SiteHeader } from "@/components/site-header";
import { Button, EmptyState } from "@/components/commerce-ui";
import { useAuth, useCart } from "@/components/providers";
import { api, type Address } from "@/lib/api";

export default function CheckoutPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { cart, loading: cartLoading, reload } = useCart();
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [form, setForm] = useState({ customer_name: "", customer_phone: "", customer_email: "", pickup_slot_start: "", pickup_slot_end: "", customer_note: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (user) api.addresses().then(setAddresses).catch(() => {}); }, [user]);
  if (authLoading) return <><SiteHeader /><div className="loading-copy">Restoring your session…</div></>;
  if (!user) return <><SiteHeader /><main className="store-main shell"><EmptyState title="Sign in before checkout." copy="The backend creates orders for authenticated customers so your order history and payment status stay connected." href="/auth/login" label="Sign in" /></main></>;
  if (cartLoading) return <><SiteHeader /><div className="loading-copy">Preparing checkout…</div></>;
  if (!cart?.items.length) return <><SiteHeader /><main className="store-main shell"><EmptyState title="There’s nothing to check out yet." copy="Add a cake to your cart first." href="/shop" label="Browse cakes" /></main></>;

  const change = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm((current) => ({ ...current, [key]: event.target.value }));
  const customerName = form.customer_name || `${user.first_name} ${user.last_name}`.trim();
  const customerPhone = form.customer_phone || user.phone_number;
  const customerEmail = form.customer_email || user.email;
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setLoading(true); setError("");
    try {
      if (cart.price_confirmation_required) { await api.confirmPrices(); await reload(); }
      const validation = await api.validateCheckout();
      if (!validation.ready_for_checkout) throw new Error("Please review your cart before checkout.");
      const idempotencyKey = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `checkout-${Date.now()}`;
      const order = await api.createOrder({ ...form, customer_name: customerName, customer_phone: customerPhone, customer_email: customerEmail }, idempotencyKey);
      router.push(`/orders/${order.id}`);
    } catch (err) { setError(err instanceof Error ? err.message : "We couldn’t place your order."); }
    finally { setLoading(false); }
  };

  return <><SiteHeader /><main className="store-main shell checkout-page"><div className="page-intro compact"><p className="eyebrow">Almost there</p><h1>Checkout.</h1><p>The current backend workflow collects a pickup slot. Delivery address selection will be enabled when the order API supports it.</p></div><div className="checkout-layout"><form className="checkout-form" onSubmit={submit}><h2>Customer details</h2><label>Name<input required value={customerName} onChange={change("customer_name")} /></label><div className="form-two"><label>Phone<input required value={customerPhone} onChange={change("customer_phone")} /></label><label>Email<input type="email" value={customerEmail} onChange={change("customer_email")} /></label></div><h2>Pickup slot</h2><div className="form-two"><label>Starts<input type="datetime-local" required value={form.pickup_slot_start} onChange={change("pickup_slot_start")} /></label><label>Ends<input type="datetime-local" required value={form.pickup_slot_end} onChange={change("pickup_slot_end")} /></label></div><label>Note<textarea rows={4} value={form.customer_note} onChange={change("customer_note")} placeholder="Any useful note for the bakery?" /></label>{addresses.length > 0 && <p className="muted">You have {addresses.length} saved address{addresses.length > 1 ? "es" : ""} in your account. The current order contract does not accept an address field.</p>}{error && <p className="form-error" role="alert">{error}</p>}<Button type="submit" loading={loading}>Place order</Button></form><aside className="summary-card"><p className="eyebrow">Your order</p>{cart.items.map((item) => <div className="summary-line" key={item.id}><span>{item.quantity} × {item.product.name}</span><strong>₹{Number(item.line_subtotal).toLocaleString("en-IN")}</strong></div>)}<div className="summary-total"><span>Subtotal</span><strong>₹{Number(cart.subtotal).toLocaleString("en-IN")}</strong></div><Link href="/cart" className="back-link">Edit cart</Link></aside></div></main></>;
}
