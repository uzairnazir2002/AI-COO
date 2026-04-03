"use client";

import { useState } from "react";

import type { TxFilters } from "@/components/common/filters-bar";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";

export function AdvancedFiltersPanel({
  filters,
  onChange,
}: {
  filters: TxFilters;
  onChange: (next: TxFilters) => void;
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div className="space-y-3">
      <div className="grid gap-2 md:grid-cols-4">
        <Input
          placeholder="Search vendor/notes"
          value={filters.q}
          onChange={(e) => onChange({ ...filters, q: e.target.value })}
        />
        <Select
          value={filters.type || "__all__"}
          onValueChange={(value) => onChange({ ...filters, type: value === "__all__" ? "" : value })}
        >
          <SelectTrigger>
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All types</SelectItem>
            <SelectItem value="REVENUE">Revenue</SelectItem>
            <SelectItem value="EXPENSE">Expense</SelectItem>
          </SelectContent>
        </Select>
        <Input type="date" value={filters.from} onChange={(e) => onChange({ ...filters, from: e.target.value })} />
        <Input type="date" value={filters.to} onChange={(e) => onChange({ ...filters, to: e.target.value })} />
      </div>

      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          data-testid="transactions-more-filters-toggle"
          onClick={() => setShowAdvanced((value) => !value)}
        >
          {showAdvanced ? "Hide filters" : "More filters"}
        </Button>
      </div>

      {showAdvanced ? (
        <div className="grid gap-2 md:grid-cols-2">
          <Input
            placeholder="Category"
            value={filters.category}
            onChange={(e) => onChange({ ...filters, category: e.target.value })}
          />
        </div>
      ) : null}
    </div>
  );
}

