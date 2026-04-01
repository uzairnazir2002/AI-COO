"use client";

import { AlertTriangle } from "lucide-react";

import { cn } from "@/lib/utils/cn";

export function InlineErrorBanner({
  message,
  className,
}: {
  message: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start gap-2 rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger", className)}>
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

