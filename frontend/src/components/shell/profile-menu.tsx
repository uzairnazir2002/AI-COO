"use client";

import { useEffect, useRef, useState } from "react";
import { LogOut, ShieldCheck, UserRound } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

export function ProfileMenu({
  email,
  role,
  onLogout,
  className,
}: {
  email?: string;
  role?: string;
  onLogout: () => Promise<void>;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEscape);
    };
  }, []);

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <Button variant="outline" className="rounded-2xl" onClick={() => setOpen((value) => !value)} aria-label="Profile menu">
        <UserRound className="mr-2 h-4 w-4" />
        Profile
      </Button>
      {open ? (
        <div className="absolute right-0 z-50 mt-2 w-64 rounded-2xl border border-border bg-card p-3 shadow-xl">
          <div className="rounded-xl border border-border/70 bg-background/70 p-3">
            <p className="truncate text-sm font-medium">{email || "Unknown user"}</p>
            <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="h-3.5 w-3.5" />
              Secure session
            </div>
            {role ? <Badge className="mt-2" variant="secondary">{role}</Badge> : null}
          </div>
          <Button
            className="mt-3 w-full"
            variant="outline"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              await onLogout();
            }}
          >
            <LogOut className="mr-2 h-4 w-4" />
            {busy ? "Logging out..." : "Logout"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
