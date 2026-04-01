"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Panel, PanelBody } from "@/components/layout/panel";

export function HeroStrip({
  from,
  to,
  headline,
}: {
  from: string;
  to: string;
  headline?: string | null;
}) {
  return (
    <Panel className="overflow-hidden border-primary/15 bg-gradient-to-r from-primary/10 via-card/85 to-card/95">
      <PanelBody className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Business health today</p>
          <p className="mt-2 text-xl font-semibold md:text-2xl">
            {headline || "Live executive brief is ready."}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Last updated for {from} to {to}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/app/transactions?action=compose">Add transaction</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/app/reports?action=generate">Generate report</Link>
          </Button>
          <Button asChild>
            <Link href="/app/alerts">Review alerts</Link>
          </Button>
        </div>
      </PanelBody>
    </Panel>
  );
}
