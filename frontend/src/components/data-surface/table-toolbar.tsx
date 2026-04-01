"use client";

import { cn } from "@/lib/utils/cn";

export function TableToolbar({
  left,
  right,
  className,
}: {
  left?: React.ReactNode;
  right?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/70 bg-card/75 px-3 py-2", className)}>
      <div className="flex flex-wrap items-center gap-2">{left}</div>
      <div className="flex flex-wrap items-center gap-2">{right}</div>
    </div>
  );
}

