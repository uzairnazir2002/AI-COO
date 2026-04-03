"use client";

import { Badge } from "@/components/ui/badge";

export function ProgressCard({
  title,
  description,
  done,
  action,
}: {
  title: string;
  description: string;
  done: boolean;
  action?: React.ReactNode;
}) {
  return (
    <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold">{title}</p>
        <Badge variant={done ? "success" : "secondary"}>{done ? "Completed" : "Pending"}</Badge>
      </div>
      <p className="mt-3 text-xs leading-5 text-muted-foreground">{description}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

