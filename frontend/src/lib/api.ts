export type ApiError = Error & { status?: number; fields?: Record<string, string[]>; retryAfter?: string | null };
export type Category = { id: string; name: string; slug: string; description: string; image: string | null; parent: string | null };
export type ProductImage = { id: string; url: string | null; image: string | null; alt_text: string; sort_order: number; is_primary: boolean };
export type Variant = { id: string; name: string; sku?: string | null; price: string; currency: string; is_active: boolean; sort_order?: number };
export type Product = { id: string; name: string; slug: string; description: string; short_description: string; category: Category; base_price: string | null; currency: string; effective_price: string | null; weight_description?: string; preparation_time?: number | null; is_featured: boolean; primary_image: ProductImage | null; images: ProductImage[]; variants: Variant[] };
export type User = { id: string; email: string; first_name: string; last_name: string; phone_number: string; is_email_verified: boolean; date_joined: string };
export type Address = { id: string; label: string; recipient_name: string; phone_number: string; address_line_1: string; address_line_2: string; locality: string; city: string; state: string; postal_code: string; country_code: string; is_default: boolean; created_at: string; updated_at: string };
export type CustomizationOption = { id: number; product: string; option: { id: number; name: string; slug: string; description: string; input_type: string; is_active: boolean; sort_order: number; choices: unknown[] }; is_required: boolean; is_active: boolean; sort_order: number; min_selections: number; max_selections: number; choices: { id: number; choice: number; choice_name: string; price_adjustment: string; currency: string; is_active: boolean; sort_order: number }[] };
export type Cart = { id: string; status: string; currency: string; items: CartItem[]; subtotal: string; price_confirmation_required: boolean };
export type CartItem = { id: string; product: { id: string; name: string; slug: string }; variant: { id: string; name: string } | null; quantity: number; customizations: { option_id: number; option_name: string; choice_id: number | null; choice_name: string | null; text_value: string; price_adjustment: string }[]; unit_price: string; line_subtotal: string; price_confirmation_required: boolean };
export type Order = { id: string; order_number: string; status: string; payment_status: string; payment?: { status: string }; customer?: { name: string; phone: string; email: string }; pickup?: { slot_start: string; slot_end: string }; currency: string; subtotal: string; discount_total: string; tax_total: string; grand_total: string; customer_note: string; items: { id: string; product_name_snapshot: string; variant_name_snapshot: string | null; sku_snapshot: string | null; quantity: number; unit_base_price: string; unit_customization_total: string; unit_price: string; line_total: string; customizations: { option_name_snapshot: string; choice_name_snapshot: string | null; value_snapshot: string; price_adjustment: string }[] }[]; created_at: string; confirmed_at: string | null; completed_at: string | null };
export type Payment = { id: string; order: string; method: string; status: string; amount_due: string; currency: string; verified_amount: string | null; verified_at: string | null; latest_submission: { id: string; status: string; original_filename: string; content_type: string; file_size: number; rejection_reason: string; submitted_at: string; reviewed_at: string | null } | null; can_submit_evidence: boolean };
export type PaymentSubmission = { id: string; status: string; original_filename: string; content_type: string; file_size: number; rejection_reason: string; submitted_at: string; reviewed_at: string | null };
export type NotificationPreferences = { marketing_whatsapp_enabled: boolean; marketing_sms_enabled: boolean; marketing_email_enabled: boolean; marketing_consent_recorded_at: string | null; marketing_consent_source: string; updated_at: string };
export type SearchResult = { id: string; name: string; slug: string; category: { slug: string; name: string }; primary_image: string | null; price: { amount: string | null; currency: string; display_type: string }; available: boolean; match_type: string };

const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const ACCESS_TOKEN_KEY = "leeza-cakes.access-token";
const REFRESH_TOKEN_KEY = "leeza-cakes.refresh-token";
let accessToken: string | null = null;
let refreshToken: string | null = null;
function persistSession() {
  if (typeof window === "undefined") return;
  try {
    if (accessToken) window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    else window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    if (refreshToken) window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    else window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    // Storage can be unavailable in private browsing; in-memory auth still works.
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
  accessToken = null;
  refreshToken = null;
  persistSession();
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${base}${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 401 && retry && refreshToken) {
    let refreshed: Response;
    try {
      refreshed = await fetch(`${base}/api/v1/accounts/token/refresh/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh: refreshToken }), credentials: "include" });
    } catch (error) {
      throw error;
    }
    if (refreshed.ok) {
      const payload = await refreshed.json();
      const nextAccess = payload.data?.access ?? null;
      const nextRefresh = payload.data?.refresh ?? refreshToken;
      if (nextAccess) {
        setSession(nextAccess, nextRefresh);
        return request<T>(path, init, false);
      }
    } else if (refreshed.status === 400 || refreshed.status === 401) {
      clearSession();
    }
  }
  if (!response.ok) { let payload: { detail?: string; error?: { detail?: string; [key: string]: unknown }; [key: string]: unknown } = {}; try { payload = await response.json(); } catch {} const body = payload.error && typeof payload.error === "object" ? payload.error : payload; const detail = typeof body.detail === "string" ? body.detail : response.status === 429 ? "Too many attempts. Please wait a moment and try again." : response.status >= 500 ? "The bakery service is temporarily unavailable. Please try again shortly." : "Request failed"; const error = new Error(detail) as ApiError; error.status = response.status; error.retryAfter = response.headers.get("Retry-After"); error.fields = Object.fromEntries(Object.entries(body).filter(([, value]) => Array.isArray(value))) as Record<string, string[]>; throw error; }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
const unwrap = <T,>(payload: { data: T } | T) => (payload && typeof payload === "object" && "data" in payload ? payload.data : payload) as T;
export const api = {
  health: (kind: "live" | "ready" = "live") => request<{ status: string }>(`/health/${kind}/`),
  products: (query = "") => request<{ results?: Product[] } | Product[]>(`/api/v1/catalog/products/${query}`).then((p) => Array.isArray(p) ? p : p.results ?? []),
  product: (slug: string) => request<Product>(`/api/v1/catalog/products/${slug}/`),
  category: (slug: string) => request<Category>(`/api/v1/catalog/categories/${slug}/`),
  variants: (slug: string) => request<Variant[]>(`/api/v1/catalog/products/${slug}/variants/`),
  categories: () => request<{ results?: Category[] } | Category[]>("/api/v1/catalog/categories/").then((p) => Array.isArray(p) ? p : p.results ?? []),
  search: (query: string) => request<{ results: SearchResult[]; count: number; page: number; page_size: number; facets: Record<string, unknown> }>(`/api/v1/search/?${query}`),
  options: (slug: string) => request<{ product: { slug: string; name: string }; options: CustomizationOption[] }>(`/api/v1/customization/products/${slug}/options/`),
  choices: (slug: string, optionId: number) => request<unknown[]>(`/api/v1/customization/products/${slug}/options/${optionId}/choices/`),
  validateSelections: (slug: string, selections: unknown[]) => request<{ valid: boolean; selections?: unknown[]; errors?: unknown[] }>(`/api/v1/customization/products/${slug}/validate/`, { method: "POST", body: JSON.stringify({ selections }) }),
  register: (body: Record<string, unknown>) => request<{ data: User }>("/api/v1/accounts/register/", { method: "POST", body: JSON.stringify(body) }).then(unwrap),
  login: (body: { email: string; password: string }) => request<{ data: { access: string; refresh: string; user: User } }>("/api/v1/accounts/login/", { method: "POST", body: JSON.stringify(body) }).then((p) => { setSession(p.data.access, p.data.refresh); return p.data.user; }),
  logout: () => request<void>("/api/v1/accounts/logout/", { method: "POST", body: JSON.stringify({ refresh: refreshToken }) }).finally(clearSession),
  me: () => request<{ data: User }>("/api/v1/accounts/me/").then(unwrap),
  updateMe: (body: Partial<User>) => request<{ data: User }>("/api/v1/accounts/me/", { method: "PATCH", body: JSON.stringify(body) }).then(unwrap),
  changePassword: (body: { current_password: string; new_password: string; new_password_confirm: string }) => request<{ detail: string }>("/api/v1/accounts/password/change/", { method: "POST", body: JSON.stringify(body) }),
  requestPasswordReset: (email: string) => request<{ detail: string }>("/api/v1/accounts/password/reset/", { method: "POST", body: JSON.stringify({ email }) }),
  confirmPasswordReset: (body: { uid: string; token: string; new_password: string; new_password_confirm: string }) => request<{ detail: string }>("/api/v1/accounts/password/reset/confirm/", { method: "POST", body: JSON.stringify(body) }),
  requestEmailVerification: (email?: string) => request<{ detail: string }>("/api/v1/accounts/email/verification/request/", { method: "POST", body: JSON.stringify(email ? { email } : {}) }),
  confirmEmailVerification: (body: { uid: string; token: string }) => request<{ detail: string }>("/api/v1/accounts/email/verification/confirm/", { method: "POST", body: JSON.stringify(body) }),
  addresses: () => request<{ data: Address[] }>("/api/v1/accounts/addresses/").then(unwrap),
  createAddress: (body: Omit<Address, "id" | "created_at" | "updated_at" | "is_default"> & { is_default?: boolean }) => request<{ data: Address }>("/api/v1/accounts/addresses/", { method: "POST", body: JSON.stringify(body) }).then(unwrap),
  updateAddress: (id: string, body: Partial<Address>) => request<{ data: Address }>(`/api/v1/accounts/addresses/${id}/`, { method: "PATCH", body: JSON.stringify(body) }).then(unwrap),
  deleteAddress: (id: string) => request<void>(`/api/v1/accounts/addresses/${id}/`, { method: "DELETE" }),
  setDefaultAddress: (id: string) => request<{ data: Address }>(`/api/v1/accounts/addresses/${id}/set-default/`, { method: "POST" }).then(unwrap),
  cart: () => request<Cart>("/api/v1/cart/"),
  addCart: (body: { product_id: string; variant_id?: string | null; quantity: number; selections?: unknown[] }) => request<Cart>("/api/v1/cart/items/", { method: "POST", body: JSON.stringify(body) }),
  updateCartItem: (id: string, quantity: number) => request<Cart>(`/api/v1/cart/items/${id}/`, { method: "PATCH", body: JSON.stringify({ quantity }) }),
  deleteCartItem: (id: string) => request<void>(`/api/v1/cart/items/${id}/`, { method: "DELETE" }),
  updateCartCustomizations: (id: string, selections: unknown[]) => request<Cart>(`/api/v1/cart/items/${id}/customizations/`, { method: "PUT", body: JSON.stringify({ selections }) }),
  validateCart: () => request<{ valid: boolean; issues?: unknown[] }>("/api/v1/cart/validate/", { method: "POST" }),
  confirmPrices: () => request<Cart>("/api/v1/cart/confirm-prices/", { method: "POST" }),
  validateCheckout: () => request<{ valid: boolean; ready_for_checkout: boolean; errors?: unknown[] }>("/api/v1/cart/checkout/validate/", { method: "POST" }),
  mergeCart: () => request<{ merged: boolean; cart: Cart; issues: unknown[] }>("/api/v1/cart/merge/", { method: "POST" }),
  orders: (query = "") => request<{ results: Order[] }>(`/api/v1/orders/${query}`).then((p) => p.results ?? []),
  order: (id: string) => request<Order>(`/api/v1/orders/${id}/`),
  createOrder: (body: Record<string, unknown>, idempotencyKey: string) => request<Order>("/api/v1/orders/", { method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: JSON.stringify(body) }),
  paymentByOrder: (id: string) => request<Payment>(`/api/v1/payments/orders/${id}/`),
  payment: (id: string) => request<Payment>(`/api/v1/payments/${id}/`),
  paymentSubmissions: (id: string) => request<PaymentSubmission[]>(`/api/v1/payments/${id}/submissions/`),
  submitEvidence: (paymentId: string, file: File) => { const form = new FormData(); form.append("evidence", file); return request<{ id: string; status: string }>(`/api/v1/payments/${paymentId}/submissions/`, { method: "POST", body: form }); },
  paymentSubmission: (paymentId: string, submissionId: string) => request<PaymentSubmission>(`/api/v1/payments/${paymentId}/submissions/${submissionId}/`),
  notificationPreferences: () => request<NotificationPreferences>("/api/v1/notifications/preferences/"),
  updateNotificationPreferences: (body: Partial<Pick<NotificationPreferences, "marketing_whatsapp_enabled" | "marketing_sms_enabled" | "marketing_email_enabled">>) => request<NotificationPreferences>("/api/v1/notifications/preferences/", { method: "PATCH", body: JSON.stringify(body) }),
};
