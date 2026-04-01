"use client";

import { CheckCircle2 } from "lucide-react";

import { Panel, PanelBody } from "@/components/layout/panel";
import { cn } from "@/lib/utils/cn";

export function SuccessStateCard({
  title,
  description,
  className,
}: {
  title: string;
  description: string;
  className?: string;
}) {
  return (
    <Panel className={cn("border-success/30 bg-success/5", className)}>
      <PanelBody className="flex items-start gap-3">
        <CheckCircle2 className="mt-0.5 h-5 w-5 text-success" />
        <div>
          <p className="text-sm font-semibold">{title}</p>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        </div>
      </PanelBody>
    </Panel>
  );
}

