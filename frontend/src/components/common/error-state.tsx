"use client";

import { AlertTriangle, RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="glass-panel panel-edge rounded-[24px] p-6">
      <div className="flex items-start gap-4 rounded-[18px] border border-danger/20 bg-danger/5 p-4">
        <div className="rounded-full bg-danger/10 p-2 text-danger">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{description ?? "Refresh and try again."}</p>
        </div>
        {onRetry ? (
          <Button variant="outline" onClick={onRetry}>
            <RefreshCcw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        ) : null}
      </div>
    </div>
  );
}
