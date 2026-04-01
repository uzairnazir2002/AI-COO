"use client";

import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { TabNav } from "@/components/layout/tab-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InventoryDetailDrawer } from "@/features/inventory/panels/inventory-detail-drawer";
import { formatMoney } from "@/lib/utils/format";
import type { InventoryForecastItem, InventoryItem, InventoryPurchaseOrder } from "@/types/domain";

type ItemOption = { id: string; label: string };

function formatQty(value: string | null | undefined) {
  const n = Number(value || "0");
  if (Number.isNaN(n)) return value || "0";
  return n.toFixed(3);
}

export function InventoryWorkspaceContainer({
  activeTab,
  onTabChange,
  editable,
  itemSku,
  onItemSkuChange,
  itemName,
  onItemNameChange,
  itemUnitCost,
  onItemUnitCostChange,
  itemReorderPoint,
  onItemReorderPointChange,
  onCreateItem,
  createItemPending,
  items,
  eventItemId,
  onEventItemIdChange,
  eventType,
  onEventTypeChange,
  eventQty,
  onEventQtyChange,
  eventUnitCost,
  onEventUnitCostChange,
  eventRef,
  onEventRefChange,
  onCreateStockEvent,
  createStockEventPending,
  poItemId,
  onPoItemIdChange,
  poQty,
  onPoQtyChange,
  poExpectedDate,
  onPoExpectedDateChange,
  poUnitCost,
  onPoUnitCostChange,
  poRef,
  onPoRefChange,
  onCreatePurchaseOrder,
  createPurchaseOrderPending,
  itemOptions,
  forecastItems,
  recentPurchaseOrders,
}: {
  activeTab: string;
  onTabChange: (value: string) => void;
  editable: boolean;
  itemSku: string;
  onItemSkuChange: (value: string) => void;
  itemName: string;
  onItemNameChange: (value: string) => void;
  itemUnitCost: string;
  onItemUnitCostChange: (value: string) => void;
  itemReorderPoint: string;
  onItemReorderPointChange: (value: string) => void;
  onCreateItem: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  createItemPending: boolean;
  items: InventoryItem[];
  eventItemId: string;
  onEventItemIdChange: (value: string) => void;
  eventType: "INBOUND" | "OUTBOUND" | "ADJUSTMENT";
  onEventTypeChange: (value: "INBOUND" | "OUTBOUND" | "ADJUSTMENT") => void;
  eventQty: string;
  onEventQtyChange: (value: string) => void;
  eventUnitCost: string;
  onEventUnitCostChange: (value: string) => void;
  eventRef: string;
  onEventRefChange: (value: string) => void;
  onCreateStockEvent: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  createStockEventPending: boolean;
  poItemId: string;
  onPoItemIdChange: (value: string) => void;
  poQty: string;
  onPoQtyChange: (value: string) => void;
  poExpectedDate: string;
  onPoExpectedDateChange: (value: string) => void;
  poUnitCost: string;
  onPoUnitCostChange: (value: string) => void;
  poRef: string;
  onPoRefChange: (value: string) => void;
  onCreatePurchaseOrder: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  createPurchaseOrderPending: boolean;
  itemOptions: ItemOption[];
  forecastItems: InventoryForecastItem[];
  recentPurchaseOrders: InventoryPurchaseOrder[];
}) {
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [selectedForecastItemId, setSelectedForecastItemId] = useState<string | null>(null);
  const [selectedPurchaseOrderId, setSelectedPurchaseOrderId] = useState<string | null>(null);
  const selectedItem = useMemo(() => items.find((item) => item.id === selectedItemId) ?? null, [items, selectedItemId]);
  const selectedForecastItem = useMemo(
    () => forecastItems.find((item) => item.item_id === selectedForecastItemId) ?? null,
    [forecastItems, selectedForecastItemId],
  );
  const selectedPurchaseOrder = recentPurchaseOrders.find((po) => po.id === selectedPurchaseOrderId) ?? null;
  const drawerOpen = Boolean(selectedItem || selectedForecastItem || selectedPurchaseOrder);

  return (
    <>
      <TabNav
        active={activeTab}
        onChange={onTabChange}
        items={[
          { id: "items", label: "Items" },
          { id: "stock-events", label: "Stock Events" },
          { id: "purchase-orders", label: "Purchase Orders" },
          { id: "risk-forecast", label: "Risk Forecast" },
        ]}
      />

      {activeTab === "items" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Create item</h2>
            </PanelHeader>
            <PanelBody>
              {!editable ? (
                <p className="text-sm text-muted-foreground">Read-only for viewers.</p>
              ) : (
                <form className="grid gap-2 md:grid-cols-2" onSubmit={(event) => void onCreateItem(event)}>
                  <Input placeholder="SKU (e.g. SKU-1001)" value={itemSku} onChange={(e) => onItemSkuChange(e.target.value)} />
                  <Input placeholder="Item name" value={itemName} onChange={(e) => onItemNameChange(e.target.value)} />
                  <Input placeholder="Unit cost" inputMode="decimal" value={itemUnitCost} onChange={(e) => onItemUnitCostChange(e.target.value)} />
                  <Input
                    placeholder="Reorder point (qty)"
                    inputMode="decimal"
                    value={itemReorderPoint}
                    onChange={(e) => onItemReorderPointChange(e.target.value)}
                  />
                  <div className="md:col-span-2">
                    <Button type="submit" disabled={createItemPending}>Create item</Button>
                  </div>
                </form>
              )}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Inventory items</h2>
            </PanelHeader>
            <PanelBody>
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
                        <tr key={item.id} className="cursor-pointer border-t border-border/60 hover:bg-muted/40" onClick={() => setSelectedItemId(item.id)}>
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
            </PanelBody>
          </Panel>
        </section>
      ) : null}

      {activeTab === "stock-events" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Record stock event</h2>
            </PanelHeader>
            <PanelBody>
              {!editable ? (
                <p className="text-sm text-muted-foreground">Read-only for viewers.</p>
              ) : (
                <form className="grid gap-2 md:grid-cols-2" onSubmit={(event) => void onCreateStockEvent(event)}>
                  <select
                    aria-label="Stock event item"
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={eventItemId}
                    onChange={(e) => onEventItemIdChange(e.target.value)}
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
                    onChange={(e) => onEventTypeChange(e.target.value as "INBOUND" | "OUTBOUND" | "ADJUSTMENT")}
                  >
                    <option value="OUTBOUND">OUTBOUND</option>
                    <option value="INBOUND">INBOUND</option>
                    <option value="ADJUSTMENT">ADJUSTMENT</option>
                  </select>
                  <Input placeholder="Quantity" inputMode="decimal" value={eventQty} onChange={(e) => onEventQtyChange(e.target.value)} />
                  <Input
                    placeholder="Unit cost (optional)"
                    inputMode="decimal"
                    value={eventUnitCost}
                    onChange={(e) => onEventUnitCostChange(e.target.value)}
                  />
                  <Input placeholder="Reference (optional)" value={eventRef} onChange={(e) => onEventRefChange(e.target.value)} />
                  <div className="md:col-span-2">
                    <Button type="submit" disabled={createStockEventPending}>Record event</Button>
                  </div>
                </form>
              )}
            </PanelBody>
          </Panel>
        </section>
      ) : null}

      {activeTab === "purchase-orders" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Create purchase order</h2>
            </PanelHeader>
            <PanelBody>
              {!editable ? (
                <p className="text-sm text-muted-foreground">Read-only for viewers.</p>
              ) : (
                <form className="grid gap-2 md:grid-cols-2" onSubmit={(event) => void onCreatePurchaseOrder(event)}>
                  <select
                    aria-label="Purchase order item"
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={poItemId}
                    onChange={(e) => onPoItemIdChange(e.target.value)}
                  >
                    <option value="">Select item</option>
                    {itemOptions.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.label}
                      </option>
                    ))}
                  </select>
                  <Input placeholder="Quantity" inputMode="decimal" value={poQty} onChange={(e) => onPoQtyChange(e.target.value)} />
                  <Input type="date" value={poExpectedDate} onChange={(e) => onPoExpectedDateChange(e.target.value)} />
                  <Input placeholder="Unit cost (optional)" inputMode="decimal" value={poUnitCost} onChange={(e) => onPoUnitCostChange(e.target.value)} />
                  <Input placeholder="External ref (optional)" value={poRef} onChange={(e) => onPoRefChange(e.target.value)} />
                  <div className="md:col-span-2">
                    <Button type="submit" disabled={createPurchaseOrderPending}>Create purchase order</Button>
                  </div>
                </form>
              )}
              <div className="mt-4">
                {recentPurchaseOrders.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No recent purchase orders in this session.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-muted-foreground">
                          <th className="py-2">PO</th>
                          <th className="py-2">Item</th>
                          <th className="py-2">Qty</th>
                          <th className="py-2">Expected</th>
                          <th className="py-2">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recentPurchaseOrders.map((po) => (
                          <tr key={po.id} className="cursor-pointer border-t border-border/60 hover:bg-muted/40" onClick={() => setSelectedPurchaseOrderId(po.id)}>
                            <td className="py-2 font-medium">{po.id.slice(0, 8)}</td>
                            <td>{po.item_id}</td>
                            <td>{po.quantity}</td>
                            <td>{po.expected_date}</td>
                            <td>{po.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </PanelBody>
          </Panel>
        </section>
      ) : null}

      {activeTab === "risk-forecast" ? (
        <section className="space-y-4">
          <Panel>
            <PanelHeader>
              <h2 className="text-base font-semibold">Forecast risk view</h2>
            </PanelHeader>
            <PanelBody>
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
                        <tr key={row.item_id} className="cursor-pointer border-t border-border/60 hover:bg-muted/40" onClick={() => setSelectedForecastItemId(row.item_id)}>
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
            </PanelBody>
          </Panel>
        </section>
      ) : null}

      <InventoryDetailDrawer
        open={drawerOpen}
        onClose={() => {
          setSelectedItemId(null);
          setSelectedForecastItemId(null);
          setSelectedPurchaseOrderId(null);
        }}
        item={selectedItem}
        forecastItem={selectedForecastItem}
        purchaseOrder={selectedPurchaseOrder}
      />
    </>
  );
}
