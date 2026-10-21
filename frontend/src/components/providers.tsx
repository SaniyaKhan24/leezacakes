"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, clearSession, restoreSession, type Cart, type User } from "@/lib/api";

type Auth = { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; register: (body: Record<string, unknown>) => Promise<void>; logout: () => Promise<void>; refresh: () => Promise<void> };
const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const announceAuth = () => window.dispatchEvent(new Event("auth-restored"));
  const mergeCart = async () => { try { await api.mergeCart(); } catch { /* No guest cart is valid. */ } };
  const signInAndMerge = async (email: string, password: string) => {
    const nextUser = await api.login({ email, password });
    setUser(nextUser);
    await mergeCart();
    announceAuth();
  };
  const refresh = async () => {
    try { setUser(await api.me()); }
    catch (error) {
      if ((error as { status?: number }).status === 401) { clearSession(); setUser(null); }
      else throw error;
    }
  };
  // Restore persisted auth before consumers can show the signed-out state.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => {
    let active = true;
    const restore = async () => {
      if (!restoreSession()) { if (active) setLoading(false); return; }
      try {
        const restoredUser = await api.me();
        if (active) { setUser(restoredUser); await mergeCart(); announceAuth(); }
      } catch (error) {
        if ((error as { status?: number }).status === 401) clearSession();
      } finally { if (active) setLoading(false); }
    };
    void restore();
    return () => { active = false; };
  }, []);
  const value = useMemo<Auth>(() => ({
    user, loading, refresh, login: signInAndMerge,
    register: async (body) => { await api.register(body); },
    logout: async () => { try { await api.logout(); } finally { clearSession(); setUser(null); announceAuth(); } },
  }), [loading, user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("useAuth must be used inside AuthProvider"); return value; }

type CartContextValue = { cart: Cart | null; loading: boolean; reload: () => Promise<void>; add: (body: Parameters<typeof api.addCart>[0]) => Promise<void>; update: (id: string, quantity: number) => Promise<void>; remove: (id: string) => Promise<void> };
const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const reload = async () => { try { setCart(await api.cart()); } catch { /* Retry on auth restoration or a later action. */ } finally { setLoading(false); } };
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void reload(); const handler = () => { void reload(); }; window.addEventListener("auth-restored", handler); return () => window.removeEventListener("auth-restored", handler); }, []);
  const value: CartContextValue = { cart, loading, reload, add: async (body) => setCart(await api.addCart(body)), update: async (id, quantity) => setCart(await api.updateCartItem(id, quantity)), remove: async (id) => { await api.deleteCartItem(id); await reload(); } };
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() { const value = useContext(CartContext); if (!value) throw new Error("useCart must be used inside CartProvider"); return value; }
