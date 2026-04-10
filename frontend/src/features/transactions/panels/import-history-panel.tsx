import { Download } from "lucide-react";

import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { Button } from "@/components/ui/button";
import type { ImportHistoryItem } from "@/types/domain";

export function ImportHistoryPanel({
  items,
  onDownloadErrors,
}: {
  items: ImportHistoryItem[];
  onDownloadErrors: (id: string) => Promise<void>;
}) {
  return (
    <Panel>
      <PanelHeader><h2 className="text-base font-semibold">Import history</h2></PanelHeader>
      <PanelBody className="space-y-3">
        {items.length ? (
          items.map((item) => (
            <div key={item.id} className="rounded-[20px] border border-border/70 bg-card/70 p-4 text-sm">
              <p className="font-medium">{item.file_name || item.id}</p>
              <p className="mt-2 text-xs text-muted-foreground">
                {item.status} | rows {item.total_rows} | inserted {item.inserted_count} | duplicates {item.duplicate_count} | errors {item.error_count}
                {item.mapping_profile_id ? ` | profile ${item.mapping_profile_id.slice(0, 8)}` : ""}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button
                  variant="ghost"
                  className="px-0"
                  disabled={item.error_count === 0}
                  onClick={() => void onDownloadErrors(item.id)}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download errors
                </Button>
                {item.error_count === 0 ? (
                  <span className="text-xs text-muted-foreground">No row errors recorded.</span>
                ) : null}
              </div>
            </div>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">No imports yet.</p>
        )}
      </PanelBody>
    </Panel>
  );
}

