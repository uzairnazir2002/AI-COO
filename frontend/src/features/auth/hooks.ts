"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useToast } from "@/components/common/use-toast";
import { api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import {
  registerOutSchema,
  resendConfirmationSchema,
  tokenSchema,
  type RegisterOutResponse,
  type ResendConfirmationResponse,
  type TokenResponse,
} from "@/lib/api/schemas";
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
      api<RegisterOutResponse>(apiPaths.register, {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
        schema: registerOutSchema,
      }),
    onSuccess: () => toast.toast({ title: "Account created" }),
  });
}

export function useConfirmRegistration() {
  const toast = useToast();
  return useMutation({
    mutationFn: async (payload: { token: string; password?: string }) =>
      api<RegisterOutResponse>(apiPaths.confirm, {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
        schema: registerOutSchema,
      }),
    onSuccess: () => toast.toast({ title: "Account confirmed", description: "You can sign in now.", variant: "success" }),
  });
}

export function useAcceptInvite() {
  const toast = useToast();
  return useMutation({
    mutationFn: async (payload: { token: string; password: string }) =>
      api<RegisterOutResponse>(apiPaths.inviteAccept, {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
        schema: registerOutSchema,
      }),
    onSuccess: () => toast.toast({ title: "Invite accepted", description: "Your account is ready. Sign in to continue.", variant: "success" }),
  });
}

export function useResendConfirmation() {
  const toast = useToast();
  return useMutation({
    mutationFn: async (payload: { email: string }) =>
      api<ResendConfirmationResponse>(apiPaths.resendConfirmation, {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
        schema: resendConfirmationSchema,
      }),
    onSuccess: (data) => {
      if (data.already_active) {
        toast.toast({ title: "Account already active", description: "You can sign in directly.", variant: "warning" });
        return;
      }
      toast.toast({ title: data.sent ? "Confirmation re-issued" : "No pending account found" });
    },
  });
}
