"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import {
  Button,
  EmptyState,
  Field,
  PageIntro,
  Skeleton,
  firstError,
} from "@/components/commerce-ui";
import { EASE } from "@/components/motion";
import { useAuth } from "@/components/providers";
import { api, type ApiError } from "@/lib/api";
import { money, shortDate, slotDay, statusLabel } from "@/lib/format";

type Tab = "orders" | "profile" | "addresses";

export default function AccountPage() {
  const { user, loading, logout, refresh } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("orders");
  useEffect(() => {
    if (!loading && !user) router.replace("/auth/login?next=/account");
  }, [loading, user, router]);
  if (!user) {
    return (
      <main className="page shell">
        <Skeleton className="sk-block" />
      </main>
    );
  }
  return (
    <main className="page shell">
      <PageIntro
        eyebrow="Your account"
        title={`Hello, *${user.first_name || "there"}.*`}
      />
      <div className="account-grid">
        <nav className="account-nav" aria-label="Account sections">
          {(
            [
              ["orders", "Orders"],
              ["profile", "Details"],
              ["addresses", "Addresses"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={tab === key ? "is-active" : ""}
              onClick={() => setTab(key)}
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            onClick={async () => {
              await logout();
              router.push("/");
            }}
          >
            Sign out
          </button>
        </nav>
        <AnimatePresence mode="wait">
          <motion.section
            key={tab}
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.5, ease: EASE }}
          >
            {tab === "orders" && <Orders />}
            {tab === "profile" && <Profile onSaved={refresh} />}
            {tab === "addresses" && <Addresses />}
          </motion.section>
        </AnimatePresence>
      </div>
    </main>
  );
}

function Orders() {
  const orders = useQuery({ queryKey: ["orders"], queryFn: api.orders });
  if (orders.isLoading) return <Skeleton className="sk-block" />;
  if (!orders.data?.length)
    return (
      <EmptyState
        title="No orders yet."
        copy="When you order a cake it'll appear here, with its pickup time and payment status."
        href="/shop"
        label="Browse the cakes"
      />
    );
  return (
    <ul className="order-rows">
      {orders.data.map((o, i) => (
        <motion.li
          key={o.id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05, duration: 0.5, ease: EASE }}
        >
          <Link href={`/orders/${o.id}`} className="order-row">
            <div>
              <strong>{o.order_number}</strong>
              <small>
                {o.item_count} {o.item_count === 1 ? "cake" : "cakes"} · ordered{" "}
                {shortDate(o.created_at)}
              </small>
            </div>
            <div>
              <small>Pickup</small>
              {slotDay(o.pickup_slot_start)}
            </div>
            <div>
              <span
                className={`status-pill ${o.status === "completed" || o.status === "ready_for_pickup" ? "is-good" : o.status === "cancelled" ? "is-bad" : ""}`}
              >
                {statusLabel(o.status)}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <span className="tabular">{money(o.grand_total)}</span>
              <ArrowUpRight size={18} />
            </div>
          </Link>
        </motion.li>
      ))}
    </ul>
  );
}

function Profile({ onSaved }: { onSaved: () => Promise<void> }) {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await api.updateMe({
        first_name: String(form.get("first_name")),
        last_name: String(form.get("last_name")),
        phone_number: String(form.get("phone_number")),
      });
      await onSaved();
      toast.success("Saved.");
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="form-card" onSubmit={submit}>
      <div className="form-grid">
        <Field
          label="First name"
          name="first_name"
          defaultValue={user?.first_name}
          error={firstError(error?.fields, "first_name")}
        />
        <Field
          label="Last name"
          name="last_name"
          defaultValue={user?.last_name}
          error={firstError(error?.fields, "last_name")}
        />
        <Field
          label="Email"
          value={user?.email ?? ""}
          disabled
          hint="Your email is how you sign in."
          readOnly
        />
        <Field
          label="Phone"
          name="phone_number"
          type="tel"
          defaultValue={user?.phone_number}
          error={firstError(error?.fields, "phone_number")}
        />
      </div>
      <Button type="submit" loading={busy} style={{ justifySelf: "start" }}>
        Save details
      </Button>
    </form>
  );
}

function Addresses() {
  const queryClient = useQueryClient();
  const addresses = useQuery({
    queryKey: ["addresses"],
    queryFn: api.addresses,
  });
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = Object.fromEntries(
      new FormData(event.currentTarget).entries(),
    ) as Record<string, string>;
    setBusy(true);
    setError(null);
    try {
      await api.createAddress({
        ...form,
        country_code: "IN",
        is_default: !addresses.data?.length,
      });
      await queryClient.invalidateQueries({ queryKey: ["addresses"] });
      setAdding(false);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div style={{ display: "grid", gap: 24 }}>
      <p className="lede" style={{ margin: 0 }}>
        Orders are collected from the studio for now. Saved addresses help us
        when we start delivering.
      </p>
      {addresses.isLoading ? (
        <Skeleton className="sk-block" />
      ) : (
        <div className="address-grid">
          {addresses.data?.map((a) => (
            <div className="address-card" key={a.id}>
              <p className="eyebrow" style={{ marginBottom: 10 }}>
                {a.label || "Address"} {a.is_default && "· default"}
              </p>
              <strong>{a.recipient_name}</strong>
              <p>
                {[
                  a.address_line_1,
                  a.address_line_2,
                  a.locality,
                  a.city,
                  a.state,
                  a.postal_code,
                ]
                  .filter(Boolean)
                  .join(", ")}
              </p>
              <button
                type="button"
                className="link-button"
                style={{ marginTop: 12 }}
                onClick={async () => {
                  await api.deleteAddress(a.id);
                  await queryClient.invalidateQueries({
                    queryKey: ["addresses"],
                  });
                }}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
      {adding ? (
        <form className="form-card" onSubmit={submit}>
          <div className="form-grid">
            <Field label="Label" name="label" placeholder="Home" />
            <Field
              label="Recipient"
              name="recipient_name"
              required
              error={firstError(error?.fields, "recipient_name")}
            />
            <Field
              label="Phone"
              name="phone_number"
              type="tel"
              required
              error={firstError(error?.fields, "phone_number")}
            />
            <Field
              label="Address line 1"
              name="address_line_1"
              required
              className="span-2"
              error={firstError(error?.fields, "address_line_1")}
            />
            <Field
              label="Address line 2"
              name="address_line_2"
              className="span-2"
            />
            <Field label="Locality" name="locality" />
            <Field
              label="City"
              name="city"
              required
              error={firstError(error?.fields, "city")}
            />
            <Field
              label="State"
              name="state"
              required
              error={firstError(error?.fields, "state")}
            />
            <Field
              label="PIN code"
              name="postal_code"
              required
              error={firstError(error?.fields, "postal_code")}
            />
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <Button type="submit" loading={busy}>
              Save address
            </Button>
            <Button
              type="button"
              variant="line"
              onClick={() => setAdding(false)}
            >
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <Button
          variant="line"
          onClick={() => setAdding(true)}
          style={{ justifySelf: "start" }}
        >
          Add an address
        </Button>
      )}
    </div>
  );
}
