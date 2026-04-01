"use client";

import { useState } from "react";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type RowActionItem = {
  id: string;
  label: string;
  disabled?: boolean;
  onSelect: () => void;
};

export function RowActionMenu({
  actions,
  triggerLabel = "Actions",
  triggerAriaLabel,
}: {
  actions: RowActionItem[];
  triggerLabel?: string;
  triggerAriaLabel?: string;
}) {
  const [value, setValue] = useState("__none__");

  return (
    <div onClick={(event) => event.stopPropagation()} onMouseDown={(event) => event.stopPropagation()}>
      <Select
        value={value}
        onValueChange={(next) => {
          setValue("__none__");
          const action = actions.find((item) => item.id === next);
          if (!action || action.disabled) return;
          action.onSelect();
        }}
      >
        <SelectTrigger className="h-8 min-w-24" aria-label={triggerAriaLabel || triggerLabel}>
          <SelectValue placeholder={triggerLabel} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__none__" disabled>
            {triggerLabel}
          </SelectItem>
          {actions.map((action) => (
            <SelectItem key={action.id} value={action.id} disabled={action.disabled}>
              {action.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
