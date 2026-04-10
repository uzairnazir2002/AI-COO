"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "@/lib/api/client";
import { apiPaths } from "@/lib/api/endpoints";
import {
  aiChatResponseSchema,
  aiChatSessionDetailSchema,
  aiChatSessionSchema,
} from "@/lib/api/schemas";
import { qk } from "@/lib/query/keys";
import { useAppStore } from "@/store/appStore";
import type { AiChatMessage, AiChatSession, AiChatSessionDetail } from "@/types/domain";

type ListSessionOpts = {
  mineOnly?: boolean;
  limit?: number;
};

type CreateSessionPayload = {
  title?: string;
};

type SendMessagePayload = {
  sessionId: string;
  message: string;
  from: string;
  to: string;
};

export function useAiChatSessions(opts?: ListSessionOpts) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const mineOnly = Boolean(opts?.mineOnly);
  const limit = opts?.limit ?? 30;
  return useQuery({
    queryKey: qk.aiChatSessions(orgId || "", mineOnly, limit),
    queryFn: async () => {
      const qs = new URLSearchParams({
        org_id: orgId || "",
        mine_only: String(mineOnly),
        limit: String(limit),
      });
      const out = await api<AiChatSession[]>(`${apiPaths.aiChatSessions}?${qs.toString()}`);
      return out.map((row) => aiChatSessionSchema.parse(row));
    },
    enabled: Boolean(orgId),
  });
}

export function useAiChatSession(sessionId: string | null) {
  const orgId = useAppStore((s) => s.selectedOrgId);
  return useQuery({
    queryKey: qk.aiChatSession(orgId || "", sessionId || ""),
    queryFn: async () => {
      const qs = new URLSearchParams({ org_id: orgId || "" });
      const out = await api<AiChatSessionDetail>(`${apiPaths.aiChatSessionById(sessionId || "")}?${qs.toString()}`);
      return aiChatSessionDetailSchema.parse(out);
    },
    enabled: Boolean(orgId && sessionId),
  });
}

export function useCreateAiChatSession() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateSessionPayload) => {
      if (!orgId) {
        throw new ApiError("Select an organization before starting an AI chat session.", 400);
      }
      const out = await api<AiChatSession>(apiPaths.aiChatSessions, {
        method: "POST",
        body: JSON.stringify({
          org_id: orgId,
          title: payload.title || undefined,
        }),
      });
      return aiChatSessionSchema.parse(out);
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["aiChatSessions", orgId || ""] });
    },
  });
}

export function useSendAiChatMessage() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SendMessagePayload) => {
      if (!orgId) {
        throw new ApiError("Select an organization before sending messages.", 400);
      }
      const out = await api<{ session_id: string; message: AiChatMessage }>(apiPaths.aiChat, {
        method: "POST",
        body: JSON.stringify({
          org_id: orgId,
          session_id: payload.sessionId,
          message: payload.message,
          from: payload.from,
          to: payload.to,
        }),
      });
      return aiChatResponseSchema.parse(out);
    },
    onSuccess: async (result) => {
      await qc.invalidateQueries({ queryKey: qk.aiChatSession(orgId || "", result.session_id) });
      await qc.invalidateQueries({ queryKey: ["aiChatSessions", orgId || ""] });
    },
  });
}
