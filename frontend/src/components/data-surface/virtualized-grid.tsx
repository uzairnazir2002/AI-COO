"use client";

import { cn } from "@/lib/utils/cn";

export function VirtualizedGrid({
  header,
  body,
  footer,
  className,
}: {
  header: React.ReactNode;
  body: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-2xl border border-border", className)}>
      <div className="overflow-x-auto">{header}</div>
      <div>{body}</div>
      {footer ? <div className="border-t border-border/70 px-3 py-2">{footer}</div> : null}
    </div>
  );
}

