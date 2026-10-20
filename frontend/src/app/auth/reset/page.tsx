"use client";
import { useState } from "react";
import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/commerce-ui";
import { api } from "@/lib/api";
export default function PasswordResetPage() { const [email, setEmail] = useState(""); const [message, setMessage] = useState(""); const [error, setError] = useState(""); const submit = async (event: React.FormEvent) => { event.preventDefault(); setError(""); try { const result = await api.requestPasswordReset(email); setMessage(result.detail); } catch (err) { setError(err instanceof Error ? err.message : "Unable to request a reset."); } }; return <><SiteHeader /><main className="form-page"><form className="auth-card" onSubmit={submit}><p className="eyebrow">Account security</p><h1>Reset your password.</h1><label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>{error && <p className="form-error">{error}</p>}{message && <p className="muted" role="status">{message}</p>}<Button type="submit">Send reset instructions</Button></form></main></>; }
