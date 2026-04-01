"use client";

import { FormEvent, useMemo, useState } from "react";

import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { StatusStrip } from "@/components/layout/status-strip";
import { InlineErrorBanner } from "@/components/states/inline-error-banner";
import { RetryCard } from "@/components/states/retry-card";
import { SkeletonPanel } from "@/components/states/skeleton-panel";
import { SuccessStateCard } from "@/components/states/success-state-card";
import { InventoryWorkspaceContainer } from "@/features/inventory/containers/inventory-workspace-container";
import {
  useCreateInventoryItem,
  useCreateInventoryPurchaseOrder,
  useCreateInventoryStockEvent,
  useInventoryForecast,
  useInventoryItems,
} from "@/features/inventory/hooks";
import { canEdit } from "@/lib/auth/rbac";
import { useAppStore } from "@/store/appStore";
import type { AlertRecalcMetadata } from "@/features/transactions/hooks";
import type { InventoryPurchaseOrder } from "@/types/domain";

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

  const [activeTab, setActiveTab] = useState("items");
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
  const [recentPurchaseOrders, setRecentPurchaseOrders] = useState<InventoryPurchaseOrder[]>([]);
  const [poExpectedDate, setPoExpectedDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 14);
    return d.toISOString().slice(0, 10);
  });
  const [poRef, setPoRef] = useState("");
  const [lastSuccess, setLastSuccess] = useState("");

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
      setLastSuccess("Item setup completed.");
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
      setLastSuccess("Inventory movement logged.");
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
      setRecentPurchaseOrders((prev) => [result.purchaseOrder, ...prev].slice(0, 20));
      setPoQty("");
      setPoUnitCost("");
      setPoRef("");
      setLastSuccess("Purchase order submitted.");
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

      <StatusStrip
        items={[
          { label: "Items", value: String(items.length), tone: "neutral" },
          { label: "High risk", value: String(highRiskItems), tone: highRiskItems > 0 ? "warning" : "live" },
          { label: "Horizon", value: `${forecastQuery.data?.horizon_days ?? 30}d`, tone: "neutral" },
        ]}
      />

      {itemsQuery.isLoading || forecastQuery.isLoading ? <SkeletonPanel rows={5} /> : null}

      {itemsQuery.error || forecastQuery.error ? (
        <div className="space-y-3">
          <InlineErrorBanner
            message={
              String(
                (itemsQuery.error as Error | undefined)?.message
                || (forecastQuery.error as Error | undefined)?.message
                || "Unable to load inventory data.",
              )
            }
          />
          <RetryCard
            message="Retry loading inventory list and risk forecast."
            onRetry={() => {
              void itemsQuery.refetch();
              void forecastQuery.refetch();
            }}
          />
        </div>
      ) : null}

      {lastSuccess ? (
        <SuccessStateCard title="Inventory workspace updated" description={lastSuccess} />
      ) : null}

      <InventoryWorkspaceContainer
        activeTab={activeTab}
        onTabChange={setActiveTab}
        editable={editable}
        itemSku={itemSku}
        onItemSkuChange={setItemSku}
        itemName={itemName}
        onItemNameChange={setItemName}
        itemUnitCost={itemUnitCost}
        onItemUnitCostChange={setItemUnitCost}
        itemReorderPoint={itemReorderPoint}
        onItemReorderPointChange={setItemReorderPoint}
        onCreateItem={onCreateItem}
        createItemPending={createItem.isPending}
        items={items}
        eventItemId={eventItemId}
        onEventItemIdChange={setEventItemId}
        eventType={eventType}
        onEventTypeChange={setEventType}
        eventQty={eventQty}
        onEventQtyChange={setEventQty}
        eventUnitCost={eventUnitCost}
        onEventUnitCostChange={setEventUnitCost}
        eventRef={eventRef}
        onEventRefChange={setEventRef}
        onCreateStockEvent={onCreateStockEvent}
        createStockEventPending={createStockEvent.isPending}
        poItemId={poItemId}
        onPoItemIdChange={setPoItemId}
        poQty={poQty}
        onPoQtyChange={setPoQty}
        poExpectedDate={poExpectedDate}
        onPoExpectedDateChange={setPoExpectedDate}
        poUnitCost={poUnitCost}
        onPoUnitCostChange={setPoUnitCost}
        poRef={poRef}
        onPoRefChange={setPoRef}
        onCreatePurchaseOrder={onCreatePurchaseOrder}
        createPurchaseOrderPending={createPurchaseOrder.isPending}
        itemOptions={itemOptions}
        forecastItems={forecastItems}
        recentPurchaseOrders={recentPurchaseOrders}
      />
    </div>
  );
}

