"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { AuthShell } from "@/components/auth-shell";
import { Button, Field, Notice, firstError } from "@/components/commerce-ui";
import { api, type ApiError } from "@/lib/api";

function Reset() {
  const params = useSearchParams();
  const uid = params.get("uid");
  const token = params.get("token");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      if (uid && token) {
        const result = await api.confirmPasswordReset({
          uid,
          token,
          new_password: String(form.get("new_password")),
          new_password_confirm: String(form.get("new_password_confirm")),
        });
        setDone(result.detail);
      } else {
        const result = await api.requestPasswordReset(
          String(form.get("email")),
        );
        setDone(result.detail);
      }
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  };

  const confirming = Boolean(uid && token);
  return (
    <AuthShell
      eyebrow="Password"
      title={confirming ? "Choose a *new one.*" : "It happens to *everyone.*"}
      art="lemon-blueberry"
    >
      {done ? (
        <div style={{ maxWidth: 460, marginTop: 30, display: "grid", gap: 20 }}>
          <Notice tone="success">{done}</Notice>
          <Link href="/auth/login" className="btn btn-dark">
            <span className="btn-label">Back to sign in</span>
          </Link>
        </div>
      ) : (
        <form onSubmit={submit}>
          {confirming ? (
            <>
              <Field
                label="New password"
                name="new_password"
                type="password"
                required
                autoComplete="new-password"
                error={firstError(error?.fields, "new_password")}
              />
              <Field
                label="Confirm new password"
                name="new_password_confirm"
                type="password"
                required
                autoComplete="new-password"
                error={firstError(error?.fields, "new_password_confirm")}
              />
            </>
          ) : (
            <>
              <p className="muted" style={{ margin: 0 }}>
                Enter your email and we&apos;ll send a link to set a new
                password.
              </p>
              <Field
                label="Email"
                name="email"
                type="email"
                required
                autoComplete="email"
                error={firstError(error?.fields, "email")}
              />
            </>
          )}
          {error && (
            <Notice tone="error">
              {firstError(error.fields, "token") ?? error.message}
            </Notice>
          )}
          <Button type="submit" loading={busy}>
            {confirming ? "Save password" : "Send the link"}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}

export default function ResetPage() {
  return (
    <Suspense fallback={null}>
      <Reset />
    </Suspense>
  );
}
