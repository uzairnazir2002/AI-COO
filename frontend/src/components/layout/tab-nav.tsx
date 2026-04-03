import { cn } from "@/lib/utils/cn";
import { KeyboardEvent, useId, useRef } from "react";

export type TabNavItem = {
  id: string;
  label: string;
};

export function TabNav({
  items,
  active,
  onChange,
  ariaLabel = "Section tabs",
  className,
}: {
  items: TabNavItem[];
  active: string;
  onChange: (id: string) => void;
  ariaLabel?: string;
  className?: string;
}) {
  const tablistId = useId();
  const panelPrefix = `${tablistId}-panel`;
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    if (event.key === "Home") {
      onChange(items[0].id);
      tabRefs.current[0]?.focus();
      return;
    }
    if (event.key === "End") {
      onChange(items[items.length - 1].id);
      tabRefs.current[items.length - 1]?.focus();
      return;
    }
    const delta = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (currentIndex + delta + items.length) % items.length;
    onChange(items[nextIndex].id);
    tabRefs.current[nextIndex]?.focus();
  };

  return (
    <div
      role="tablist"
      id={tablistId}
      aria-label={ariaLabel}
      className={cn("flex flex-wrap items-center gap-2 rounded-2xl border border-border/70 bg-card/75 p-2", className)}
    >
      {items.map((item, index) => (
        <button
          key={item.id}
          id={`${tablistId}-tab-${item.id}`}
          ref={(el) => {
            tabRefs.current[index] = el;
          }}
          type="button"
          onClick={() => onChange(item.id)}
          onKeyDown={(event) => onKeyDown(event, index)}
          role="tab"
          aria-selected={active === item.id}
          aria-controls={`${panelPrefix}-${item.id}`}
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
