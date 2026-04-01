"use client";

import { AlertTriangle } from "lucide-react";

import { cn } from "@/lib/utils/cn";

export function InlineValidationHint({
  message,
  className,
}: {
  message: string | null | undefined;
  className?: string;
}) {
  if (!message) return null;
  return (
    <p className={cn("mt-2 inline-flex items-center gap-1.5 text-xs text-danger", className)}>
      <AlertTriangle className="h-3.5 w-3.5" />
      {message}
    </p>
  );
}

