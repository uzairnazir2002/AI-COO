"use client";

import { Lock } from "lucide-react";

import { cn } from "@/lib/utils/cn";

export function RoleAwareDisabledHint({
  role,
  requiredRole,
  className,
}: {
  role?: string | null;
  requiredRole: "OWNER" | "EDITOR";
  className?: string;
}) {
  return (
    <p className={cn("inline-flex items-center gap-1.5 text-xs text-muted-foreground", className)}>
      <Lock className="h-3.5 w-3.5" />
      Requires {requiredRole} role. Current role: {role ?? "unknown"}.
    </p>
  );
}

