"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { AuthShell } from "@/components/auth-shell";
import { Button, Field, Notice, firstError } from "@/components/commerce-ui";
import { EASE } from "@/components/motion";
import { useAuth } from "@/components/providers";
import { api, type ApiError } from "@/lib/api";

function Register() {
  const { register } = useAuth();
  const params = useSearchParams();
  const next = params.get("next");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [resent, setResent] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = Object.fromEntries(form.entries());
    setBusy(true);
    setError(null);
    try {
      await register(body);
      setSentTo(String(body.email));
      // Remember where to return after the email link is opened in this browser.
      if (next) window.sessionStorage.setItem("leeza:after-verify", next);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell
      eyebrow="Create an account"
      title={sentTo ? "Check your *inbox.*" : "Lovely to *meet you.*"}
      art="bento-hearts"
      caption="Bento Hearts — a four-inch cake for two."
    >
      <AnimatePresence mode="wait">
        {sentTo ? (
          <motion.div
            key="sent"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE }}
            style={{ maxWidth: 460, marginTop: 30, display: "grid", gap: 18 }}
          >
            <p className="muted">
              We&apos;ve sent a confirmation link to <strong>{sentTo}</strong>.
              Open it on this device and you&apos;ll be ready to order.
            </p>
            <Button
              variant="line"
              disabled={resent}
              onClick={async () => {
                await api
                  .requestEmailVerification(sentTo)
                  .catch(() => undefined);
                setResent(true);
              }}
            >
              {resent ? "Sent again" : "Resend the link"}
            </Button>
            <p className="muted">
              Already confirmed?{" "}
              <Link
                href={`/auth/login${next ? `?next=${encodeURIComponent(next)}` : ""}`}
              >
                Sign in
              </Link>
            </p>
          </motion.div>
        ) : (
          <motion.form
            key="form"
            onSubmit={submit}
            exit={{ opacity: 0, y: -12 }}
          >
            <div className="form-grid">
              <Field
                label="First name"
                name="first_name"
                required
                autoComplete="given-name"
                error={firstError(error?.fields, "first_name")}
              />
              <Field
                label="Last name"
                name="last_name"
                required
                autoComplete="family-name"
                error={firstError(error?.fields, "last_name")}
              />
              <Field
                label="Email"
                name="email"
                type="email"
                required
                autoComplete="email"
                className="span-2"
                error={firstError(error?.fields, "email")}
              />
              <Field
                label="Phone"
                name="phone_number"
                type="tel"
                autoComplete="tel"
                placeholder="+91 98xxx xxxxx"
                className="span-2"
                error={firstError(error?.fields, "phone_number")}
                hint="For pickup updates. Optional."
              />
              <Field
                label="Password"
                name="password"
                type="password"
                required
                autoComplete="new-password"
                error={firstError(error?.fields, "password")}
              />
              <Field
                label="Confirm password"
                name="password_confirm"
                type="password"
                required
                autoComplete="new-password"
                error={firstError(error?.fields, "password_confirm")}
              />
            </div>
            {error &&
              !Object.keys(error.fields ?? {}).some((k) =>
                [
                  "first_name",
                  "last_name",
                  "email",
                  "phone_number",
                  "password",
                  "password_confirm",
                ].includes(k),
              ) && <Notice tone="error">{error.message}</Notice>}
            <Button type="submit" loading={busy}>
              Create account
            </Button>
            <p className="muted">
              Already have one?{" "}
              <Link
                href={`/auth/login${next ? `?next=${encodeURIComponent(next)}` : ""}`}
              >
                Sign in
              </Link>
            </p>
          </motion.form>
        )}
      </AnimatePresence>
    </AuthShell>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={null}>
      <Register />
    </Suspense>
  );
}
