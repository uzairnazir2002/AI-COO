"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

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
      clearSession();
      if (required) {
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
