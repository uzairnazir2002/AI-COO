const defaultLocale =
  typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-US";

export function formatMoney(value: string | number | null | undefined, currency = "USD", locale = defaultLocale) {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: Math.abs(n) >= 1000 ? 0 : 2,
  }).format(n);
}

export function formatCompactMoney(value: string | number | null | undefined, currency = "USD", locale = defaultLocale) {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}

export function formatDate(value: string) {
  return new Date(value).toLocaleDateString(defaultLocale, { month: "short", day: "numeric", year: "numeric" });
}

export function formatMonth(value: string) {
  return new Date(`${value}-01`).toLocaleDateString(defaultLocale, { month: "short", year: "numeric" });
}

export function formatPercent(value: string | number | null | undefined, digits = 1) {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat(defaultLocale, {
    style: "percent",
    maximumFractionDigits: digits,
    minimumFractionDigits: digits > 0 ? 1 : 0,
  }).format(n / 100);
}

export function formatDelta(value: string | number | null | undefined) {
  const n = Number(value ?? 0);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

export function startOfMonthISO(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-01`;
}

export function todayISO(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

export function weekStartISO(date = new Date()) {
  const day = date.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  const start = new Date(date);
  start.setDate(date.getDate() + diff);
  return start.toISOString().slice(0, 10);
}

export function shiftDaysISO(value: string, days: number) {
  const date = new Date(`${value}T00:00:00`);
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

export function daysBetween(from: string, to: string) {
  const start = new Date(`${from}T00:00:00`).getTime();
  const end = new Date(`${to}T00:00:00`).getTime();
  return Math.max(1, Math.round((end - start) / 86_400_000) + 1);
}
