"use client";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";

export function OperationsHealthCard({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Panel>
      <PanelHeader>
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-base font-semibold">{title}</h2>
        </div>
      </PanelHeader>
      <PanelBody className="space-y-2 text-sm">{children}</PanelBody>
    </Panel>
  );
}

