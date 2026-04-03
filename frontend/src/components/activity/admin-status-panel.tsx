"use client";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";

export function AdminStatusPanel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Panel>
      <PanelHeader>
        <h2 className="text-base font-semibold">{title}</h2>
      </PanelHeader>
      <PanelBody className="space-y-2 text-sm text-muted-foreground">{children}</PanelBody>
    </Panel>
  );
}

