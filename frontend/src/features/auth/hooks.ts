"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useToast } from "@/components/common/use-toast";
import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import { tokenSchema, type TokenResponse } from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { setTokens } from "@/lib/auth/tokens";

export function useLogin() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const mode = process.env.NEXT_PUBLIC_AUTH_MODE || "bearer";
  const cookie = mode === "cookie";
  return useMutation({
    mutationFn: async (payload: { email: string; password: string }) =>
      api<TokenResponse>(apiPaths.login, {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
        schema: tokenSchema,
      }),
    onSuccess: async (data) => {
      if (!cookie && data.access_token && data.refresh_token) {
        setTokens(data.access_token, data.refresh_token);
      }
      await queryClient.invalidateQueries({ queryKey: qk.me });
      toast.toast({ title: "Logged in" });
    },
  });
}

export function useRegister() {
  const toast = useToast();
  return useMutation({
    mutationFn: async (payload: { email: string; password: string }) =>
      api<{ user_id: string }>(apiPaths.register, {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
      }),
    onSuccess: () => toast.toast({ title: "Account created" }),
  });
}
