import { cn } from "@/lib/utils/cn";
import { KeyboardEvent, useId } from "react";

export type TabNavItem = {
  id: string;
  label: string;
};

export function TabNav({
  items,
  active,
  onChange,
  className,
}: {
  items: TabNavItem[];
  active: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  const tablistId = useId();

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    if (event.key === "Home") {
      onChange(items[0].id);
      return;
    }
    if (event.key === "End") {
      onChange(items[items.length - 1].id);
      return;
    }
    const delta = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (currentIndex + delta + items.length) % items.length;
    onChange(items[nextIndex].id);
  };

  return (
    <div
      role="tablist"
      aria-label="Section tabs"
      className={cn("flex flex-wrap items-center gap-2 rounded-2xl border border-border/70 bg-card/75 p-2", className)}
    >
      {items.map((item, index) => (
        <button
          key={item.id}
          id={`${tablistId}-tab-${item.id}`}
          type="button"
          onClick={() => onChange(item.id)}
          onKeyDown={(event) => onKeyDown(event, index)}
          role="tab"
          aria-selected={active === item.id}
          tabIndex={active === item.id ? 0 : -1}
          className={cn(
            "rounded-xl px-3 py-2 text-sm transition",
            active === item.id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
