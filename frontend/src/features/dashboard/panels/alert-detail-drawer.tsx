"use client";

import { DetailDrawer } from "@/components/drawers/detail-drawer";
import type { Alert } from "@/types/domain";

export function AlertDetailDrawer({
  alert,
  onClose,
}: {
  alert: Alert | null;
  onClose: () => void;
}) {
  return (
    <DetailDrawer open={Boolean(alert)} title="Alert detail" onClose={onClose}>
      {alert ? (
        <div className="rounded-[24px] border border-border/70 bg-card/75 p-5">
          <h3 className="text-xl font-semibold">{alert.title}</h3>
          <p className="mt-3 text-sm text-muted-foreground">{alert.description}</p>
          <pre className="mt-4 overflow-auto rounded-2xl bg-muted p-4 text-xs">{JSON.stringify(alert.meta ?? {}, null, 2)}</pre>
        </div>
      ) : null}
    </DetailDrawer>
  );
}

