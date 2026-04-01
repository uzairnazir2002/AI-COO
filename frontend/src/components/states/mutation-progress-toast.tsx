"use client";

import { LoaderCircle } from "lucide-react";

export function MutationProgressToast({
  label,
}: {
  label: string;
}) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/85 px-3 py-1.5 text-xs text-muted-foreground">
      <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
      {label}
    </div>
  );
}

