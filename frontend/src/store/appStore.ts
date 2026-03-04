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
  setSelectedOrgId: (orgId: string | null) => void;
  setSession: (user: MeUser, orgs: MeOrg[]) => void;
  clearSession: () => void;
};

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      selectedOrgId: null,
      user: null,
      orgs: [],
      setSelectedOrgId: (selectedOrgId) => {
        if (typeof document !== "undefined" && selectedOrgId) {
          document.cookie = `ai_coo_selected_org=${selectedOrgId}; path=/; max-age=31536000; SameSite=Lax`;
        }
        set({ selectedOrgId });
      },
      setSession: (user, orgs) => {
        const prev = get().selectedOrgId;
        const selectedOrgId = prev && orgs.some((o) => o.org_id === prev) ? prev : orgs[0]?.org_id ?? null;
        if (typeof document !== "undefined" && selectedOrgId) {
          document.cookie = `ai_coo_selected_org=${selectedOrgId}; path=/; max-age=31536000; SameSite=Lax`;
        }
        set({ user, orgs, selectedOrgId });
      },
      clearSession: () => set({ selectedOrgId: null, user: null, orgs: [] }),
    }),
    { name: "ai-coo-app-store", partialize: (s) => ({ selectedOrgId: s.selectedOrgId }) },
  ),
);
