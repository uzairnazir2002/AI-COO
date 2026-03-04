import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export type TxFilters = {
  from: string;
  to: string;
  type: string;
  category: string;
  q: string;
};

export function FiltersBar({
  filters,
  onChange,
}: {
  filters: TxFilters;
  onChange: (next: TxFilters) => void;
}) {
  return (
    <div className="grid gap-2 md:grid-cols-5">
      <Input type="date" value={filters.from} onChange={(e) => onChange({ ...filters, from: e.target.value })} />
      <Input type="date" value={filters.to} onChange={(e) => onChange({ ...filters, to: e.target.value })} />
      <Select value={filters.type || "__all__"} onValueChange={(value) => onChange({ ...filters, type: value === "__all__" ? "" : value })}>
        <SelectTrigger><SelectValue placeholder="All types" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All types</SelectItem>
          <SelectItem value="REVENUE">Revenue</SelectItem>
          <SelectItem value="EXPENSE">Expense</SelectItem>
        </SelectContent>
      </Select>
      <Input placeholder="Category" value={filters.category} onChange={(e) => onChange({ ...filters, category: e.target.value })} />
      <Input placeholder="Search vendor/notes" value={filters.q} onChange={(e) => onChange({ ...filters, q: e.target.value })} />
    </div>
  );
}
