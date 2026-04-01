"use client";

import { DetailDrawer } from "@/components/drawers/detail-drawer";
import { Badge } from "@/components/ui/badge";
import { formatMoney } from "@/lib/utils/format";
import type { InventoryForecastItem, InventoryItem, InventoryPurchaseOrder } from "@/types/domain";

export function InventoryDetailDrawer({
  open,
  onClose,
  item,
  forecastItem,
  purchaseOrder,
}: {
  open: boolean;
  onClose: () => void;
  item: InventoryItem | null;
  forecastItem: InventoryForecastItem | null;
  purchaseOrder: InventoryPurchaseOrder | null;
}) {
  return (
    <DetailDrawer open={open} onClose={onClose} title="Inventory detail">
      <div className="space-y-3 text-sm">
        {item ? (
          <div className="rounded-xl border border-border/70 bg-card/70 p-3">
            <p className="font-medium">{item.sku} · {item.name}</p>
            <p className="mt-1 text-xs text-muted-foreground">Unit cost {formatMoney(item.unit_cost)} · Reorder {item.reorder_point}</p>
          </div>
        ) : null}

        {purchaseOrder ? (
          <div className="rounded-xl border border-border/70 bg-card/70 p-3">
            <p className="font-medium">Purchase order {purchaseOrder.id}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Qty {purchaseOrder.quantity} · Expected {purchaseOrder.expected_date} · Status {purchaseOrder.status}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Unit cost: {purchaseOrder.unit_cost ? formatMoney(purchaseOrder.unit_cost) : "-"}</p>
          </div>
        ) : null}

        {forecastItem ? (
          <div className="rounded-xl border border-border/70 bg-card/70 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="font-medium">Forecast risk ({forecastItem.sku})</p>
              <Badge variant={forecastItem.risk_level === "HIGH" ? "destructive" : forecastItem.risk_level === "MEDIUM" ? "warning" : "outline"}>
                {forecastItem.risk_level}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">Projected stockout: {forecastItem.projected_stockout_date || "N/A"}</p>
            <p className="mt-1 text-xs text-muted-foreground">COGS exposure (30d): {formatMoney(forecastItem.cogs_exposure_30d)}</p>
          </div>
        ) : null}

        <div className="rounded-xl border border-border/70 bg-card/70 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Related alert context</p>
          <p className="mt-1 text-xs text-muted-foreground">
            High risk forecast rows contribute to stockout and margin-pressure alert workflows in the Alerts workspace.
          </p>
        </div>
      </div>
    </DetailDrawer>
  );
}
