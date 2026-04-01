import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Transaction } from "@/types/domain";

export function EditTransactionDialog({
  transaction,
  onClose,
  onSave,
}: {
  transaction: Transaction | null;
  onClose: () => void;
  onSave: (payload: { date: string; amount: string; category: string; vendor: string; notes: string }) => Promise<void>;
}) {
  return (
    <Dialog open={Boolean(transaction)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit transaction</DialogTitle>
          <DialogDescription>Update a single row without leaving the ledger.</DialogDescription>
        </DialogHeader>
        {transaction ? (
          <form
            className="grid gap-3 md:grid-cols-2"
            onSubmit={async (event) => {
              event.preventDefault();
              const formData = new FormData(event.currentTarget);
              await onSave({
                date: String(formData.get("date")),
                amount: String(formData.get("amount")),
                category: String(formData.get("category")),
                vendor: String(formData.get("vendor") || ""),
                notes: String(formData.get("notes") || ""),
              });
            }}
          >
            <Input name="date" type="date" defaultValue={transaction.date} />
            <Input name="amount" defaultValue={transaction.amount} />
            <Input name="category" defaultValue={transaction.category} />
            <Input name="vendor" defaultValue={transaction.vendor || ""} />
            <Input name="notes" defaultValue={transaction.notes || ""} className="md:col-span-2" />
            <div className="flex justify-end gap-2 md:col-span-2">
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit">Save</Button>
            </div>
          </form>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

