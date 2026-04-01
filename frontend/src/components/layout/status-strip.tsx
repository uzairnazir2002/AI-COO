import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils/cn";

type StatusTone = "neutral" | "live" | "warning" | "danger";

export type StatusItem = {
  label: string;
  value: string;
  tone?: StatusTone;
};

function toBadgeVariant(tone: StatusTone) {
  if (tone === "live") return "success" as const;
  if (tone === "warning") return "warning" as const;
  if (tone === "danger") return "destructive" as const;
  return "secondary" as const;
}

export function StatusStrip({
  items,
  className,
}: {
  items: StatusItem[];
  className?: string;
}) {
  if (items.length === 0) return null;

  return (
    <div className={cn("flex flex-wrap items-center gap-2 rounded-2xl border border-border/70 bg-card/75 px-3 py-2", className)}>
      {items.map((item) => (
        <div key={`${item.label}:${item.value}`} className="flex items-center gap-2 rounded-full bg-background/70 px-2.5 py-1">
          <span className="text-xs text-muted-foreground">{item.label}</span>
          <Badge variant={toBadgeVariant(item.tone || "neutral")}>{item.value}</Badge>
        </div>
      ))}
    </div>
  );
}
