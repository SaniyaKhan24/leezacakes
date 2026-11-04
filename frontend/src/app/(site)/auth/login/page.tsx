"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth-shell";
import { SignInForm } from "./sign-in-form";

function Login() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") ?? "/account";
  const verified = params.get("verified") === "1";
  return (
    <AuthShell
      eyebrow={verified ? "Email confirmed" : "Welcome back"}
      title={verified ? "You're in. *Sign in.*" : "Good to *see you.*"}
      art="pistachio-rose"
      caption="Pistachio Rose — pistachio sponge, rose cream."
    >
      <div style={{ maxWidth: 460, marginTop: 30 }}>
        <SignInForm
          onDone={() => router.push(next.startsWith("/") ? next : "/account")}
        />
        <p className="muted" style={{ marginTop: 28 }}>
          New to Leeza Cakes?{" "}
          <Link
            href={`/auth/register${next !== "/account" ? `?next=${encodeURIComponent(next)}` : ""}`}
          >
            Create an account
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <Login />
    </Suspense>
  );
}
