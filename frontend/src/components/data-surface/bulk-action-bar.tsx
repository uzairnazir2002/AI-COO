"use client";

import { cn } from "@/lib/utils/cn";

export function BulkActionBar({
  visible,
  summary,
  actions,
  className,
}: {
  visible: boolean;
  summary: React.ReactNode;
  actions: React.ReactNode;
  className?: string;
}) {
  if (!visible) return null;
  return (
    <div
      className={cn(
        "fixed bottom-4 left-1/2 z-40 flex w-[min(92vw,860px)] -translate-x-1/2 items-center justify-between gap-3 rounded-2xl border border-border/70 bg-background/95 px-4 py-3 shadow-xl backdrop-blur",
        className,
      )}
    >
      <div className="text-sm text-muted-foreground">{summary}</div>
      <div className="flex items-center gap-2">{actions}</div>
    </div>
  );
}

