"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Toaster } from "sonner";
import {
  api,
  clearSession,
  restoreSession,
  type Cart,
  type Selection,
  type User,
} from "@/lib/api";

type Auth = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (body: Record<string, unknown>) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<Auth | null>(null);
const AUTH_EVENT = "leeza:auth-changed";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const announce = () => window.dispatchEvent(new Event(AUTH_EVENT));

  useEffect(() => {
    let active = true;
    (async () => {
      if (!restoreSession()) {
        if (active) setLoading(false);
        return;
      }
      try {
        const restored = await api.me();
        if (!active) return;
        setUser(restored);
        await api.mergeCart().catch(() => undefined);
        announce();
      } catch (error) {
        if ((error as { status?: number }).status === 401) clearSession();
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<Auth>(
    () => ({
      user,
      loading,
      login: async (email, password) => {
        const next = await api.login({ email, password });
        setUser(next);
        // Carry anything added as a guest into the signed-in cart.
        await api.mergeCart().catch(() => undefined);
        announce();
        return next;
      },
      register: (body) => api.register(body),
      logout: async () => {
        try {
          await api.logout();
        } finally {
          clearSession();
          setUser(null);
          announce();
        }
      },
      refresh: async () => {
        try {
          setUser(await api.me());
        } catch (error) {
          if ((error as { status?: number }).status === 401) {
            clearSession();
            setUser(null);
          } else throw error;
        }
      },
    }),
    [loading, user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

type CartContextValue = {
  cart: Cart | null;
  count: number;
  loading: boolean;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
  /** Increments on every successful add, so the bag icon can celebrate. */
  pulse: number;
  reload: () => Promise<void>;
  add: (body: {
    product_id: string;
    variant_id?: string | null;
    quantity: number;
    selections?: Selection[];
  }) => Promise<void>;
  update: (id: string, quantity: number) => Promise<void>;
  remove: (id: string) => Promise<void>;
};

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [pulse, setPulse] = useState(0);

  const reload = useCallback(async () => {
    try {
      setCart(await api.cart());
    } catch {
      // The cart re-syncs after the next auth change or cart action.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api
      .cart()
      .then(setCart)
      .catch(() => undefined)
      .finally(() => setLoading(false));
    const handler = () => void reload();
    window.addEventListener(AUTH_EVENT, handler);
    return () => window.removeEventListener(AUTH_EVENT, handler);
  }, [reload]);

  const value = useMemo<CartContextValue>(
    () => ({
      cart,
      count: cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0,
      loading,
      drawerOpen,
      setDrawerOpen,
      pulse,
      reload,
      add: async (body) => {
        setCart(await api.addCart(body));
        setPulse((p) => p + 1);
      },
      update: async (id, quantity) =>
        setCart(await api.updateCartItem(id, quantity)),
      remove: async (id) => {
        await api.deleteCartItem(id);
        await reload();
      },
    }),
    [cart, loading, drawerOpen, pulse, reload],
  );
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const value = useContext(CartContext);
  if (!value) throw new Error("useCart must be used inside CartProvider");
  return value;
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60_000, refetchOnWindowFocus: false, retry: 1 },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <AuthProvider>
        <CartProvider>
          {children}
          <Toaster
            position="bottom-center"
            toastOptions={{
              className: "toast",
              style: {
                fontFamily: "var(--font-sans)",
                borderRadius: 0,
                background: "var(--ink)",
                color: "var(--paper)",
                border: "none",
              },
            }}
          />
        </CartProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
