"use client";

import { create } from "zustand";

export type ToastVariant = "default" | "success" | "warning" | "danger";
export type Toast = {
  id: string;
  title: string;
  description?: string;
  variant?: ToastVariant;
  createdAt: number;
  dismissAt: number;
};

type ToastState = {
  toasts: Toast[];
  history: Toast[];
  push: (toast: { title: string; description?: string; variant?: ToastVariant; durationMs?: number }) => void;
  remove: (id: string) => void;
  markAllRead: () => void;
  clearHistory: () => void;
};

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  history: [],
  push: (toast) =>
    set((state) => {
      const now = Date.now();
      const normalizedTitle = toast.title.trim().toLowerCase();
      const normalizedDescription = (toast.description || "").trim().toLowerCase();
      const duplicate = state.toasts.find(
        (item) =>
          item.title.trim().toLowerCase() === normalizedTitle &&
          (item.description || "").trim().toLowerCase() === normalizedDescription &&
          now - item.createdAt < 1600,
      );
      if (duplicate) {
        return state;
      }
      const durationMs = toast.durationMs ?? 3500;
      const next: Toast = {
        id: crypto.randomUUID(),
        title: toast.title,
        description: toast.description,
        variant: toast.variant ?? "default",
        createdAt: now,
        dismissAt: now + durationMs,
      };
      const capped = [next, ...state.toasts].slice(0, 4);
      const history = [next, ...state.history].slice(0, 100);
      return { toasts: capped, history };
    }),
  remove: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  markAllRead: () => set((state) => ({ toasts: [] })),
  clearHistory: () => set({ history: [] }),
}));

export function useToast() {
  const push = useToastStore((s) => s.push);
  return {
    toast: push,
  };
}
