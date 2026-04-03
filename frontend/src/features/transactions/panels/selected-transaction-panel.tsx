import { Pencil } from "lucide-react";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { Button } from "@/components/ui/button";
import { formatDate, formatMoney } from "@/lib/utils/format";
import type { Transaction } from "@/types/domain";

export function SelectedTransactionPanel({
  transaction,
  editable,
  onEdit,
  inDrawer = false,
}: {
  transaction: Transaction | null;
  editable: boolean;
  onEdit: (tx: Transaction) => void;
  inDrawer?: boolean;
}) {
  const content = !transaction ? (
    <p className="text-sm text-muted-foreground">Select a row to open the transaction detail panel.</p>
  ) : (
    <div className="space-y-3 text-sm">
      <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
        <p className="font-medium">{transaction.category}</p>
        <p className="mt-1 text-xs text-muted-foreground">{formatDate(transaction.date)} · {transaction.type}</p>
        <p className="mt-3 text-xl font-semibold">{formatMoney(transaction.amount)}</p>
        <div className="mt-3 space-y-1 text-xs text-muted-foreground">
          <p>Vendor: {transaction.vendor || "-"}</p>
          <p>Notes: {transaction.notes || "-"}</p>
          <p>Location: {transaction.location_id || "org default"}</p>
        </div>
        {editable ? (
          <Button className="mt-3" size="sm" variant="outline" onClick={() => onEdit(transaction)}>
            <Pencil className="mr-2 h-4 w-4" />
            Quick edit
          </Button>
        ) : null}
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Related alerts</p>
        <p className="mt-2 text-xs text-muted-foreground">
          No direct alert links are attached to this row yet. Use the category/type context in the Alerts workspace for investigation.
        </p>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Audit snippet</p>
        <div className="mt-2 space-y-1 text-xs text-muted-foreground">
          <p>Transaction ID: {transaction.id}</p>
          <p>Effective date: {formatDate(transaction.date)}</p>
          <p>Org scope: {transaction.org_id}</p>
        </div>
      </div>
    </div>
  );

  if (inDrawer) {
    return <div className="space-y-3">{content}</div>;
  }

  return (
    <Panel>
      <PanelHeader><h2 className="text-base font-semibold">Selected transaction</h2></PanelHeader>
      <PanelBody className="space-y-3">{content}</PanelBody>
    </Panel>
  );
}

