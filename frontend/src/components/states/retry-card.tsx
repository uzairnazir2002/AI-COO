"use client";

import { RefreshCcw } from "lucide-react";

import { Panel, PanelBody } from "@/components/layout/panel";
import { Button } from "@/components/ui/button";

export function RetryCard({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <Panel>
      <PanelBody className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{message}</p>
        <Button variant="outline" onClick={onRetry}>
          <RefreshCcw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </PanelBody>
    </Panel>
  );
}

