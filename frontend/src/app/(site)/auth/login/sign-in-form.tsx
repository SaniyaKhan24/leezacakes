"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button, Field, Notice } from "@/components/commerce-ui";
import { useAuth } from "@/components/providers";
import { api, type ApiError } from "@/lib/api";

export function SignInForm({ onDone }: { onDone: () => void }) {
  const { login } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [email, setEmail] = useState("");
  const [resent, setResent] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await login(String(form.get("email")), String(form.get("password")));
      onDone();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} style={{ display: "grid", gap: 18 }}>
      <Field
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
        required
      />
      {error && (
        <Notice tone="error">
          {error.status === 401
            ? "That email and password don't match an active account. If you've just registered, confirm your email first."
            : error.message}
          {error.status === 401 && email && !resent && (
            <>
              {" "}
              <button
                type="button"
                className="link-button"
                onClick={async () => {
                  await api
                    .requestEmailVerification(email)
                    .catch(() => undefined);
                  setResent(true);
                }}
              >
                Resend the confirmation email
              </button>
            </>
          )}
          {resent &&
            " If that account needs confirming, a fresh link is on its way."}
        </Notice>
      )}
      <Button type="submit" loading={busy}>
        Sign in
      </Button>
      <Link
        href="/auth/reset"
        className="link-button"
        style={{ justifySelf: "start" }}
      >
        Forgotten your password?
      </Link>
    </form>
  );
}
