import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type BulkRemapState = {
  from_category: string;
  to_category: string;
  from_date: string;
  to_date: string;
};

export function BulkRemapWorkspacePanel({
  selectedCount,
  deletePending,
  remapPending,
  state,
  onStateChange,
  onDeleteSelected,
  onClearSelection,
  onRemap,
}: {
  selectedCount: number;
  deletePending: boolean;
  remapPending: boolean;
  state: BulkRemapState;
  onStateChange: (next: BulkRemapState) => void;
  onDeleteSelected: () => Promise<void>;
  onClearSelection: () => void;
  onRemap: () => Promise<void>;
}) {
  return (
    <Panel>
      <PanelHeader><h2 className="text-base font-semibold">Bulk category remap</h2></PanelHeader>
      <PanelBody className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm text-muted-foreground">Selected rows: {selectedCount}</p>
          <Button
            variant="outline"
            disabled={selectedCount === 0 || deletePending}
            onClick={() => void onDeleteSelected()}
          >
            Delete selected
          </Button>
          <Button variant="ghost" disabled={selectedCount === 0} onClick={onClearSelection}>Clear selection</Button>
        </div>

        <div className="grid gap-2 md:grid-cols-5">
          <Input
            placeholder="From category"
            data-testid="bulk-remap-from-category"
            value={state.from_category}
            onChange={(e) => onStateChange({ ...state, from_category: e.target.value })}
          />
          <Input
            placeholder="To category"
            data-testid="bulk-remap-to-category"
            value={state.to_category}
            onChange={(e) => onStateChange({ ...state, to_category: e.target.value })}
          />
          <Input
            type="date"
            value={state.from_date}
            onChange={(e) => onStateChange({ ...state, from_date: e.target.value })}
          />
          <Input
            type="date"
            value={state.to_date}
            onChange={(e) => onStateChange({ ...state, to_date: e.target.value })}
          />
          <Button
            data-testid="bulk-remap-submit"
            disabled={!state.from_category || !state.to_category || remapPending}
            onClick={() => void onRemap()}
          >
            Remap category
          </Button>
        </div>
      </PanelBody>
    </Panel>
  );
}

