/**
 * Typed client for the Leeza Cakes Django API.
 *
 * Requests go to this site's own origin (`/api/...`); Next.js rewrites them to
 * Django, so the guest-cart session cookie is first-party. Signed-in requests
 * carry a short-lived JWT access token that is refreshed transparently.
 */

export type ApiError = Error & {
  status?: number;
  fields?: Record<string, string[]>;
  retryAfter?: string | null;
};

export type Category = {
  id: string;
  name: string;
  slug: string;
  description: string;
  image: string | null;
  parent: string | null;
};
export type ProductImage = {
  id: string;
  url: string | null;
  image: string | null;
  alt_text: string;
  sort_order: number;
  is_primary: boolean;
};
export type Variant = {
  id: string;
  name: string;
  sku?: string | null;
  price: string;
  currency: string;
  is_active: boolean;
  sort_order?: number;
};
export type Product = {
  id: string;
  name: string;
  slug: string;
  description: string;
  short_description: string;
  category: Category;
  base_price: string | null;
  currency: string;
  effective_price: string | null;
  weight_description?: string;
  preparation_time?: number | null;
  is_featured: boolean;
  primary_image: ProductImage | null;
  images: ProductImage[];
  variants: Variant[];
};
export type User = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  is_email_verified: boolean;
  date_joined: string;
};
export type Address = {
  id: string;
  label: string;
  recipient_name: string;
  phone_number: string;
  address_line_1: string;
  address_line_2: string;
  locality: string;
  city: string;
  state: string;
  postal_code: string;
  country_code: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};
export type OptionChoice = {
  id: number;
  choice: number;
  choice_name: string;
  price_adjustment: string;
  currency: string;
  is_active: boolean;
  sort_order: number;
};
export type CustomizationOption = {
  id: number;
  product: string;
  option: {
    id: number;
    name: string;
    slug: string;
    description: string;
    input_type: "single_choice" | "multiple_choice" | "text";
    is_active: boolean;
    sort_order: number;
    choices: unknown[];
  };
  is_required: boolean;
  is_active: boolean;
  sort_order: number;
  min_selections: number | null;
  max_selections: number | null;
  choices: OptionChoice[];
};
export type Selection = {
  option_id: number;
  choice_ids?: number[];
  text_value?: string;
};
export type CartItem = {
  id: string;
  product: { id: string; name: string; slug: string };
  variant: { id: string; name: string } | null;
  quantity: number;
  customizations: {
    option_id: number;
    option_name: string;
    choice_id: number | null;
    choice_name: string | null;
    text_value: string;
    price_adjustment: string;
  }[];
  unit_price: string;
  line_subtotal: string;
  price_confirmation_required: boolean;
};
export type Cart = {
  id: string;
  status: string;
  currency: string;
  items: CartItem[];
  subtotal: string;
  price_confirmation_required: boolean;
};
export type OrderStatus =
  | "pending_payment_verification"
  | "confirmed"
  | "preparing"
  | "ready_for_pickup"
  | "completed"
  | "cancelled";
export type OrderSummary = {
  id: string;
  order_number: string;
  status: OrderStatus;
  payment_status: string;
  currency: string;
  grand_total: string;
  item_count: number;
  pickup_slot_start: string;
  pickup_slot_end: string;
  created_at: string;
};
export type Order = {
  id: string;
  order_number: string;
  status: OrderStatus;
  payment_status: string;
  payment?: { status: string; id?: string; review_status?: Payment["status"] };
  customer?: { name: string; phone: string; email: string };
  pickup?: { slot_start: string; slot_end: string };
  currency: string;
  subtotal: string;
  discount_total: string;
  tax_total: string | null;
  grand_total: string | null;
  prices_include_tax?: boolean;
  customer_note: string;
  items: {
    id: string;
    product_name_snapshot: string;
    variant_name_snapshot: string | null;
    sku_snapshot: string | null;
    quantity: number;
    unit_base_price: string;
    unit_customization_total: string;
    unit_price: string;
    line_total: string;
    customizations: {
      option_name_snapshot: string;
      choice_name_snapshot: string | null;
      value_snapshot: string;
      price_adjustment: string;
    }[];
  }[];
  created_at: string;
  confirmed_at: string | null;
  completed_at: string | null;
};
export type PaymentInstructions = {
  upi_id: string;
  payee_name: string;
  amount: string;
  currency: string;
  upi_uri: string;
  note: string;
  is_sample: boolean;
};
export type PaymentSubmission = {
  id: string;
  status: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  rejection_reason: string;
  submitted_at: string;
  reviewed_at: string | null;
};
export type Payment = {
  id: string;
  order: string;
  order_number?: string;
  method: string;
  status: "awaiting_payment" | "pending_verification" | "verified" | "rejected";
  amount_due: string;
  currency: string;
  verified_amount: string | null;
  verified_at: string | null;
  latest_submission: PaymentSubmission | null;
  can_submit_evidence: boolean;
  instructions?: PaymentInstructions | null;
};
export type PickupSlot = { start: string; end: string; available: boolean };
export type PickupSchedule = {
  lead_time_minutes: number;
  timezone: string;
  days: { date: string; slots: PickupSlot[] }[];
};
export type SiteConfig = {
  business_name: string;
  contact_phone: string | null;
  contact_email: string | null;
  whatsapp: string | null;
  /** Digits-only international number for wa.me links, e.g. "919000000000". */
  whatsapp_link_number?: string | null;
  instagram: string | null;
  address: string | null;
  pickup_hours_label: string | null;
  is_sample: boolean;
};
export type InboxItem = {
  id: number;
  event_key: string;
  audience: "customer" | "staff";
  title: string;
  body: string;
  link: string;
  created_at: string;
  read_at: string | null;
};
export type Inbox = {
  count: number;
  next: string | null;
  previous: string | null;
  unread_count: number;
  results: InboxItem[];
};
export type SearchResult = {
  id: string;
  name: string;
  slug: string;
  category: { slug: string; name: string };
  primary_image: string | null;
  price: { amount: string | null; currency: string; display_type: string };
  available: boolean;
  match_type: string;
};
export type Enquiry = {
  kind: "general" | "custom_cake";
  name: string;
  email: string;
  phone?: string;
  occasion?: string;
  event_date?: string | null;
  servings?: number | null;
  budget?: string;
  message: string;
};

const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const ACCESS_TOKEN_KEY = "leeza-cakes.access-token";
const REFRESH_TOKEN_KEY = "leeza-cakes.refresh-token";
let accessToken: string | null = null;
let refreshToken: string | null = null;
let refreshing: Promise<boolean> | null = null;

function persistSession() {
  if (typeof window === "undefined") return;
  try {
    if (accessToken) window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    else window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    if (refreshToken)
      window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    else window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    // Storage can be blocked (private browsing); the in-memory session still works for this tab.
  }
}

export function setSession(access: string | null, refresh: string | null) {
  accessToken = access;
  refreshToken = refresh;
  persistSession();
}

export function restoreSession() {
  if (typeof window === "undefined") return false;
  try {
    accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY);
    refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    accessToken = null;
    refreshToken = null;
  }
  return Boolean(accessToken || refreshToken);
}

export function clearSession() {
  setSession(null, null);
}

async function refreshAccess(): Promise<boolean> {
  if (!refreshToken) return false;
  refreshing ??= (async () => {
    try {
      const response = await fetch(`${base}/api/v1/accounts/token/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refreshToken }),
        credentials: "include",
      });
      if (!response.ok) {
        if (response.status === 400 || response.status === 401) clearSession();
        return false;
      }
      const payload = await response.json();
      const nextAccess = payload.data?.access ?? null;
      if (!nextAccess) return false;
      setSession(nextAccess, payload.data?.refresh ?? refreshToken);
      return true;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

function toError(
  response: Response,
  payload: Record<string, unknown>,
): ApiError {
  const body = (
    payload.error && typeof payload.error === "object" ? payload.error : payload
  ) as Record<string, unknown>;
  const firstField = Object.values(body).find(
    (value) => Array.isArray(value) && typeof value[0] === "string",
  ) as string[] | undefined;
  const detail =
    typeof body.detail === "string"
      ? body.detail
      : response.status === 429
        ? "Too many attempts. Please wait a moment and try again."
        : response.status >= 500
          ? "The bakery is having a moment. Please try again shortly."
          : (firstField?.[0] ??
            "Something went wrong. Please check the details and try again.");
  const error = new Error(detail) as ApiError;
  error.status = response.status;
  error.retryAfter = response.headers.get("Retry-After");
  error.fields = Object.fromEntries(
    Object.entries(body)
      .filter(([, value]) => Array.isArray(value) || typeof value === "string")
      .map(([key, value]) => [
        key,
        Array.isArray(value) ? value.map(String) : [String(value)],
      ]),
  );
  return error;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (
    response.status === 401 &&
    retry &&
    refreshToken &&
    (await refreshAccess())
  ) {
    return request<T>(path, init, false);
  }
  if (!response.ok) {
    let payload: Record<string, unknown> = {};
    try {
      payload = await response.json();
    } catch {
      // Non-JSON error bodies fall back to status-based messages.
    }
    throw toError(response, payload);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const unwrap = <T>(payload: { data: T } | T) =>
  (payload && typeof payload === "object" && "data" in (payload as object)
    ? (payload as { data: T }).data
    : payload) as T;
const list = <T>(payload: { results?: T[] } | T[]) =>
  Array.isArray(payload) ? payload : (payload.results ?? []);
const json = (body: unknown) => JSON.stringify(body);

export const api = {
  products: (query = "") =>
    request<{ results?: Product[] } | Product[]>(
      `/api/v1/catalog/products/${query}`,
    ).then(list),
  product: (slug: string) =>
    request<Product>(`/api/v1/catalog/products/${slug}/`),
  categories: () =>
    request<{ results?: Category[] } | Category[]>(
      "/api/v1/catalog/categories/",
    ).then(list),
  search: (query: string) =>
    request<{ results: SearchResult[]; count: number }>(
      `/api/v1/search/?${query}`,
    ),
  options: (slug: string) =>
    request<{
      product: { slug: string; name: string };
      options: CustomizationOption[];
    }>(`/api/v1/customization/products/${slug}/options/`),

  register: (body: Record<string, unknown>) =>
    request<{ data: User }>("/api/v1/accounts/register/", {
      method: "POST",
      body: json(body),
    }).then(unwrap),
  login: (body: { email: string; password: string }) =>
    request<{ data: { access: string; refresh: string; user: User } }>(
      "/api/v1/accounts/login/",
      { method: "POST", body: json(body) },
    ).then((p) => {
      setSession(p.data.access, p.data.refresh);
      return p.data.user;
    }),
  logout: () =>
    request<void>("/api/v1/accounts/logout/", {
      method: "POST",
      body: json({ refresh: refreshToken }),
    }).finally(clearSession),
  me: () => request<{ data: User }>("/api/v1/accounts/me/").then(unwrap),
  updateMe: (body: Partial<User>) =>
    request<{ data: User }>("/api/v1/accounts/me/", {
      method: "PATCH",
      body: json(body),
    }).then(unwrap),
  requestPasswordReset: (email: string) =>
    request<{ detail: string }>("/api/v1/accounts/password/reset/", {
      method: "POST",
      body: json({ email }),
    }),
  confirmPasswordReset: (body: {
    uid: string;
    token: string;
    new_password: string;
    new_password_confirm: string;
  }) =>
    request<{ detail: string }>("/api/v1/accounts/password/reset/confirm/", {
      method: "POST",
      body: json(body),
    }),
  requestEmailVerification: (email: string) =>
    request<{ detail: string }>(
      "/api/v1/accounts/email/verification/request/",
      { method: "POST", body: json({ email }) },
    ),
  confirmEmailVerification: (body: { uid: string; token: string }) =>
    request<{ data: { is_email_verified: boolean } }>(
      "/api/v1/accounts/email/verification/confirm/",
      { method: "POST", body: json(body) },
    ),
  addresses: () =>
    request<{ data: Address[] }>("/api/v1/accounts/addresses/").then(unwrap),
  createAddress: (body: Partial<Address>) =>
    request<{ data: Address }>("/api/v1/accounts/addresses/", {
      method: "POST",
      body: json(body),
    }).then(unwrap),
  deleteAddress: (id: string) =>
    request<void>(`/api/v1/accounts/addresses/${id}/`, { method: "DELETE" }),

  cart: () => request<Cart>("/api/v1/cart/"),
  addCart: (body: {
    product_id: string;
    variant_id?: string | null;
    quantity: number;
    selections?: Selection[];
  }) =>
    request<Cart>("/api/v1/cart/items/", { method: "POST", body: json(body) }),
  updateCartItem: (id: string, quantity: number) =>
    request<Cart>(`/api/v1/cart/items/${id}/`, {
      method: "PATCH",
      body: json({ quantity }),
    }),
  deleteCartItem: (id: string) =>
    request<void>(`/api/v1/cart/items/${id}/`, { method: "DELETE" }),
  confirmPrices: () =>
    request<Cart>("/api/v1/cart/confirm-prices/", { method: "POST" }),
  validateCheckout: () =>
    request<{
      valid: boolean;
      ready_for_checkout: boolean;
      errors?: unknown[];
    }>("/api/v1/cart/checkout/validate/", { method: "POST" }),
  mergeCart: () =>
    request<{ merged: boolean; cart: Cart; issues: unknown[] }>(
      "/api/v1/cart/merge/",
      { method: "POST" },
    ),

  pickupSlots: () => request<PickupSchedule>("/api/v1/orders/pickup-slots/"),
  orders: () =>
    request<{ results: OrderSummary[] }>("/api/v1/orders/").then(
      (p) => p.results ?? [],
    ),
  order: (id: string) => request<Order>(`/api/v1/orders/${id}/`),
  createOrder: (body: Record<string, unknown>, idempotencyKey: string) =>
    request<Order>("/api/v1/orders/", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: json(body),
    }),
  paymentByOrder: (id: string) =>
    request<Payment>(`/api/v1/payments/orders/${id}/`),
  submitEvidence: (paymentId: string, file: File) => {
    const form = new FormData();
    form.append("evidence", file);
    return request<PaymentSubmission>(
      `/api/v1/payments/${paymentId}/submissions/`,
      { method: "POST", body: form },
    );
  },

  inbox: (page = 1, pageSize = 20) =>
    request<Inbox>(
      `/api/v1/notifications/inbox/?page=${page}&page_size=${pageSize}`,
    ),
  unreadCount: () =>
    request<{ unread_count: number }>(
      "/api/v1/notifications/inbox/unread-count/",
    ),
  markRead: (body: { ids: number[] } | { all: true }) =>
    request<{ unread_count: number }>("/api/v1/notifications/inbox/read/", {
      method: "POST",
      body: json(body),
    }),

  site: () =>
    request<{ data: SiteConfig } | SiteConfig>("/api/v1/site/").then(unwrap),
  enquire: (body: Enquiry) =>
    request<{ data: { id: string; reference: string } }>("/api/v1/enquiries/", {
      method: "POST",
      body: json(body),
    }).then(unwrap),
};
