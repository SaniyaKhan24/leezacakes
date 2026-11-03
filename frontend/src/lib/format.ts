const rupees = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});
const rupeesExact = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function money(
  amount: string | number | null | undefined,
  exact = false,
) {
  if (amount === null || amount === undefined || amount === "") return "—";
  const value = Number(amount);
  if (!Number.isFinite(value)) return "—";
  return exact || !Number.isInteger(value)
    ? rupeesExact.format(value)
    : rupees.format(value);
}

const TZ = "Asia/Kolkata";

export function slotDay(iso: string) {
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: TZ,
  }).format(new Date(iso));
}

export function slotTime(iso: string) {
  return new Intl.DateTimeFormat("en-IN", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: TZ,
  })
    .format(new Date(iso))
    .replace(" ", " ");
}

export function slotRange(start: string, end: string) {
  return `${slotTime(start)} – ${slotTime(end)}`;
}

export function shortDate(iso: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: TZ,
  }).format(new Date(iso));
}

export function dayParts(date: string) {
  const d = new Date(`${date}T12:00:00+05:30`);
  return {
    weekday: new Intl.DateTimeFormat("en-IN", {
      weekday: "short",
      timeZone: TZ,
    }).format(d),
    day: new Intl.DateTimeFormat("en-IN", {
      day: "numeric",
      timeZone: TZ,
    }).format(d),
    month: new Intl.DateTimeFormat("en-IN", {
      month: "short",
      timeZone: TZ,
    }).format(d),
  };
}

export function leadTime(minutes?: number | null) {
  if (!minutes) return null;
  if (minutes < 60 * 12) return `${Math.round(minutes / 60)} hours' notice`;
  const days = Math.round(minutes / 1440);
  return days === 1 ? "24 hours' notice" : `${days} days' notice`;
}

export const ORDER_STEPS = [
  { key: "pending_payment_verification", label: "Payment check" },
  { key: "confirmed", label: "Confirmed" },
  { key: "preparing", label: "In the oven" },
  { key: "ready_for_pickup", label: "Ready for pickup" },
  { key: "completed", label: "Collected" },
] as const;

export function statusLabel(status: string) {
  if (status === "cancelled") return "Cancelled";
  return (
    ORDER_STEPS.find((s) => s.key === status)?.label ??
    status.replaceAll("_", " ")
  );
}

export function newIdempotencyKey() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
