import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkline } from "@/components/charts/sparkline";

export function KpiCard({
  label,
  value,
  hint,
  warning,
  sparklineData,
  sparklineKey = "value",
}: {
  label: string;
  value: string;
  hint?: string;
  warning?: boolean;
  sparklineData?: Array<Record<string, number | string>>;
  sparklineKey?: string;
}) {
  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className={warning ? "text-warning" : "text-2xl"}>{value}</CardTitle>
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
