"use client";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";

export function AlertDetailCard({
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
      <PanelBody>{children}</PanelBody>
    </Panel>
  );
}

