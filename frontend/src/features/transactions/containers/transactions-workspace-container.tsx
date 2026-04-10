"use client";

import { useRef, useState } from "react";
import { flexRender, getCoreRowModel, useReactTable, type ColumnDef, type VisibilityState } from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";

import { EmptyState } from "@/components/common/empty-state";
import { AdvancedFiltersPanel } from "@/components/data-surface/advanced-filters-panel";
import { ColumnVisibilityMenu } from "@/components/data-surface/column-visibility-menu";
import { SavedViewSelector } from "@/components/data-surface/saved-view-selector";
import { type TxFilters } from "@/components/common/filters-bar";
import { SimpleDataTable } from "@/components/data-surface/simple-data-table";
import { TableToolbar } from "@/components/data-surface/table-toolbar";
import { VirtualizedGrid } from "@/components/data-surface/virtualized-grid";
import { DetailDrawer } from "@/components/drawers/detail-drawer";
import { Panel, PanelBody, PanelHeader } from "@/components/layout/panel";
import { MutationProgressToast } from "@/components/states/mutation-progress-toast";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ImportHistoryItem, Transaction } from "@/types/domain";
import { BulkRemapWorkspacePanel } from "@/features/transactions/panels/bulk-remap-workspace-panel";
import { BulkSelectionBar } from "@/features/transactions/panels/bulk-selection-bar";
import { CategoryBreakdownPanel } from "@/features/transactions/panels/category-breakdown-panel";
import { ImportHistoryPanel } from "@/features/transactions/panels/import-history-panel";
import { SelectedTransactionPanel } from "@/features/transactions/panels/selected-transaction-panel";

type BulkRemapState = {
  from_category: string;
  to_category: string;
  from_date: string;
  to_date: string;
};

type CategoryBreakdownRow = {
  category: string;
  value: number;
};

type SavedViewOption = {
  id: string;
  name: string;
};

export function TransactionsWorkspaceContainer({
  editable,
  filters,
  onFiltersChange,
  savedViews,
  activeSavedViewId,
  onSelectSavedView,
  onSaveSavedView,
  onDeleteSavedView,
  selectedCount,
  deletePending,
  remapPending,
  bulkRemapState,
  onBulkRemapStateChange,
  onDeleteSelected,
  onClearSelection,
  onRemap,
  total,
  isFetching,
  csvBusy,
  page,
  pageSize,
  onPrevPage,
  onNextPage,
  data,
  columns,
  onRowSelect,
  onAddTransaction,
  activeTransaction,
  onEditTransaction,
  categoryBreakdown,
  categoryColors,
  onSelectCategory,
  importHistoryItems,
  onDownloadErrors,
}: {
  editable: boolean;
  filters: TxFilters;
  onFiltersChange: (next: TxFilters) => void;
  savedViews: SavedViewOption[];
  activeSavedViewId: string;
  onSelectSavedView: (id: string) => void;
  onSaveSavedView: (name: string, existingId?: string) => void;
  onDeleteSavedView: (id: string) => void;
  selectedCount: number;
  deletePending: boolean;
  remapPending: boolean;
  bulkRemapState: BulkRemapState;
  onBulkRemapStateChange: (next: BulkRemapState) => void;
  onDeleteSelected: () => Promise<void>;
  onClearSelection: () => void;
  onRemap: () => Promise<void>;
  total: number;
  isFetching: boolean;
  csvBusy: boolean;
  page: number;
  pageSize: number;
  onPrevPage: () => void;
  onNextPage: () => void;
  data: Transaction[];
  columns: ColumnDef<Transaction, any>[];
  onRowSelect: (txId: string | null) => void;
  onAddTransaction: () => void;
  activeTransaction: Transaction | null;
  onEditTransaction: (tx: Transaction) => void;
  categoryBreakdown: CategoryBreakdownRow[];
  categoryColors: readonly string[];
  onSelectCategory: (category: string) => void;
  importHistoryItems: ImportHistoryItem[];
  onDownloadErrors: (importId: string) => Promise<void>;
}) {
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const table = useReactTable({
    data,
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  });
  const parentRef = useRef<HTMLDivElement | null>(null);
  const rows = table.getRowModel().rows;
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56,
    overscan: 12,
  });
  const columnVisibilityItems = table
    .getAllLeafColumns()
    .map((column) => ({
      id: column.id,
      label: typeof column.columnDef.header === "string" ? column.columnDef.header : column.id,
      visible: column.getIsVisible(),
      canHide: column.getCanHide(),
    }))
    .filter((item) => item.id !== "select");

  return (
    <>
      <Panel>
        <PanelHeader><h2 className="text-base font-semibold">Filter workspace</h2></PanelHeader>
        <PanelBody>
          <AdvancedFiltersPanel filters={filters} onChange={onFiltersChange} />
        </PanelBody>
      </Panel>

      {editable ? (
        <BulkRemapWorkspacePanel
          selectedCount={selectedCount}
          deletePending={deletePending}
          remapPending={remapPending}
          state={bulkRemapState}
          onStateChange={onBulkRemapStateChange}
          onDeleteSelected={onDeleteSelected}
          onClearSelection={onClearSelection}
          onRemap={onRemap}
        />
      ) : null}

      <SimpleDataTable
        title="Transaction grid"
        description="Virtualized ledger with consistent table, drawer, and import history surfaces."
        toolbar={
          <TableToolbar
            left={
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-muted-foreground">{total.toLocaleString()} records</span>
                <SavedViewSelector
                  views={savedViews}
                  selectedId={activeSavedViewId}
                  onSelect={onSelectSavedView}
                  onSave={onSaveSavedView}
                  onDelete={onDeleteSavedView}
                />
                {(isFetching || csvBusy) ? (
                  <MutationProgressToast label={csvBusy ? "Import processing..." : "Refreshing data..."} />
                ) : null}
              </div>
            }
            right={
              <div className="flex items-center gap-2">
                <ColumnVisibilityMenu
                  items={columnVisibilityItems}
                  onToggle={(columnId, visible) => table.getColumn(columnId)?.toggleVisibility(visible)}
                />
                <Button aria-label="Previous transactions page" variant="outline" size="sm" disabled={page <= 1} onClick={onPrevPage}>Prev</Button>
                <span className="text-sm">Page {page}</span>
                <Button aria-label="Next transactions page" variant="outline" size="sm" disabled={page * pageSize >= total} onClick={onNextPage}>Next</Button>
              </div>
            }
          />
        }
        table={
          data.length === 0 && isFetching ? (
            <div className="space-y-3 rounded-[24px] border border-border/70 bg-card/60 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-sm font-medium">Loading transactions…</p>
                  <p className="text-xs text-muted-foreground">Fetching the current page for the active filters.</p>
                </div>
                <div className="hidden gap-2 sm:flex">
                  <Skeleton className="h-8 w-24 rounded-md" />
                  <Skeleton className="h-8 w-28 rounded-md" />
                </div>
              </div>
              <div className="space-y-2">
                {Array.from({ length: 8 }).map((_, idx) => (
                  <Skeleton key={idx} className="h-10 w-full rounded-xl" />
                ))}
              </div>
            </div>
          ) : data.length === 0 ? (
            <EmptyState
              eyebrow="No data"
              title="No transactions match the current filters."
              description="Adjust the date range or add data manually or via CSV import."
              actions={editable ? [{ label: "Add transaction", onClick: onAddTransaction }] : []}
            />
          ) : (
            <VirtualizedGrid
              header={
                <table className="w-full border-collapse text-sm">
                  <thead className="sticky top-0 z-10 bg-muted">
                    {table.getHeaderGroups().map((headerGroup) => (
                      <tr key={headerGroup.id}>
                        {headerGroup.headers.map((header) => (
                          <th key={header.id} className="px-3 py-3 text-left">
                            {flexRender(header.column.columnDef.header, header.getContext())}
                          </th>
                        ))}
                      </tr>
                    ))}
                  </thead>
                </table>
              }
              body={
                <div ref={parentRef} className="h-[520px] overflow-auto">
                  <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: "relative" }}>
                    {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                      const row = rows[virtualRow.index];
                      return (
                        <div key={row.id} className="absolute left-0 top-0 w-full border-b" style={{ transform: `translateY(${virtualRow.start}px)` }}>
                          <table className="w-full table-fixed text-sm">
                            <tbody>
                              <tr onClick={() => onRowSelect(row.original.id)} className="cursor-pointer hover:bg-muted/40">
                                {row.getVisibleCells().map((cell) => (
                                  <td key={cell.id} className="px-3 py-3">
                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                  </td>
                                ))}
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      );
                    })}
                  </div>
                </div>
              }
            />
          )
        }
        side={
          <>
            <CategoryBreakdownPanel categoryBreakdown={categoryBreakdown} categoryColors={categoryColors} onSelect={onSelectCategory} />
            <ImportHistoryPanel items={importHistoryItems} onDownloadErrors={onDownloadErrors} />
          </>
        }
      />

      <DetailDrawer
        open={Boolean(activeTransaction)}
        title="Transaction detail"
        onClose={() => onRowSelect(null)}
      >
        <SelectedTransactionPanel transaction={activeTransaction} editable={editable} onEdit={onEditTransaction} inDrawer />
      </DetailDrawer>

      {editable ? (
        <BulkSelectionBar
          selectedCount={selectedCount}
          deleting={deletePending}
          onDelete={onDeleteSelected}
          onClear={onClearSelection}
        />
      ) : null}
    </>
  );
}
