"use client";

import { create } from "zustand";

type Toast = { id: string; title: string; description?: string; variant?: "default" | "danger" };

type ToastState = {
  toasts: Toast[];
  push: (toast: Omit<Toast, "id">) => void;
  remove: (id: string) => void;
};

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (toast) =>
    set((state) => ({ toasts: [...state.toasts, { ...toast, id: crypto.randomUUID() }] })),
  remove: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));

export function useToast() {
  const push = useToastStore((s) => s.push);
  return {
    toast: push,
  };
}
