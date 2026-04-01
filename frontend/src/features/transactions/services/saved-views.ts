import { type TxFilters } from "@/components/common/filters-bar";

export type SavedTransactionView = {
  id: string;
  name: string;
  filters: TxFilters;
};

function viewsStorageKey(orgId: string) {
  return `tx-saved-views-${orgId}`;
}

function activeStorageKey(orgId: string) {
  return `tx-saved-view-active-${orgId}`;
}

function isValidFilters(value: unknown): value is TxFilters {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<TxFilters>;
  return typeof candidate.from === "string"
    && typeof candidate.to === "string"
    && typeof candidate.type === "string"
    && typeof candidate.category === "string"
    && typeof candidate.q === "string";
}

function isValidView(value: unknown): value is SavedTransactionView {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<SavedTransactionView>;
  return typeof candidate.id === "string"
    && typeof candidate.name === "string"
    && isValidFilters(candidate.filters);
}

export function loadSavedTransactionViews(orgId: string): { views: SavedTransactionView[]; activeViewId: string } {
  if (typeof window === "undefined") return { views: [], activeViewId: "" };
  try {
    const raw = window.localStorage.getItem(viewsStorageKey(orgId));
    const parsed = raw ? JSON.parse(raw) : [];
    const views = Array.isArray(parsed) ? parsed.filter(isValidView) : [];
    const activeViewId = window.localStorage.getItem(activeStorageKey(orgId)) || "";
    return { views, activeViewId };
  } catch {
    return { views: [], activeViewId: "" };
  }
}

export function persistSavedTransactionViews(orgId: string, views: SavedTransactionView[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(viewsStorageKey(orgId), JSON.stringify(views));
}

export function persistActiveTransactionView(orgId: string, activeViewId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(activeStorageKey(orgId), activeViewId);
}
