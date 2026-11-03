"use client";

import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { useState, type FormEvent } from "react";
import {
  Button,
  Field,
  Notice,
  TextArea,
  firstError,
} from "@/components/commerce-ui";
import { EASE } from "@/components/motion";
import { useAuth } from "@/components/providers";
import { api, type ApiError, type Enquiry } from "@/lib/api";

export function EnquiryForm({
  defaultKind = "general",
}: {
  defaultKind?: Enquiry["kind"];
}) {
  const { user } = useAuth();
  const [kind, setKind] = useState<Enquiry["kind"]>(defaultKind);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [reference, setReference] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const value = (key: string) => String(form.get(key) ?? "").trim();
    setSending(true);
    setError(null);
    try {
      const result = await api.enquire({
        kind,
        name: value("name"),
        email: value("email"),
        phone: value("phone") || undefined,
        occasion: value("occasion") || undefined,
        event_date: value("event_date") || null,
        servings: value("servings") ? Number(value("servings")) : null,
        budget: value("budget") || undefined,
        message: value("message"),
      });
      setReference(result.reference);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="form-card">
      <AnimatePresence mode="wait">
        {reference ? (
          <motion.div
            key="done"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE }}
            style={{ display: "grid", gap: 14 }}
          >
            <p className="eyebrow">Received · {reference}</p>
            <h2 style={{ fontSize: "clamp(40px, 4vw, 60px)" }}>
              Thank you. <em>We&apos;ll be in touch.</em>
            </h2>
            <p style={{ margin: 0, color: "var(--muted)" }}>
              We read every message ourselves and usually reply within a working
              day. Keep the reference above if you write again.
            </p>
          </motion.div>
        ) : (
          <motion.form
            key="form"
            onSubmit={submit}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -10 }}
            style={{ display: "grid", gap: 18 }}
          >
            <LayoutGroup id="kind">
              <div className="kind-switch" role="tablist">
                {(
                  [
                    ["general", "A question"],
                    ["custom_cake", "A bespoke cake"],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={kind === key}
                    className={kind === key ? "is-active" : ""}
                    onClick={() => setKind(key)}
                  >
                    {kind === key && (
                      <motion.span layoutId="kind-bg" className="chip-bg" />
                    )}
                    {label}
                  </button>
                ))}
              </div>
            </LayoutGroup>
            <div className="form-grid">
              <Field
                label="Your name"
                name="name"
                required
                autoComplete="name"
                defaultValue={
                  user ? `${user.first_name} ${user.last_name}`.trim() : ""
                }
                error={firstError(error?.fields, "name")}
              />
              <Field
                label="Email"
                name="email"
                type="email"
                required
                autoComplete="email"
                defaultValue={user?.email ?? ""}
                error={firstError(error?.fields, "email")}
              />
              <Field
                label="Phone (optional)"
                name="phone"
                type="tel"
                autoComplete="tel"
                defaultValue={user?.phone_number ?? ""}
                error={firstError(error?.fields, "phone")}
              />
              {kind === "custom_cake" ? (
                <Field
                  label="Occasion"
                  name="occasion"
                  placeholder="Wedding, 60th birthday…"
                  error={firstError(error?.fields, "occasion")}
                />
              ) : (
                <span />
              )}
              <AnimatePresence initial={false}>
                {kind === "custom_cake" && (
                  <motion.div
                    className="span-2 form-grid"
                    style={{
                      gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                      overflow: "hidden",
                    }}
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.5, ease: EASE }}
                  >
                    <Field
                      label="Date"
                      name="event_date"
                      type="date"
                      error={firstError(error?.fields, "event_date")}
                    />
                    <Field
                      label="Guests"
                      name="servings"
                      type="number"
                      min={1}
                      max={1000}
                      error={firstError(error?.fields, "servings")}
                    />
                    <Field
                      label="Budget"
                      name="budget"
                      placeholder="₹8,000–12,000"
                      error={firstError(error?.fields, "budget")}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
              <TextArea
                className="span-2"
                label={
                  kind === "custom_cake"
                    ? "Tell us about the cake"
                    : "Your message"
                }
                name="message"
                required
                maxLength={2000}
                placeholder={
                  kind === "custom_cake"
                    ? "Flavours you love, colours, a photo you've saved, how many tiers…"
                    : "How can we help?"
                }
                error={firstError(error?.fields, "message")}
              />
            </div>
            {error && !Object.keys(error.fields ?? {}).length && (
              <Notice tone="error">{error.message}</Notice>
            )}
            <Button type="submit" loading={sending}>
              Send
            </Button>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
}
