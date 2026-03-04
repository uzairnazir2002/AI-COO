import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function KpiCard({
  label,
  value,
  hint,
  warning,
}: {
  label: string;
  value: string;
  hint?: string;
  warning?: boolean;
}) {
  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className={warning ? "text-warning" : "text-2xl"}>{value}</CardTitle>
      </CardHeader>
      {hint ? <CardContent className="pt-0 text-xs text-muted-foreground">{hint}</CardContent> : null}
    </Card>
  );
}
