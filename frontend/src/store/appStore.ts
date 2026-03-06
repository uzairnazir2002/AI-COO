"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type OrgRole = "OWNER" | "EDITOR" | "VIEWER";

export type MeOrg = { org_id: string; role: OrgRole; name: string };
export type MeUser = { id: string; email: string; created_at: string };

type AppState = {
  selectedOrgId: string | null;
  user: MeUser | null;
  orgs: MeOrg[];
  shellCollapsed: boolean;
  globalDateRange: { from: string; to: string };
  cashflowGranularity: "day" | "week" | "month";
  setSelectedOrgId: (orgId: string | null) => void;
  setSession: (user: MeUser, orgs: MeOrg[]) => void;
  setShellCollapsed: (collapsed: boolean) => void;
  setGlobalDateRange: (range: { from: string; to: string }) => void;
  setCashflowGranularity: (value: "day" | "week" | "month") => void;
  clearSession: () => void;
};

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
      selectedOrgId: null,
      user: null,
      orgs: [],
      shellCollapsed: false,
      globalDateRange: {
        from: `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}-01`,
        to: new Date().toISOString().slice(0, 10),
      },
      cashflowGranularity: "week",
      setSelectedOrgId: (selectedOrgId) => {
        persistSelectedOrgCookie(selectedOrgId);
        set({ selectedOrgId });
      },
      setSession: (user, orgs) => {
        const prev = get().selectedOrgId;
        const selectedOrgId = prev && orgs.some((o) => o.org_id === prev) ? prev : orgs[0]?.org_id ?? null;
        persistSelectedOrgCookie(selectedOrgId);
        set({ user, orgs, selectedOrgId });
      },
      setShellCollapsed: (shellCollapsed) => set({ shellCollapsed }),
      setGlobalDateRange: (globalDateRange) => set({ globalDateRange }),
      setCashflowGranularity: (cashflowGranularity) => set({ cashflowGranularity }),
      clearSession: () => {
        persistSelectedOrgCookie(null);
        set({ selectedOrgId: null, user: null, orgs: [] });
      },
    }),
    {
      name: "ai-coo-app-store",
      partialize: (s) => ({
        selectedOrgId: s.selectedOrgId,
        shellCollapsed: s.shellCollapsed,
        globalDateRange: s.globalDateRange,
        cashflowGranularity: s.cashflowGranularity,
      }),
    },
  ),
);
