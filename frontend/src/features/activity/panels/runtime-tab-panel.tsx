"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { EndpointSLO } from "@/types/domain";

export function RuntimeTabPanel({
  isOwner,
  windowSeconds,
  p95ThresholdMs,
  errorRateThresholdPct,
  endpoints,
}: {
  isOwner: boolean;
  windowSeconds: number;
  p95ThresholdMs: number;
  errorRateThresholdPct: number;
  endpoints: EndpointSLO[];
}) {
  if (!isOwner) return null;

  return (
    <section id="activity-runtime" className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Runtime SLOs</CardTitle>
          <CardDescription>
            Rolling endpoint p95 and 5xx error-rate window ({windowSeconds}s).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {endpoints.length === 0 ? (
            <p className="text-sm text-muted-foreground">No runtime samples yet for this window.</p>
          ) : (
            endpoints.map((row) => (
              <div key={row.endpoint} className="rounded-[22px] border border-border/70 bg-card/70 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-medium">{row.endpoint}</p>
                  <Badge variant={row.breach ? "destructive" : "success"}>{row.breach ? "breach" : "ok"}</Badge>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  requests {row.requests} | p95 {row.p95_ms}ms (threshold {p95ThresholdMs}ms) | 5xx{" "}
                  {row.error_rate_pct}% (threshold {errorRateThresholdPct}%)
                </p>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </section>
  );
}

