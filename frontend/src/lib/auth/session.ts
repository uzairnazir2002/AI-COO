"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { clearTokens } from "@/lib/auth/tokens";
import { bootstrapSession } from "@/lib/api/client";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";

export function useSessionBootstrap(required = true) {
  const router = useRouter();
  const setSession = useAppStore((s) => s.setSession);
  const clearSession = useAppStore((s) => s.clearSession);

  const query = useQuery({
    queryKey: qk.me,
    queryFn: bootstrapSession,
    retry: false,
  });

  useEffect(() => {
    if (query.data) {
      setSession(query.data.user, query.data.orgs);
    }
  }, [query.data, setSession]);

  useEffect(() => {
    if (query.isError) {
      clearTokens();
      clearSession();
      if (required) {
        if (typeof window !== "undefined") {
          const path = `${window.location.pathname}${window.location.search}`;
          if (!path.startsWith("/auth")) {
            window.sessionStorage.setItem("ai_coo_return_to", path);
            router.replace(`/auth/login?return_to=${encodeURIComponent(path)}`);
            return;
          }
        }
        router.replace("/auth/login");
      }
    }
  }, [query.isError, clearSession, required, router]);

  return useMemo(
    () => ({
      loading: query.isLoading,
      error: query.error,
      session: query.data,
    }),
    [query.error, query.isLoading, query.data],
  );
}
