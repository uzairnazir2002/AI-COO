"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useToastStore } from "@/components/common/use-toast";
import { apiPaths } from "@/lib/api/endpoints";
import { getAccessToken } from "@/lib/auth/tokens";
import { useAppStore } from "@/store/appStore";
import type { StreamUpdate } from "@/types/domain";

const apiBase = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const authMode = process.env.NEXT_PUBLIC_AUTH_MODE || "bearer";

export function useOrgEventFeed() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const pushToast = useToastStore((s) => s.push);
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<"idle" | "connecting" | "live" | "error">("idle");
  const lastSnapshotRef = useRef<{ openAlerts: number; cashBalance: string } | null>(null);

  useEffect(() => {
    if (!orgId) {
      setStatus("idle");
      lastSnapshotRef.current = null;
      return;
    }

    let stopped = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let controller: AbortController | null = null;

    const scheduleReconnect = () => {
      if (stopped) return;
      reconnectTimer = setTimeout(() => {
        void connect();
      }, 5000);
    };

    const handleUpdate = (update: StreamUpdate) => {
      queryClient.invalidateQueries({ queryKey: ["summary", orgId] });
      queryClient.invalidateQueries({ queryKey: ["alerts", orgId] });
      queryClient.invalidateQueries({ queryKey: ["runway", orgId] });
      queryClient.invalidateQueries({ queryKey: ["notifications", orgId] });

      const nextSnapshot = {
        openAlerts: update.open_alerts,
        cashBalance: String(update.summary.cash_balance ?? ""),
      };
      const previous = lastSnapshotRef.current;
      lastSnapshotRef.current = nextSnapshot;
      if (!previous) return;

      if (previous.openAlerts !== nextSnapshot.openAlerts) {
        pushToast({
          title: "Live alert count updated",
          description: `${nextSnapshot.openAlerts} open alerts for the selected organization.`,
          variant: nextSnapshot.openAlerts > previous.openAlerts ? "warning" : "success",
          durationMs: 4500,
        });
        return;
      }

      if (previous.cashBalance !== nextSnapshot.cashBalance) {
        pushToast({
          title: "Live financial update received",
          description: `Cash balance changed to ${nextSnapshot.cashBalance}.`,
          variant: "default",
          durationMs: 3000,
        });
      }
    };

    const parseEventBlock = (block: string) => {
      const lines = block.split(/\r?\n/);
      let eventName = "message";
      const dataLines: string[] = [];
      for (const line of lines) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (eventName !== "update" || dataLines.length === 0) return;
      try {
        handleUpdate(JSON.parse(dataLines.join("\n")) as StreamUpdate);
      } catch {
        // Ignore malformed server events and continue streaming.
      }
    };

    const connect = async () => {
      if (stopped) return;
      setStatus("connecting");
      controller = new AbortController();
      try {
        const headers = new Headers({
          Accept: "text/event-stream",
          "X-Request-ID": crypto.randomUUID(),
        });
        if (authMode !== "cookie") {
          const accessToken = getAccessToken();
          if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
        }

        const response = await fetch(
          `${apiBase}${apiPaths.eventsStream}?org_id=${orgId}&interval_seconds=10`,
          {
            method: "GET",
            headers,
            credentials: "include",
            cache: "no-store",
            signal: controller.signal,
          },
        );

        if (!response.ok || !response.body) {
          throw new Error(`Stream failed (${response.status})`);
        }

        setStatus("live");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!stopped) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() || "";
          for (const block of blocks) {
            parseEventBlock(block);
          }
        }
      } catch (error) {
        if (stopped || (error instanceof DOMException && error.name === "AbortError")) return;
        setStatus("error");
        scheduleReconnect();
      }
    };

    void connect();

    return () => {
      stopped = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      controller?.abort();
    };
  }, [orgId, pushToast, queryClient]);

  return status;
}
