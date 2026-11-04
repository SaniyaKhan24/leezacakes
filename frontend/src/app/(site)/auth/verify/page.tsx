"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Suspense,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { AuthShell } from "@/components/auth-shell";
import { Notice } from "@/components/commerce-ui";
import { api } from "@/lib/api";

function Verify() {
  const params = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const [state, setState] = useState<"working" | "done" | "failed">(
    uid && token ? "working" : "failed",
  );
  const [message, setMessage] = useState(
    uid && token
      ? ""
      : "This link is incomplete. Open the most recent email we sent, or request a new link from the sign-in page.",
  );
  const started = useRef(false);
  const next = useSyncExternalStore(
    () => () => undefined,
    () => window.sessionStorage.getItem("leeza:after-verify"),
    () => null,
  );

  useEffect(() => {
    if (!uid || !token || started.current) return;
    started.current = true;
    api
      .confirmEmailVerification({ uid, token })
      .then(() => setState("done"))
      .catch((e: Error) => {
        setState("failed");
        setMessage(e.message);
      });
  }, [uid, token]);

  const signIn = `/auth/login?verified=1${next ? `&next=${encodeURIComponent(next)}` : ""}`;
  return (
    <AuthShell
      eyebrow="Confirm your email"
      title={
        state === "done"
          ? "All *confirmed.*"
          : state === "failed"
            ? "That link *didn't work.*"
            : "One *moment…*"
      }
      art="vanilla-berry"
    >
      <div style={{ maxWidth: 460, marginTop: 30, display: "grid", gap: 20 }}>
        {state === "done" && (
          <>
            <p className="muted">
              Your account is ready. Sign in and your bag will be waiting.
            </p>
            <Link href={signIn} className="btn btn-dark">
              <span className="btn-label">Sign in and continue</span>
            </Link>
          </>
        )}
        {state === "failed" && (
          <>
            <Notice tone="error">{message}</Notice>
            <Link href="/auth/login" className="btn btn-line">
              <span className="btn-label">Go to sign in</span>
            </Link>
          </>
        )}
      </div>
    </AuthShell>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <Verify />
    </Suspense>
  );
}
