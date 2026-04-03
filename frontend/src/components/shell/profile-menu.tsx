"use client";

import { useEffect, useRef, useState } from "react";
import { LogOut, ShieldCheck, UserRound } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils/cn";
import type { ExperienceTier } from "@/store/appStore";

export function ProfileMenu({
  email,
  role,
  experienceTier,
  onExperienceTierChange,
  onLogout,
  className,
}: {
  email?: string;
  role?: string;
  experienceTier: ExperienceTier;
  onExperienceTierChange: (value: ExperienceTier) => void;
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
            <div className="mt-3 space-y-1">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Workspace mode</p>
              <Select value={experienceTier} onValueChange={(value) => onExperienceTierChange(value as ExperienceTier)}>
                <SelectTrigger data-testid="profile-tier-select" className="h-9 rounded-xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="simple">Simple</SelectItem>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="advanced">Advanced</SelectItem>
                </SelectContent>
              </Select>
            </div>
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
