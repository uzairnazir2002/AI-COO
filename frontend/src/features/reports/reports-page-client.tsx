"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/common/use-toast";
import { fetchReportDownload, useGenerateReport, useReports } from "@/features/reports/hooks";
import { formatDate, weekStartISO } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";

export function ReportsPageClient() {
  const orgId = useAppStore((s) => s.selectedOrgId);
  const reports = useReports();
  const generate = useGenerateReport();
  const toast = useToast();
  const [weekStart, setWeekStart] = useState(weekStartISO());

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Reports</h1>

      <Card>
        <CardHeader><CardTitle>Generate weekly report</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Input type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} className="w-56" />
          <Button
            disabled={generate.isPending}
            onClick={async () => {
              await generate.mutateAsync(weekStart);
              toast.toast({ title: "Report generation requested" });
            }}
          >
            Generate / Regenerate
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Generated reports</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            {(reports.data?.items ?? []).map((report) => (
              <div key={report.id} className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <p className="font-medium">{formatDate(report.week_start)} - {formatDate(report.week_end)}</p>
                  <p className="text-xs text-muted-foreground">Created {formatDate(report.created_at)}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    if (!orgId) return;
                    const dl = await fetchReportDownload(report.id, orgId);
                    if (dl.url) {
                      window.open(dl.url, "_blank", "noopener,noreferrer");
                    } else {
                      toast.toast({ title: "Download response did not include URL", variant: "danger" });
                    }
                  }}
                >
                  Download
                </Button>
              </div>
            ))}
            {(reports.data?.items.length ?? 0) === 0 ? <p className="text-sm text-muted-foreground">No reports yet.</p> : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
