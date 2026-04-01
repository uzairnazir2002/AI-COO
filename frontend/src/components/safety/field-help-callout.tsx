"use client";

import { cn } from "@/lib/utils/cn";

export function FieldHelpCallout({
  title,
  description,
  className,
}: {
  title: string;
  description: string;
  className?: string;
}) {
  return (
    <div className={cn("rounded-2xl border border-border/70 bg-card/70 p-3", className)}>
      <p className="text-xs font-semibold uppercase tracking-[0.15em] text-primary">{title}</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p>
    </div>
  );
}

