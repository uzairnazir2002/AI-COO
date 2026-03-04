import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Alert } from "@/types/domain";

function severityVariant(severity: Alert["severity"]) {
  if (severity === "HIGH") return "destructive" as const;
  if (severity === "MEDIUM") return "warning" as const;
  return "success" as const;
}

export function AlertCard({ alert, onDismiss }: { alert: Alert; onDismiss?: (id: string) => void }) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant={severityVariant(alert.severity)}>{alert.severity}</Badge>
            <Badge>{alert.kind}</Badge>
          </div>
          <h4 className="font-medium">{alert.title}</h4>
          <p className="text-sm text-muted-foreground">{alert.description}</p>
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">Details</summary>
            <pre className="mt-2 overflow-auto rounded bg-muted p-2">{JSON.stringify(alert.meta ?? {}, null, 2)}</pre>
          </details>
        </div>
        {onDismiss ? (
          <Button variant="outline" size="sm" onClick={() => onDismiss(alert.id)}>
            Dismiss
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
