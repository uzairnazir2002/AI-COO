"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { useToast } from "@/components/common/use-toast";
import { Button } from "@/components/ui/button";
import { API_CLIENT_EVENT_NAME, type ApiClientEventDetail } from "@/lib/api/events";
import { clearTokens } from "@/lib/auth/tokens";
import { useAppStore } from "@/store/appStore";

function sanitizeReturnTo(value: string | null | undefined) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return "/app/dashboard";
  return value;
}

export function GlobalApiFeedback() {
  const pathname = usePathname();
  const router = useRouter();
  const queryClient = useQueryClient();
  const clearSession = useAppStore((s) => s.clearSession);
  const toast = useToast();

  const [open, setOpen] = useState(false);
  const [returnTo, setReturnTo] = useState("/app/dashboard");
  const lastNetworkToastAt = useRef(0);

  const isAuthRoute = useMemo(() => pathname.startsWith("/auth/"), [pathname]);

  useEffect(() => {
    const onEvent = (event: Event) => {
      const detail = (event as CustomEvent<ApiClientEventDetail>).detail;
      if (!detail) return;

      if (detail.kind === "network_error") {
        const now = Date.now();
        if (now - lastNetworkToastAt.current > 5000) {
          lastNetworkToastAt.current = now;
          toast.toast({
            title: "Network request failed",
            description: "Check backend availability and CORS/API URL settings.",
            variant: "warning",
          });
        }
        return;
      }

      if (detail.kind === "auth_expired") {
        if (isAuthRoute) return;
        const current = typeof window !== "undefined" ? `${window.location.pathname}${window.location.search}` : pathname;
        setReturnTo(sanitizeReturnTo(current));
        clearTokens();
        clearSession();
        queryClient.clear();
        toast.toast({
          title: "Session expired",
          description: "Please sign in again to continue.",
          variant: "warning",
        });
        setOpen(true);
      }
    };

    window.addEventListener(API_CLIENT_EVENT_NAME, onEvent as EventListener);
    return () => window.removeEventListener(API_CLIENT_EVENT_NAME, onEvent as EventListener);
  }, [clearSession, isAuthRoute, pathname, queryClient, toast]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[130] flex items-center justify-center bg-background/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-[24px] border border-border bg-card p-6 shadow-2xl">
        <h2 className="text-xl font-semibold">Session expired</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Your authentication session ended. Re-login to resume from where you left off.
        </p>
        <div className="mt-5 flex justify-end">
          <Button
            onClick={() => {
              const target = sanitizeReturnTo(returnTo);
              setOpen(false);
              if (typeof window !== "undefined") {
                window.sessionStorage.setItem("ai_coo_return_to", target);
              }
              router.replace(`/auth/login?return_to=${encodeURIComponent(target)}`);
            }}
          >
            Re-login
          </Button>
          <Button variant="outline" className="ml-2" onClick={() => setOpen(false)}>
            Dismiss
          </Button>
        </div>
      </div>
    </div>
  );
}
