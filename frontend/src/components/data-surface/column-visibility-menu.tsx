"use client";

import { cn } from "@/lib/utils/cn";

type ColumnVisibilityItem = {
  id: string;
  label: string;
  visible: boolean;
  canHide?: boolean;
};

export function ColumnVisibilityMenu({
  items,
  onToggle,
  className,
}: {
  items: ColumnVisibilityItem[];
  onToggle: (id: string, visible: boolean) => void;
  className?: string;
}) {
  return (
    <details className={cn("relative", className)} data-testid="column-visibility-menu">
      <summary aria-label="Toggle visible columns" className="h-8 cursor-pointer rounded-md border border-border/70 px-3 py-1 text-sm text-muted-foreground">
        Columns
      </summary>
      <div className="absolute right-0 z-20 mt-2 w-56 space-y-2 rounded-xl border border-border/80 bg-background p-3 shadow-lg">
        {items.map((item) => (
          <label key={item.id} className="flex items-center justify-between gap-2 text-sm">
            <span className={item.visible ? "text-foreground" : "text-muted-foreground"}>{item.label}</span>
            <input
              type="checkbox"
              checked={item.visible}
              disabled={item.canHide === false}
              onChange={(event) => onToggle(item.id, event.target.checked)}
              data-testid={`column-visibility-toggle-${item.id}`}
            />
          </label>
        ))}
      </div>
    </details>
  );
}
