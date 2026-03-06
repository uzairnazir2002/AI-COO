import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { alertImpactValue, normalizeImpact, toNumber } from "@/lib/utils/chart";
import { formatMoney } from "@/lib/utils/format";
import type { Alert } from "@/types/domain";

function severityVariant(severity: Alert["severity"]) {
  if (severity === "HIGH") return "destructive" as const;
  if (severity === "MEDIUM") return "warning" as const;
  return "success" as const;
}

export function AlertCard({
  alert,
  maxImpact = 100,
  onDismiss,
  onOpen,
}: {
  alert: Alert;
  maxImpact?: number;
  onDismiss?: (id: string) => void;
  onOpen?: (id: string) => void;
}) {
  const impact = alertImpactValue(alert.meta);
  const barWidth = normalizeImpact(impact, maxImpact);
  const variance = toNumber(alert.meta?.variance_pct);
  const baseline = toNumber(alert.meta?.baseline);
  const latest = toNumber(alert.meta?.latest);

  return (
    <Card className="transition hover:-translate-y-0.5">
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant={severityVariant(alert.severity)}>{alert.severity}</Badge>
            <Badge variant="secondary">{alert.kind}</Badge>
          </div>
          <h4 className="font-medium">{alert.title}</h4>
          <p className="text-sm text-muted-foreground">{alert.description}</p>
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Impact</span>
              <span>{impact > 0 ? formatMoney(impact) : "n/a"}</span>
            </div>
            <div className="h-2 rounded-full bg-muted">
              <div className="h-2 rounded-full bg-primary transition-all" style={{ width: `${barWidth}%` }} />
            </div>
          </div>
          {(variance !== 0 || baseline > 0 || latest > 0) ? (
            <p className="text-xs text-muted-foreground">
              {variance !== 0 ? `Variance ${variance.toFixed(1)}%` : "Variance n/a"}
              {baseline > 0 && latest > 0 ? ` | Baseline ${formatMoney(baseline)} -> Actual ${formatMoney(latest)}` : ""}
            </p>
          ) : null}
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">Details</summary>
            <pre className="mt-2 overflow-auto rounded bg-muted p-2">{JSON.stringify(alert.meta ?? {}, null, 2)}</pre>
          </details>
        </div>
        <div className="flex flex-col gap-2">
          {onOpen ? (
            <Button variant="ghost" size="sm" onClick={() => onOpen(alert.id)}>
              View
            </Button>
          ) : null}
          {onDismiss ? (
            <Button variant="outline" size="sm" onClick={() => onDismiss(alert.id)}>
              Dismiss
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
