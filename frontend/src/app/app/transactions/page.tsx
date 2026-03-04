"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useRouter } from "next/navigation";

import { FiltersBar, type TxFilters } from "@/components/common/filters-bar";
import { useToast } from "@/components/common/use-toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { canEdit } from "@/lib/auth/rbac";
import { ApiError } from "@/lib/api/client";
import { formatMoney, startOfMonthISO, todayISO } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";
import type { Transaction } from "@/types/domain";
import {
  importCsv,
  useBulkRemapCategory,
  useCreateTransaction,
  useDeleteTransaction,
  useTransactions,
  useUpdateTransaction,
} from "@/features/transactions/hooks";

const helper = createColumnHelper<Transaction>();

type CsvField = "date" | "amount" | "type" | "category" | "vendor" | "notes";

type CsvMapping = Record<CsvField, string>;

type CsvRawRow = Record<string, string>;

const csvFields: Array<{ key: CsvField; label: string; required: boolean }> = [
  { key: "date", label: "Date", required: true },
  { key: "amount", label: "Amount", required: true },
  { key: "type", label: "Type", required: true },
  { key: "category", label: "Category", required: true },
  { key: "vendor", label: "Vendor", required: false },
  { key: "notes", label: "Notes", required: false },
];
const defaultCsvMaxBytes = 5 * 1024 * 1024;
const csvMaxBytes = Number(process.env.NEXT_PUBLIC_CSV_MAX_BYTES || defaultCsvMaxBytes);

function normalizeHeader(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
}

function parseCsvContent(text: string): { headers: string[]; rows: CsvRawRow[] } {
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length === 0) {
    return { headers: [], rows: [] };
  }
  const headers = lines[0].split(",").map((h) => h.trim());
  const rows = lines.slice(1).map((line) => {
    const cells = line.split(",");
    const row: CsvRawRow = {};
    headers.forEach((header, idx) => {
      row[header] = (cells[idx] ?? "").trim();
    });
    return row;
  });
  return { headers, rows };
}

function autoDetectMapping(headers: string[]): CsvMapping {
  const normalized = headers.map((h) => ({ original: h, normalized: normalizeHeader(h) }));
  const pick = (...aliases: string[]) => {
    const hit = normalized.find((item) => aliases.includes(item.normalized));
    return hit?.original ?? "";
  };

  return {
    date: pick("date", "transactiondate", "posteddate"),
    amount: pick("amount", "value", "total"),
    type: pick("type", "transactiontype", "kind"),
    category: pick("category", "group", "expensecategory"),
    vendor: pick("vendor", "merchant", "payee", "supplier"),
    notes: pick("notes", "note", "memo", "description"),
  };
}

function mappingToApiPayload(mapping: CsvMapping): Record<string, string> {
  return {
    date: mapping.date,
    amount: mapping.amount,
    type: mapping.type,
    category: mapping.category,
    vendor: mapping.vendor || "",
    notes: mapping.notes || "",
  };
}

export default function TransactionsPage() {
  const router = useRouter();
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const orgId = useAppStore((s) => s.selectedOrgId);
  const editable = canEdit(role);
  const toast = useToast();

  const [filters, setFilters] = useState<TxFilters>({
    from: startOfMonthISO(),
    to: todayISO(),
    type: "",
    category: "",
    q: "",
  });
  const [page, setPage] = useState(1);
  const pageSize = 100;
  const query = useTransactions({ ...filters, page, page_size: pageSize });

  const createTx = useCreateTransaction();
  const updateTx = useUpdateTransaction();
  const deleteTx = useDeleteTransaction();
  const bulkRemap = useBulkRemapCategory();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const [newTx, setNewTx] = useState({ date: todayISO(), amount: "", type: "EXPENSE", category: "Misc", vendor: "", notes: "" });
  const [editingId, setEditingId] = useState<string | null>(null);

  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRows, setCsvRows] = useState<CsvRawRow[]>([]);
  const [csvPreview, setCsvPreview] = useState<{ rows: number; detected_duplicates: number } | null>(null);
  const [mapping, setMapping] = useState<CsvMapping>({ date: "", amount: "", type: "", category: "", vendor: "", notes: "" });
  const [csvBusy, setCsvBusy] = useState(false);

  const [bulkRemapState, setBulkRemapState] = useState({
    from_category: "",
    to_category: "",
    from_date: filters.from,
    to_date: filters.to,
  });

  const data = useMemo(() => query.data?.items ?? [], [query.data?.items]);
  const total = query.data?.total ?? 0;

  const requiredMissing = csvFields.filter((field) => field.required && !mapping[field.key]).map((field) => field.label);

  const mappedPreviewRows = useMemo(() => {
    if (csvRows.length === 0) return [] as Array<Record<CsvField, string>>;
    return csvRows.slice(0, 12).map((row) => ({
      date: mapping.date ? row[mapping.date] ?? "" : "",
      amount: mapping.amount ? row[mapping.amount] ?? "" : "",
      type: mapping.type ? row[mapping.type] ?? "" : "",
      category: mapping.category ? row[mapping.category] ?? "" : "",
      vendor: mapping.vendor ? row[mapping.vendor] ?? "" : "",
      notes: mapping.notes ? row[mapping.notes] ?? "" : "",
    }));
  }, [csvRows, mapping]);

  const localDupes = useMemo(() => {
    if (csvRows.length === 0 || requiredMissing.length > 0) return 0;
    const seen = new Set<string>();
    let dupes = 0;
    for (const row of csvRows) {
      const key = `${row[mapping.date] || ""}|${row[mapping.amount] || ""}|${row[mapping.type] || ""}|${row[mapping.category] || ""}|${row[mapping.vendor] || ""}`;
      if (seen.has(key)) dupes += 1;
      seen.add(key);
    }
    return dupes;
  }, [csvRows, mapping, requiredMissing.length]);

  const handleApiError = useCallback((error: unknown, fallbackTitle: string) => {
    if (error instanceof ApiError) {
      if (error.status === 401) {
        toast.toast({ title: "Session expired", description: "Please login again." });
        router.push("/auth/login");
        return;
      }
      toast.toast({ title: fallbackTitle, description: error.message || `Request failed (${error.status})` });
      return;
    }
    toast.toast({ title: fallbackTitle, description: "Unexpected error. Please retry." });
  }, [router, toast]);

  const columns = useMemo(
    () => [
      helper.display({
        id: "select",
        header: () => (
          editable ? (
            <input
              aria-label="Select all rows"
              type="checkbox"
              checked={data.length > 0 && selectedIds.size === data.length}
              onChange={(e) => {
                if (e.target.checked) {
                  setSelectedIds(new Set(data.map((row) => row.id)));
                } else {
                  setSelectedIds(new Set());
                }
              }}
            />
          ) : null
        ),
        cell: ({ row }) =>
          editable ? (
            <input
              aria-label={`Select ${row.original.id}`}
              type="checkbox"
              checked={selectedIds.has(row.original.id)}
              onChange={(e) => {
                setSelectedIds((prev) => {
                  const next = new Set(prev);
                  if (e.target.checked) next.add(row.original.id);
                  else next.delete(row.original.id);
                  return next;
                });
              }}
            />
          ) : null,
      }),
      helper.accessor("date", { header: "Date" }),
      helper.accessor("type", { header: "Type" }),
      helper.accessor("category", { header: "Category" }),
      helper.accessor("vendor", { header: "Vendor" }),
      helper.accessor("amount", {
        header: "Amount",
        cell: (info) => formatMoney(info.getValue()),
      }),
      helper.display({
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="flex gap-2">
            {editable ? (
              <Button size="sm" variant="outline" onClick={() => setEditingId(row.original.id)}>
                Edit
              </Button>
            ) : null}
            {editable ? (
              <Button
                size="sm"
                variant="destructive"
                onClick={async () => {
                  if (!confirm("Delete transaction?")) return;
                  try {
                    await deleteTx.mutateAsync(row.original.id);
                    toast.toast({ title: "Deleted" });
                    setSelectedIds((prev) => {
                      const next = new Set(prev);
                      next.delete(row.original.id);
                      return next;
                    });
                  } catch (error) {
                    handleApiError(error, "Delete failed");
                  }
                }}
              >
                Delete
              </Button>
            ) : null}
          </div>
        ),
      }),
    ],
    [editable, data, selectedIds, deleteTx, handleApiError, toast],
  );

  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });

  const parentRef = useRef<HTMLDivElement | null>(null);
  const rows = table.getRowModel().rows;
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48,
    overscan: 12,
  });

  async function handleCsvFile(file: File | null) {
    setCsvFile(file);
    setCsvPreview(null);
    if (!file) {
      setCsvHeaders([]);
      setCsvRows([]);
      setMapping({ date: "", amount: "", type: "", category: "", vendor: "", notes: "" });
      return;
    }
    if (file.size > csvMaxBytes) {
      toast.toast({
        title: "CSV too large",
        description: `Maximum allowed size is ${Math.floor(csvMaxBytes / 1024 / 1024)}MB.`,
      });
      setCsvFile(null);
      setCsvHeaders([]);
      setCsvRows([]);
      setMapping({ date: "", amount: "", type: "", category: "", vendor: "", notes: "" });
      return;
    }
    const text = await file.text();
    const parsed = parseCsvContent(text);
    setCsvHeaders(parsed.headers);
    setCsvRows(parsed.rows);
    setMapping(autoDetectMapping(parsed.headers));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Transactions</h1>
        <p className="text-sm text-muted-foreground">{total} records</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Filters</CardTitle></CardHeader>
        <CardContent>
          <FiltersBar
            filters={filters}
            onChange={(f) => {
              setFilters(f);
              setPage(1);
              setBulkRemapState((prev) => ({ ...prev, from_date: f.from, to_date: f.to }));
            }}
          />
        </CardContent>
      </Card>

      {editable ? (
        <Card>
          <CardHeader><CardTitle>Bulk Actions</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm text-muted-foreground">Selected rows: {selectedIds.size}</p>
              <Button
                variant="outline"
                disabled={selectedIds.size === 0 || deleteTx.isPending}
                onClick={async () => {
                  if (!confirm(`Delete ${selectedIds.size} selected transactions?`)) return;
                  try {
                    const ids = Array.from(selectedIds);
                    await Promise.all(ids.map((id) => deleteTx.mutateAsync(id)));
                    setSelectedIds(new Set());
                    toast.toast({ title: "Selected transactions deleted" });
                  } catch (error) {
                    handleApiError(error, "Bulk delete failed");
                  }
                }}
              >
                Delete Selected
              </Button>
              <Button variant="ghost" disabled={selectedIds.size === 0} onClick={() => setSelectedIds(new Set())}>
                Clear Selection
              </Button>
            </div>

            <div className="grid gap-2 md:grid-cols-5">
              <Input
                placeholder="From category"
                data-testid="bulk-remap-from-category"
                value={bulkRemapState.from_category}
                onChange={(e) => setBulkRemapState({ ...bulkRemapState, from_category: e.target.value })}
              />
              <Input
                placeholder="To category"
                data-testid="bulk-remap-to-category"
                value={bulkRemapState.to_category}
                onChange={(e) => setBulkRemapState({ ...bulkRemapState, to_category: e.target.value })}
              />
              <Input
                type="date"
                value={bulkRemapState.from_date}
                onChange={(e) => setBulkRemapState({ ...bulkRemapState, from_date: e.target.value })}
              />
              <Input
                type="date"
                value={bulkRemapState.to_date}
                onChange={(e) => setBulkRemapState({ ...bulkRemapState, to_date: e.target.value })}
              />
              <Button
                data-testid="bulk-remap-submit"
                disabled={!orgId || !bulkRemapState.from_category || !bulkRemapState.to_category || bulkRemap.isPending}
                onClick={async () => {
                  if (!orgId) return;
                  try {
                    const result = await bulkRemap.mutateAsync({
                      org_id: orgId,
                      from_category: bulkRemapState.from_category,
                      to_category: bulkRemapState.to_category,
                      from_date: bulkRemapState.from_date || undefined,
                      to_date: bulkRemapState.to_date || undefined,
                    });
                    toast.toast({ title: "Bulk remap applied", description: `Updated ${result.updated_count} rows` });
                    query.refetch();
                  } catch (error) {
                    handleApiError(error, "Bulk remap failed");
                  }
                }}
              >
                Remap Category
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {editable ? (
        <Card>
          <CardHeader><CardTitle>Add Transaction</CardTitle></CardHeader>
          <CardContent>
            <form
              className="grid gap-2 md:grid-cols-6"
              onSubmit={async (e) => {
                e.preventDefault();
                if (!orgId) return;
                try {
                  await createTx.mutateAsync({
                    org_id: orgId,
                    date: newTx.date,
                    amount: newTx.amount,
                    type: newTx.type as "REVENUE" | "EXPENSE",
                    category: newTx.category,
                    vendor: newTx.vendor || null,
                    notes: newTx.notes || null,
                  });
                  setNewTx({ date: todayISO(), amount: "", type: "EXPENSE", category: "Misc", vendor: "", notes: "" });
                  toast.toast({ title: "Transaction added" });
                } catch (error) {
                  handleApiError(error, "Create transaction failed");
                }
              }}
            >
              <Input type="date" value={newTx.date} onChange={(e) => setNewTx({ ...newTx, date: e.target.value })} />
              <Input placeholder="Amount" value={newTx.amount} onChange={(e) => setNewTx({ ...newTx, amount: e.target.value })} required />
              <Select value={newTx.type} onValueChange={(value) => setNewTx({ ...newTx, type: value })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="REVENUE">Revenue</SelectItem>
                  <SelectItem value="EXPENSE">Expense</SelectItem>
                </SelectContent>
              </Select>
              <Input placeholder="Category" value={newTx.category} onChange={(e) => setNewTx({ ...newTx, category: e.target.value })} required />
              <Input placeholder="Vendor" value={newTx.vendor} onChange={(e) => setNewTx({ ...newTx, vendor: e.target.value })} />
              <Button type="submit">Add</Button>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {editable ? (
        <Card>
          <CardHeader><CardTitle>CSV Import</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <input data-testid="csv-file-input" type="file" accept=".csv" onChange={(e) => void handleCsvFile(e.target.files?.[0] ?? null)} />

            {csvHeaders.length > 0 ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Mapping</p>
                <div className="grid gap-2 md:grid-cols-2">
                  {csvFields.map((field) => (
                    <div key={field.key} className="space-y-1">
                      <p className="text-xs text-muted-foreground">
                        {field.label} {field.required ? "*" : "(optional)"}
                      </p>
                      <Select
                        value={mapping[field.key] || "__none__"}
                        onValueChange={(value) =>
                          setMapping((prev) => ({
                            ...prev,
                            [field.key]: value === "__none__" ? "" : value,
                          }))
                        }
                      >
                        <SelectTrigger data-testid={`csv-map-${field.key}`}><SelectValue placeholder={`Select ${field.label} column`} /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="__none__">Not mapped</SelectItem>
                          {csvHeaders.map((header) => (
                            <SelectItem key={`${field.key}-${header}`} value={header}>{header}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                </div>

                {requiredMissing.length > 0 ? (
                  <p className="text-sm text-danger">Missing required mappings: {requiredMissing.join(", ")}</p>
                ) : null}
              </div>
            ) : null}

            <div className="flex gap-2">
              <Button
                data-testid="csv-preview-button"
                variant="outline"
                disabled={!csvFile || !orgId || requiredMissing.length > 0 || csvBusy}
                onClick={async () => {
                  if (!csvFile || !orgId || requiredMissing.length > 0) return;
                  setCsvBusy(true);
                  try {
                    const out = await importCsv(orgId, csvFile, mappingToApiPayload(mapping), false);
                    setCsvPreview(out.preview);
                  } catch (error) {
                    handleApiError(error, "CSV preview failed");
                  } finally {
                    setCsvBusy(false);
                  }
                }}
              >
                Preview Import
              </Button>
              <Button
                data-testid="csv-confirm-button"
                disabled={!csvFile || !orgId || requiredMissing.length > 0 || csvBusy}
                onClick={async () => {
                  if (!csvFile || !orgId || requiredMissing.length > 0) return;
                  setCsvBusy(true);
                  try {
                    const out = await importCsv(orgId, csvFile, mappingToApiPayload(mapping), true);
                    setCsvPreview(out.preview);
                    toast.toast({ title: "CSV imported", description: `Inserted ${out.inserted_count}` });
                    query.refetch();
                  } catch (error) {
                    handleApiError(error, "CSV import failed");
                  } finally {
                    setCsvBusy(false);
                  }
                }}
              >
                Confirm Import
              </Button>
            </div>

            {csvPreview ? (
              <p className="text-sm text-muted-foreground">
                Rows: {csvPreview.rows} | Duplicates detected by backend: {csvPreview.detected_duplicates}
              </p>
            ) : null}

            {mappedPreviewRows.length > 0 ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Mapped preview (first {mappedPreviewRows.length}) | Local duplicate hints: {localDupes}</p>
                <div className="max-h-64 overflow-auto rounded-md border">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-muted">
                      <tr>
                        {csvFields.map((field) => (
                          <th key={field.key} className="px-2 py-1 text-left">{field.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {mappedPreviewRows.map((row, idx) => (
                        <tr key={idx} className="border-t">
                          {csvFields.map((field) => (
                            <td key={`${idx}-${field.key}`} className="px-2 py-1">{row[field.key]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {editingId ? (
        <Card>
          <CardHeader><CardTitle>Edit Transaction</CardTitle></CardHeader>
          <CardContent>
            {(() => {
              const tx = data.find((d) => d.id === editingId);
              if (!tx) return null;
              return (
                <form
                  className="grid gap-2 md:grid-cols-6"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const form = e.currentTarget as HTMLFormElement;
                    const fd = new FormData(form);
                    try {
                      await updateTx.mutateAsync({
                        id: tx.id,
                        payload: {
                          date: String(fd.get("date")),
                          amount: String(fd.get("amount")),
                          category: String(fd.get("category")),
                          vendor: String(fd.get("vendor") || ""),
                          notes: String(fd.get("notes") || ""),
                        },
                      });
                      setEditingId(null);
                      toast.toast({ title: "Updated" });
                    } catch (error) {
                      handleApiError(error, "Update failed");
                    }
                  }}
                >
                  <Input name="date" type="date" defaultValue={tx.date} />
                  <Input name="amount" defaultValue={tx.amount} />
                  <Input name="category" defaultValue={tx.category} />
                  <Input name="vendor" defaultValue={tx.vendor || ""} />
                  <Input name="notes" defaultValue={tx.notes || ""} />
                  <div className="flex gap-2">
                    <Button type="submit">Save</Button>
                    <Button type="button" variant="outline" onClick={() => setEditingId(null)}>Cancel</Button>
                  </div>
                </form>
              );
            })()}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader><CardTitle>Transactions</CardTitle></CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <table className="w-full border-collapse text-sm">
              <thead className="sticky top-0 z-10 bg-muted">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="px-3 py-2 text-left">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
            </table>
            <div ref={parentRef} className="h-[420px] overflow-auto">
              <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: "relative" }}>
                {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                  const row = rows[virtualRow.index];
                  return (
                    <div
                      key={row.id}
                      className="absolute left-0 top-0 w-full border-b"
                      style={{ transform: `translateY(${virtualRow.start}px)` }}
                    >
                      <table className="w-full table-fixed text-sm">
                        <tbody>
                          <tr>
                            {row.getVisibleCells().map((cell) => (
                              <td key={cell.id} className="px-3 py-2">
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
          </div>
          <div className="mt-3 flex items-center justify-end gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
            <span className="text-sm">Page {page}</span>
            <Button variant="outline" size="sm" disabled={page * pageSize >= total} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
