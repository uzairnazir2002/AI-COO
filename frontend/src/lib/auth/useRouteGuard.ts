"use client";

import { useSessionBootstrap } from "@/lib/auth/session";

export function useRouteGuard() {
  return useSessionBootstrap(true);
}
