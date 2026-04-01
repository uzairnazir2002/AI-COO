import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkline } from "@/components/charts/sparkline";
import { Badge } from "@/components/ui/badge";
import { ChevronRight } from "lucide-react";

export function KpiCard({
  label,
  value,
  hint,
  warning,
  delta,
  insight,
  sparklineData,
  sparklineKey = "value",
  onClick,
}: {
  label: string;
  value: string;
  hint?: string;
  warning?: boolean;
  delta?: string;
  insight?: string;
  sparklineData?: Array<Record<string, number | string>>;
  sparklineKey?: string;
  onClick?: () => void;
}) {
  return (
    <Card
      className={`animate-fade-in rounded-3xl border-border/70 bg-card/85 ${onClick ? "cursor-pointer transition hover:border-primary/40 hover:shadow-sm" : ""}`}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        onClick
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <CardHeader className="space-y-1">
        <CardDescription>{label}</CardDescription>
        <CardTitle className={warning ? "text-2xl text-warning" : "text-2xl"}>{value}</CardTitle>
        {onClick ? (
          <div className="inline-flex items-center gap-1 text-[11px] font-medium text-primary">
            <span>View calculation</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </div>
        ) : null}
        {(delta || insight) ? (
          <div className="flex flex-wrap items-center gap-2">
            {delta ? <Badge variant={warning ? "warning" : "secondary"}>{delta}</Badge> : null}
            {insight ? <span className="text-xs text-muted-foreground">{insight}</span> : null}
          </div>
        ) : null}
      </CardHeader>
      {hint || (sparklineData && sparklineData.length > 1) ? (
        <CardContent className="space-y-2 pt-0">
          {sparklineData && sparklineData.length > 1 ? <Sparkline data={sparklineData} dataKey={sparklineKey} color={warning ? "hsl(var(--warning))" : "hsl(var(--primary))"} /> : null}
          {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
        </CardContent>
      ) : null}
    </Card>
  );
}
