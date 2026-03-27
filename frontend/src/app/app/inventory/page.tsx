"use client";

import { FormEvent, useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  useCreateInventoryItem,
  useCreateInventoryPurchaseOrder,
  useCreateInventoryStockEvent,
  useInventoryForecast,
  useInventoryItems,
} from "@/features/inventory/hooks";
import { canEdit } from "@/lib/auth/rbac";
import { formatMoney } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";
import type { AlertRecalcMetadata } from "@/features/transactions/hooks";

function formatQty(value: string | null | undefined) {
  const n = Number(value || "0");
  if (Number.isNaN(n)) return value || "0";
  return n.toFixed(3);
}

function describeAlertRefresh(meta?: AlertRecalcMetadata | null) {
  if (!meta) return "Alert refresh queued.";
  return meta.queued
    ? `Alert refresh queued (job ${meta.taskId}).`
    : `Alert refresh already pending (job ${meta.taskId}).`;
}

export default function InventoryPage() {
  const selectedOrg = useAppStore((s) => s.orgs.find((org) => org.org_id === s.selectedOrgId));
  const role = selectedOrg?.role;
  const editable = canEdit(role);
  const toast = useToast();

  const itemsQuery = useInventoryItems(false);
  const forecastQuery = useInventoryForecast(30, 30);
  const createItem = useCreateInventoryItem();
  const createStockEvent = useCreateInventoryStockEvent();
  const createPurchaseOrder = useCreateInventoryPurchaseOrder();

  const [itemSku, setItemSku] = useState("");
  const [itemName, setItemName] = useState("");
  const [itemUnitCost, setItemUnitCost] = useState("0");
  const [itemReorderPoint, setItemReorderPoint] = useState("0");

  const [eventItemId, setEventItemId] = useState("");
  const [eventType, setEventType] = useState<"INBOUND" | "OUTBOUND" | "ADJUSTMENT">("OUTBOUND");
  const [eventQty, setEventQty] = useState("");
  const [eventUnitCost, setEventUnitCost] = useState("");
  const [eventRef, setEventRef] = useState("");

  const [poItemId, setPoItemId] = useState("");
  const [poQty, setPoQty] = useState("");
  const [poUnitCost, setPoUnitCost] = useState("");
  const [poExpectedDate, setPoExpectedDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 14);
    return d.toISOString().slice(0, 10);
  });
  const [poRef, setPoRef] = useState("");

  const items = useMemo(() => itemsQuery.data ?? [], [itemsQuery.data]);
  const forecastItems = forecastQuery.data?.items ?? [];
  const highRiskItems = forecastQuery.data?.high_risk_items ?? 0;

  const itemOptions = useMemo(
    () => items.map((item) => ({ id: item.id, label: `${item.sku} - ${item.name}` })),
    [items],
  );

  async function onCreateItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!itemSku.trim() || !itemName.trim()) {
      toast.toast({ title: "SKU and item name are required", variant: "danger" });
      return;
    }
    try {
      const result = await createItem.mutateAsync({
        sku: itemSku.trim(),
        name: itemName.trim(),
        unit_cost: String(Number(itemUnitCost || "0")),
        reorder_point: String(Number(itemReorderPoint || "0")),
      });
      setItemSku("");
      setItemName("");
      setItemUnitCost("0");
      setItemReorderPoint("0");
      setEventItemId((prev) => prev || result.item.id);
      setPoItemId((prev) => prev || result.item.id);
      toast.toast({ title: "Inventory item created", description: describeAlertRefresh(result.alertRecalc), variant: "success" });
    } catch (err) {
      toast.toast({ title: err instanceof Error ? err.message : "Failed to create item", variant: "danger" });
    }
  }

  async function onCreateStockEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!eventItemId || !eventQty.trim()) {
      toast.toast({ title: "Item and quantity are required", variant: "danger" });
      return;
    }
    try {
      const result = await createStockEvent.mutateAsync({
        item_id: eventItemId,
        event_type: eventType,
        quantity: String(Number(eventQty)),
        unit_cost: eventUnitCost.trim() ? String(Number(eventUnitCost)) : undefined,
        reference: eventRef.trim() || undefined,
      });
      setEventQty("");
      setEventUnitCost("");
      setEventRef("");
      toast.toast({ title: "Stock event recorded", description: describeAlertRefresh(result.alertRecalc), variant: "success" });
    } catch (err) {
      toast.toast({ title: err instanceof Error ? err.message : "Failed to record stock event", variant: "danger" });
    }
  }

  async function onCreatePurchaseOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!poItemId || !poQty.trim() || !poExpectedDate) {
      toast.toast({ title: "Item, quantity, and expected date are required", variant: "danger" });
      return;
    }
    try {
      const result = await createPurchaseOrder.mutateAsync({
        item_id: poItemId,
        quantity: String(Number(poQty)),
        expected_date: poExpectedDate,
        unit_cost: poUnitCost.trim() ? String(Number(poUnitCost)) : undefined,
        external_ref: poRef.trim() || undefined,
      });
      setPoQty("");
      setPoUnitCost("");
      setPoRef("");
      toast.toast({
        title: "Purchase order created",
        description: describeAlertRefresh(result.alertRecalc),
        variant: "success",
      });
    } catch (err) {
      toast.toast({ title: err instanceof Error ? err.message : "Failed to create purchase order", variant: "danger" });
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Inventory"
        description="Track stock movement, inbound supply, and projected stockout risk."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Tracked items</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{items.length}</p>
            <p className="text-xs text-muted-foreground">Active item records in current org/location scope.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>High stockout risk</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold text-amber-600">{highRiskItems}</p>
            <p className="text-xs text-muted-foreground">Items currently flagged high by forecast model.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Forecast horizon</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{forecastQuery.data?.horizon_days ?? 30}d</p>
            <p className="text-xs text-muted-foreground">Velocity based on {forecastQuery.data?.lookback_days ?? 30}-day lookback.</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Create item</CardTitle>
          </CardHeader>
          <CardContent>
            {!editable ? (
              <p className="text-sm text-muted-foreground">Read-only for viewers.</p>
            ) : (
              <form className="space-y-2" onSubmit={onCreateItem}>
                <Input placeholder="SKU (e.g. SKU-1001)" value={itemSku} onChange={(e) => setItemSku(e.target.value)} />
                <Input placeholder="Item name" value={itemName} onChange={(e) => setItemName(e.target.value)} />
                <Input placeholder="Unit cost" inputMode="decimal" value={itemUnitCost} onChange={(e) => setItemUnitCost(e.target.value)} />
                <Input
                  placeholder="Reorder point (qty)"
                  inputMode="decimal"
                  value={itemReorderPoint}
                  onChange={(e) => setItemReorderPoint(e.target.value)}
                />
                <Button type="submit" disabled={createItem.isPending}>Create item</Button>
              </form>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Record stock event</CardTitle>
          </CardHeader>
          <CardContent>
            {!editable ? (
              <p className="text-sm text-muted-foreground">Read-only for viewers.</p>
            ) : (
              <form className="space-y-2" onSubmit={onCreateStockEvent}>
                <select
                  aria-label="Stock event item"
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={eventItemId}
                  onChange={(e) => setEventItemId(e.target.value)}
                >
                  <option value="">Select item</option>
                  {itemOptions.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.label}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Stock event type"
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={eventType}
                  onChange={(e) => setEventType(e.target.value as "INBOUND" | "OUTBOUND" | "ADJUSTMENT")}
                >
                  <option value="OUTBOUND">OUTBOUND</option>
                  <option value="INBOUND">INBOUND</option>
                  <option value="ADJUSTMENT">ADJUSTMENT</option>
                </select>
                <Input placeholder="Quantity" inputMode="decimal" value={eventQty} onChange={(e) => setEventQty(e.target.value)} />
                <Input
                  placeholder="Unit cost (optional)"
                  inputMode="decimal"
                  value={eventUnitCost}
                  onChange={(e) => setEventUnitCost(e.target.value)}
                />
                <Input placeholder="Reference (optional)" value={eventRef} onChange={(e) => setEventRef(e.target.value)} />
                <Button type="submit" disabled={createStockEvent.isPending}>Record event</Button>
              </form>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Create purchase order</CardTitle>
          </CardHeader>
          <CardContent>
            {!editable ? (
              <p className="text-sm text-muted-foreground">Read-only for viewers.</p>
            ) : (
              <form className="space-y-2" onSubmit={onCreatePurchaseOrder}>
                <select
                  aria-label="Purchase order item"
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={poItemId}
                  onChange={(e) => setPoItemId(e.target.value)}
                >
                  <option value="">Select item</option>
                  {itemOptions.map((row) => (
                    <option key={row.id} value={row.id}>
                      {row.label}
                    </option>
                  ))}
                </select>
                <Input placeholder="Quantity" inputMode="decimal" value={poQty} onChange={(e) => setPoQty(e.target.value)} />
                <Input type="date" value={poExpectedDate} onChange={(e) => setPoExpectedDate(e.target.value)} />
                <Input placeholder="Unit cost (optional)" inputMode="decimal" value={poUnitCost} onChange={(e) => setPoUnitCost(e.target.value)} />
                <Input placeholder="External ref (optional)" value={poRef} onChange={(e) => setPoRef(e.target.value)} />
                <Button type="submit" disabled={createPurchaseOrder.isPending}>Create purchase order</Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Inventory items</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <EmptyState
              eyebrow="No items yet"
              title="Create your first inventory item."
              description="Inventory forecasting starts once stock events are recorded."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="py-2">SKU</th>
                    <th className="py-2">Name</th>
                    <th className="py-2">Unit cost</th>
                    <th className="py-2">Reorder point</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-t border-border/60">
                      <td className="py-3 font-medium">{item.sku}</td>
                      <td>{item.name}</td>
                      <td>{formatMoney(item.unit_cost)}</td>
                      <td>{formatQty(item.reorder_point)}</td>
                      <td>
                        <Badge variant={item.is_active ? "secondary" : "outline"}>
                          {item.is_active ? "ACTIVE" : "INACTIVE"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Forecast risk view</CardTitle>
        </CardHeader>
        <CardContent>
          {forecastItems.length === 0 ? (
            <p className="text-sm text-muted-foreground">No inventory forecast rows yet. Record stock events first.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="py-2">SKU</th>
                    <th className="py-2">On hand</th>
                    <th className="py-2">Inbound</th>
                    <th className="py-2">Units/day</th>
                    <th className="py-2">Days cover</th>
                    <th className="py-2">Stockout date</th>
                    <th className="py-2">Risk</th>
                    <th className="py-2">COGS 30d</th>
                  </tr>
                </thead>
                <tbody>
                  {forecastItems.map((row) => (
                    <tr key={row.item_id} className="border-t border-border/60">
                      <td className="py-3 font-medium">{row.sku}</td>
                      <td>{formatQty(row.on_hand_qty)}</td>
                      <td>{formatQty(row.inbound_open_qty)}</td>
                      <td>{formatQty(row.units_per_day)}</td>
                      <td>{row.days_of_cover ?? "-"}</td>
                      <td>{row.projected_stockout_date ?? "-"}</td>
                      <td>
                        <Badge variant={row.risk_level === "HIGH" ? "destructive" : row.risk_level === "MEDIUM" ? "warning" : "outline"}>
                          {row.risk_level}
                        </Badge>
                      </td>
                      <td>{formatMoney(row.cogs_exposure_30d)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
