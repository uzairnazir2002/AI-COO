import { BulkActionBar } from "@/components/data-surface/bulk-action-bar";
import { Button } from "@/components/ui/button";

export function BulkSelectionBar({
  selectedCount,
  deleting,
  onDelete,
  onClear,
}: {
  selectedCount: number;
  deleting: boolean;
  onDelete: () => Promise<void>;
  onClear: () => void;
}) {
  return (
    <BulkActionBar
      testId="transactions-bulk-action-bar"
      visible={selectedCount > 0}
      summary={`${selectedCount} row(s) selected`}
      actions={
        <>
          <Button variant="outline" size="sm" disabled={deleting} onClick={() => void onDelete()}>
            Delete selected
          </Button>
          <Button variant="ghost" size="sm" onClick={onClear}>Clear</Button>
        </>
      }
    />
  );
}

