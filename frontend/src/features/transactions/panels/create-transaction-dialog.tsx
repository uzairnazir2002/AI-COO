import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type NewTransactionDraft = {
  date: string;
  amount: string;
  type: string;
  category: string;
  vendor: string;
  notes: string;
};

export function CreateTransactionDialog({
  open,
  onOpenChange,
  draft,
  onDraftChange,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  draft: NewTransactionDraft;
  onDraftChange: (next: NewTransactionDraft) => void;
  onSubmit: () => Promise<void>;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Add transaction
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add transaction</DialogTitle>
          <DialogDescription>Fast keyboard-friendly manual entry.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-3 md:grid-cols-2"
          onSubmit={async (e) => {
            e.preventDefault();
            await onSubmit();
          }}
        >
          <Input type="date" value={draft.date} onChange={(e) => onDraftChange({ ...draft, date: e.target.value })} required />
          <Input
            placeholder="Amount"
            inputMode="decimal"
            value={draft.amount}
            onChange={(e) => onDraftChange({ ...draft, amount: e.target.value })}
            required
          />
          <Select value={draft.type} onValueChange={(value) => onDraftChange({ ...draft, type: value })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="REVENUE">Revenue</SelectItem>
              <SelectItem value="EXPENSE">Expense</SelectItem>
            </SelectContent>
          </Select>
          <Input placeholder="Category" value={draft.category} onChange={(e) => onDraftChange({ ...draft, category: e.target.value })} required />
          <Input placeholder="Vendor" value={draft.vendor} onChange={(e) => onDraftChange({ ...draft, vendor: e.target.value })} />
          <Input placeholder="Notes" value={draft.notes} onChange={(e) => onDraftChange({ ...draft, notes: e.target.value })} />
          <div className="flex justify-end gap-2 md:col-span-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit">Add</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

