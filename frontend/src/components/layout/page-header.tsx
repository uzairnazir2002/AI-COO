"use client";

import { PageActionBar } from "@/components/layout/page-action-bar";
import { cn } from "@/lib/utils/cn";

export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
  scopeChips,
  className,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  eyebrow?: string;
  scopeChips?: string[];
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-4 md:flex-row md:items-end md:justify-between", className)}>
      <div className="space-y-2">
        {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">{eyebrow}</p> : null}
        <h1 className="text-3xl font-semibold md:text-4xl">{title}</h1>
        {description ? <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p> : null}
        {scopeChips && scopeChips.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2">
            {scopeChips.map((chip) => (
              <span key={chip} className="rounded-full border border-border/70 bg-card/80 px-3 py-1 text-xs text-muted-foreground">
                {chip}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      {actions ? <PageActionBar>{actions}</PageActionBar> : null}
    </div>
  );
}
