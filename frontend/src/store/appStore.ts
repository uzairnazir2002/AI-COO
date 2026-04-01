"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type OrgRole = "OWNER" | "EDITOR" | "VIEWER";

export type MeOrg = { org_id: string; role: OrgRole; name: string };
export type MeUser = { id: string; email: string; created_at: string };

type AppState = {
  selectedOrgId: string | null;
  selectedLocationId: string | null;
  user: MeUser | null;
  orgs: MeOrg[];
  shellCollapsed: boolean;
  globalDateRange: { from: string; to: string };
  cashflowGranularity: "day" | "week" | "month";
  setSelectedOrgId: (orgId: string | null) => void;
  setSelectedLocationId: (locationId: string | null) => void;
  setSession: (user: MeUser, orgs: MeOrg[]) => void;
  setShellCollapsed: (collapsed: boolean) => void;
  setGlobalDateRange: (range: { from: string; to: string }) => void;
  setCashflowGranularity: (value: "day" | "week" | "month") => void;
  clearSession: () => void;
};

function localDateISO(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startOfMonthISO(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}-01`;
}

function normalizeDateRange(range: { from: string; to: string }) {
  if (range.from <= range.to) return range;
  const fallbackFrom = `${range.to.slice(0, 7)}-01`;
  return { from: fallbackFrom <= range.to ? fallbackFrom : range.to, to: range.to };
}

function persistSelectedOrgCookie(selectedOrgId: string | null) {
  if (typeof document === "undefined") return;
  if (selectedOrgId) {
    document.cookie = `ai_coo_selected_org=${selectedOrgId}; path=/; max-age=31536000; SameSite=Lax`;
    return;
  }
  document.cookie = "ai_coo_selected_org=; path=/; max-age=0; SameSite=Lax";
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...(() => {
        const today = localDateISO(new Date());
        return {
          globalDateRange: normalizeDateRange({
            from: startOfMonthISO(new Date()),
            to: today,
          }),
        };
      })(),
      selectedOrgId: null,
      selectedLocationId: null,
      user: null,
      orgs: [],
      shellCollapsed: false,
      cashflowGranularity: "week",
      setSelectedOrgId: (selectedOrgId) => {
        persistSelectedOrgCookie(selectedOrgId);
        set({ selectedOrgId, selectedLocationId: null });
      },
      setSelectedLocationId: (selectedLocationId) => set({ selectedLocationId }),
      setSession: (user, orgs) => {
        const prev = get().selectedOrgId;
        const selectedOrgId = prev && orgs.some((o) => o.org_id === prev) ? prev : orgs[0]?.org_id ?? null;
        persistSelectedOrgCookie(selectedOrgId);
        set({ user, orgs, selectedOrgId, selectedLocationId: null });
      },
      setShellCollapsed: (shellCollapsed) => set({ shellCollapsed }),
      setGlobalDateRange: (globalDateRange) => set({ globalDateRange: normalizeDateRange(globalDateRange) }),
      setCashflowGranularity: (cashflowGranularity) => set({ cashflowGranularity }),
      clearSession: () => {
        persistSelectedOrgCookie(null);
        set({ selectedOrgId: null, selectedLocationId: null, user: null, orgs: [] });
      },
    }),
    {
      name: "ai-coo-app-store",
      merge: (persisted, current) => {
        const persistedState = (persisted as Partial<AppState> | undefined) ?? {};
        const dateRange = persistedState.globalDateRange
          ? normalizeDateRange(persistedState.globalDateRange)
          : current.globalDateRange;
        return {
          ...current,
          ...persistedState,
          globalDateRange: dateRange,
        };
      },
      partialize: (s) => ({
        selectedOrgId: s.selectedOrgId,
        selectedLocationId: s.selectedLocationId,
        shellCollapsed: s.shellCollapsed,
        globalDateRange: s.globalDateRange,
        cashflowGranularity: s.cashflowGranularity,
      }),
    },
  ),
);
