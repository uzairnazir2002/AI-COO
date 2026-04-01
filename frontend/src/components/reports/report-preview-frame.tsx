"use client";

import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/common/empty-state";

export function ReportPreviewFrame({
  previewUrl,
}: {
  previewUrl: string | null;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Report preview</h2>
        {previewUrl ? <Badge variant="success">ready</Badge> : <Badge variant="secondary">empty</Badge>}
      </div>
      {previewUrl ? (
        <div className="h-[640px] overflow-hidden rounded-2xl border border-border">
          <iframe title="Report preview" src={previewUrl} className="h-full w-full" />
        </div>
      ) : (
        <EmptyState
          eyebrow="Preview"
          title="No report selected"
          description="Generate or download a report to open a preview canvas."
        />
      )}
    </div>
  );
}

