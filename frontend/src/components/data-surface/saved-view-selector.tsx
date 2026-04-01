"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type SavedViewOption = {
  id: string;
  name: string;
};

export function SavedViewSelector({
  views,
  selectedId,
  onSelect,
  onSave,
  onDelete,
}: {
  views: SavedViewOption[];
  selectedId: string;
  onSelect: (id: string) => void;
  onSave: (name: string, existingId?: string) => void;
  onDelete: (id: string) => void;
}) {
  const [draftName, setDraftName] = useState("");

  useEffect(() => {
    const current = views.find((view) => view.id === selectedId);
    setDraftName(current?.name ?? "");
  }, [selectedId, views]);

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="saved-view-selector">
      <Select value={selectedId || "__none__"} onValueChange={(value) => onSelect(value === "__none__" ? "" : value)}>
        <SelectTrigger className="h-8 w-[170px]">
          <SelectValue placeholder="Saved views" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__none__">No saved view</SelectItem>
          {views.map((view) => (
            <SelectItem key={view.id} value={view.id}>
              {view.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Input
        className="h-8 w-[180px]"
        placeholder="View name"
        value={draftName}
        onChange={(event) => setDraftName(event.target.value)}
      />
      <Button
        size="sm"
        variant="outline"
        disabled={draftName.trim().length === 0}
        onClick={() => onSave(draftName.trim(), selectedId || undefined)}
      >
        {selectedId ? "Update view" : "Save view"}
      </Button>
      {selectedId ? (
        <Button size="sm" variant="ghost" onClick={() => onDelete(selectedId)}>
          Delete view
        </Button>
      ) : null}
    </div>
  );
}
