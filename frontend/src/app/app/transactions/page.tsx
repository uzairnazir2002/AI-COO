"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Download, Pencil, Plus, Trash2, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { Cell, Pie, PieChart, Tooltip } from "recharts";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { FiltersBar, type TxFilters } from "@/components/common/filters-bar";
import { SectionHeader } from "@/components/common/section-header";
import { useToast } from "@/components/common/use-toast";
import { ChartCanvas } from "@/components/charts/chart-canvas";
import { ChartFrame } from "@/components/charts/chart-frame";
import { chartPalette } from "@/components/charts/theme";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ApiError } from "@/lib/api/client";
import { canEdit } from "@/lib/auth/rbac";
import { buildCategoryBreakdown } from "@/lib/utils/chart";
import { formatDate, formatMoney, startOfMonthISO, todayISO } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";
import type { Transaction } from "@/types/domain";
import {
  type AlertRecalcMetadata,
  useCreateImportProfile,
  useDeleteImportProfile,
  downloadImportErrors,
  importCsv,
  useImportProfiles,
  useBulkRemapCategory,
  useCreateTransaction,
  useUpdateImportProfile,
  useDeleteTransaction,
  useImportHistory,
  useTransactions,
  useUpdateTransaction,
} from "@/features/transactions/hooks";

const helper = createColumnHelper<Transaction>();

type CsvField = "date" | "amount" | "type" | "category" | "vendor" | "notes" | "location";
type CsvMapping = Record<CsvField, string>;
type CsvRawRow = Record<string, string>;

const csvFields: Array<{ key: CsvField; label: string; required: boolean }> = [
  { key: "date", label: "Date", required: true },
  { key: "amount", label: "Amount", required: true },
  { key: "type", label: "Type", required: true },
  { key: "category", label: "Category", required: true },
  { key: "vendor", label: "Vendor", required: false },
  { key: "notes", label: "Notes", required: false },
  { key: "location", label: "Location", required: false },
];

const defaultCsvMaxBytes = 5 * 1024 * 1024;
const csvMaxBytes = Number(process.env.NEXT_PUBLIC_CSV_MAX_BYTES || defaultCsvMaxBytes);

function normalizeHeader(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
}

function parseCsvContent(text: string): { headers: string[]; rows: CsvRawRow[] } {
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length === 0) return { headers: [], rows: [] };
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
  const pick = (...aliases: string[]) => normalized.find((item) => aliases.includes(item.normalized))?.original ?? "";
  return {
    date: pick("date", "transactiondate", "posteddate"),
    amount: pick("amount", "value", "total"),
    type: pick("type", "transactiontype", "kind"),
    category: pick("category", "group", "expensecategory"),
    vendor: pick("vendor", "merchant", "payee", "supplier"),
    notes: pick("notes", "note", "memo", "description"),
    location: pick("location", "branch", "store", "site", "office", "locationcode"),
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
    location: mapping.location || "",
  };
}

export default function TransactionsPage() {
  const router = useRouter();
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const orgId = useAppStore((s) => s.selectedOrgId);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const editable = canEdit(role);
  const toast = useToast();

  const [filters, setFilters] = useState<TxFilters>({ from: startOfMonthISO(), to: todayISO(), type: "", category: "", q: "" });
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [composeOpen, setComposeOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<Transaction | null>(null);
  const [newTx, setNewTx] = useState({ date: todayISO(), amount: "", type: "EXPENSE", category: "Misc", vendor: "", notes: "" });
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRows, setCsvRows] = useState<CsvRawRow[]>([]);
  const [csvPreview, setCsvPreview] = useState<{ rows: number; detected_duplicates: number } | null>(null);
  const [mapping, setMapping] = useState<CsvMapping>({
    date: "",
    amount: "",
    type: "",
    category: "",
    vendor: "",
    notes: "",
    location: "",
  });
  const [selectedProfileId, setSelectedProfileId] = useState<string>("");
  const [profileName, setProfileName] = useState("");
  const [profileShared, setProfileShared] = useState(false);
  const [csvBusy, setCsvBusy] = useState(false);
  const [bulkRemapState, setBulkRemapState] = useState({ from_category: "", to_category: "", from_date: filters.from, to_date: filters.to });

  const pageSize = 100;
  const query = useTransactions({ ...filters, page, page_size: pageSize });
  const importHistory = useImportHistory(1, 20);
  const createTx = useCreateTransaction();
  const updateTx = useUpdateTransaction();
  const deleteTx = useDeleteTransaction();
  const bulkRemap = useBulkRemapCategory();
  const profiles = useImportProfiles();
  const createProfile = useCreateImportProfile();
  const updateProfile = useUpdateImportProfile();
  const deleteProfile = useDeleteImportProfile();

  const data = useMemo(() => query.data?.items ?? [], [query.data?.items]);
  const total = query.data?.total ?? 0;
  const requiredMissing = csvFields.filter((field) => field.required && !mapping[field.key]).map((field) => field.label);
  const selectedProfile = profiles.data?.find((p) => p.id === selectedProfileId) || null;

  const mappedPreviewRows = useMemo(
    () =>
      csvRows.slice(0, 10).map((row) => ({
        date: mapping.date ? row[mapping.date] ?? "" : "",
        amount: mapping.amount ? row[mapping.amount] ?? "" : "",
        type: mapping.type ? row[mapping.type] ?? "" : "",
        category: mapping.category ? row[mapping.category] ?? "" : "",
        vendor: mapping.vendor ? row[mapping.vendor] ?? "" : "",
        notes: mapping.notes ? row[mapping.notes] ?? "" : "",
        location: mapping.location ? row[mapping.location] ?? "" : "",
      })),
    [csvRows, mapping],
  );

  const localDupes = useMemo(() => {
    if (csvRows.length === 0 || requiredMissing.length > 0) return 0;
    const seen = new Set<string>();
    let dupes = 0;
    for (const row of csvRows) {
      const key = `${row[mapping.date] || ""}|${row[mapping.amount] || ""}|${row[mapping.type] || ""}|${row[mapping.category] || ""}|${row[mapping.location] || ""}|${row[mapping.vendor] || ""}`;
      if (seen.has(key)) dupes += 1;
      seen.add(key);
    }
    return dupes;
  }, [csvRows, mapping, requiredMissing.length]);

  const categoryBreakdown = useMemo(
    () =>
      buildCategoryBreakdown(
        data
          .filter((row) => row.type === "EXPENSE")
          .map((row) => ({ category: row.category, amount: row.amount })),
        5,
      ),
    [data],
  );
  const categoryColors = chartPalette.pie;

  const handleApiError = useCallback((error: unknown, fallbackTitle: string) => {
    if (error instanceof ApiError) {
      toast.toast({ title: fallbackTitle, description: error.message || `Request failed (${error.status})`, variant: "danger" });
      return;
    }
    toast.toast({ title: fallbackTitle, description: "Unexpected error. Please retry.", variant: "danger" });
  }, [toast]);

  const describeAlertRefresh = useCallback((meta?: AlertRecalcMetadata | null) => {
    if (!meta) return "Alert refresh queued.";
    return meta.queued
      ? `Alert refresh queued (job ${meta.taskId}).`
      : `Alert refresh already pending (job ${meta.taskId}).`;
  }, []);

  async function handleCsvFile(file: File | null) {
    setCsvFile(file);
    setCsvPreview(null);
    if (!file) {
      setCsvHeaders([]);
      setCsvRows([]);
      setMapping({ date: "", amount: "", type: "", category: "", vendor: "", notes: "", location: "" });
      return;
    }
    if (file.size > csvMaxBytes) {
      toast.toast({ title: "CSV too large", description: `Maximum allowed size is ${Math.floor(csvMaxBytes / 1024 / 1024)}MB.`, variant: "danger" });
      setCsvFile(null);
      setCsvHeaders([]);
      setCsvRows([]);
      setMapping({ date: "", amount: "", type: "", category: "", vendor: "", notes: "", location: "" });
      return;
    }
    const text = await file.text();
    const parsed = parseCsvContent(text);
    setCsvHeaders(parsed.headers);
    setCsvRows(parsed.rows);
    setMapping(autoDetectMapping(parsed.headers));
    setSelectedProfileId("");
  }

  const columns = useMemo(
    () => [
      helper.display({
        id: "select",
        header: () =>
          editable ? (
            <input
              aria-label="Select all rows"
              type="checkbox"
              checked={data.length > 0 && selectedIds.size === data.length}
              onChange={(e) => setSelectedIds(e.target.checked ? new Set(data.map((row) => row.id)) : new Set())}
            />
          ) : null,
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
      helper.accessor("date", { header: "Date", cell: (info) => formatDate(info.getValue()) }),
      helper.accessor("type", { header: "Type" }),
      helper.accessor("category", { header: "Category" }),
      helper.accessor("vendor", { header: "Vendor" }),
      helper.accessor("amount", { header: "Amount", cell: (info) => formatMoney(info.getValue()) }),
      helper.display({
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <div className="flex gap-2">
            {editable ? (
              <Button size="sm" variant="outline" onClick={() => setEditingRow(row.original)}>
                <Pencil className="mr-2 h-4 w-4" /> Edit
              </Button>
            ) : null}
            {editable ? (
              <Button
                size="sm"
                variant="destructive"
                onClick={async () => {
                  try {
                    const result = await deleteTx.mutateAsync(row.original.id);
                    toast.toast({ title: "Deleted", description: describeAlertRefresh(result.alertRecalc) });
                  } catch (error) {
                    handleApiError(error, "Delete failed");
                  }
                }}
              >
                <Trash2 className="mr-2 h-4 w-4" /> Delete
              </Button>
            ) : null}
          </div>
        ),
      }),
    ],
    [data, deleteTx, describeAlertRefresh, editable, handleApiError, selectedIds, toast],
  );
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });
  const parentRef = useRef<HTMLDivElement | null>(null);
  const rows = table.getRowModel().rows;
  const rowVirtualizer = useVirtualizer({ count: rows.length, getScrollElement: () => parentRef.current, estimateSize: () => 56, overscan: 12 });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const searchParams = new URLSearchParams(window.location.search);
    const action = searchParams.get("action");
    if (action === "compose") {
      setComposeOpen(true);
      router.replace("/app/transactions");
    }
    if (action === "import") {
      setImportOpen(true);
      router.replace("/app/transactions");
    }
  }, [router]);

  if (!orgId) {
    return (
      <EmptyState
        eyebrow="No organization"
        title="Select an organization before working with transactions."
        description="Transaction list, import history, filters, and analytics all require an active organization context."
        actions={[{ label: "Go to organizations", href: "/app/orgs" }]}
      />
    );
  }

  if (query.error) {
    return <ErrorState description={String((query.error as Error).message || query.error)} onRetry={() => void query.refetch()} />;
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Transactions"
        description="Fast ledger operations with virtualization, org-scoped filtering, and import history."
        actions={
          editable ? (
            <>
              <Dialog open={importOpen} onOpenChange={setImportOpen}>
                <DialogTrigger asChild>
                  <Button id="import" variant="outline">
                    <Upload className="mr-2 h-4 w-4" />
                    Import CSV
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-5xl">
                  <DialogHeader>
                    <DialogTitle>CSV import wizard</DialogTitle>
                    <DialogDescription>Upload, map columns, preview, detect duplicates, and confirm without leaving the page.</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <input data-testid="csv-file-input" type="file" accept=".csv" onChange={(e) => void handleCsvFile(e.target.files?.[0] ?? null)} />
                    {csvHeaders.length > 0 ? (
                      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
                        <div className="space-y-3">
                          <div className="rounded-xl border border-border/70 p-3">
                            <p className="text-sm font-medium">Saved profiles</p>
                            <div className="mt-2 grid gap-2 md:grid-cols-[1fr_auto_auto]">
                              <Select
                                value={selectedProfileId || "__none__"}
                                onValueChange={(value) => {
                                  if (value === "__none__") {
                                    setSelectedProfileId("");
                                    return;
                                  }
                                  const profile = profiles.data?.find((p) => p.id === value);
                                  if (!profile) return;
                                  setSelectedProfileId(profile.id);
                                  setProfileName(profile.name);
                                  setProfileShared(profile.user_id === null);
                                  setMapping((prev) => ({ ...prev, ...(profile.column_map as Partial<CsvMapping>) }));
                                }}
                              >
                                <SelectTrigger><SelectValue placeholder="Use saved profile" /></SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="__none__">No profile</SelectItem>
                                  {(profiles.data || []).map((profile) => (
                                    <SelectItem key={profile.id} value={profile.id}>
                                      {profile.name}{profile.user_id === null ? " (shared)" : ""}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              <Button
                                variant="outline"
                                disabled={!selectedProfileId || deleteProfile.isPending}
                                onClick={async () => {
                                  if (!selectedProfileId) return;
                                  try {
                                    await deleteProfile.mutateAsync(selectedProfileId);
                                    setSelectedProfileId("");
                                    toast.toast({ title: "Profile deleted" });
                                  } catch (error) {
                                    handleApiError(error, "Delete profile failed");
                                  }
                                }}
                              >
                                Delete
                              </Button>
                            </div>
                            <div className="mt-2 grid gap-2 md:grid-cols-[1fr_auto_auto]">
                              <Input
                                placeholder="Profile name"
                                value={profileName}
                                onChange={(e) => setProfileName(e.target.value)}
                              />
                              <Select value={profileShared ? "shared" : "personal"} onValueChange={(v) => setProfileShared(v === "shared")}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="personal">Personal</SelectItem>
                                  <SelectItem value="shared">Shared</SelectItem>
                                </SelectContent>
                              </Select>
                              <Button
                                variant="outline"
                                disabled={profileName.trim().length === 0 || requiredMissing.length > 0 || createProfile.isPending || updateProfile.isPending}
                                onClick={async () => {
                                  const payload = {
                                    name: profileName.trim(),
                                    column_map: mappingToApiPayload(mapping),
                                    shared: profileShared,
                                  };
                                  try {
                                    if (selectedProfileId) {
                                      const saved = await updateProfile.mutateAsync({ profile_id: selectedProfileId, ...payload });
                                      setSelectedProfileId(saved.id);
                                      toast.toast({ title: "Profile updated" });
                                    } else {
                                      const saved = await createProfile.mutateAsync(payload);
                                      setSelectedProfileId(saved.id);
                                      toast.toast({ title: "Profile saved" });
                                    }
                                  } catch (error) {
                                    handleApiError(error, "Save profile failed");
                                  }
                                }}
                              >
                                {selectedProfile ? "Update profile" : "Save profile"}
                              </Button>
                            </div>
                          </div>
                          <p className="text-sm font-medium">Column mapping</p>
                          {csvFields.map((field) => (
                            <div key={field.key} className="space-y-1">
                              <p className="text-xs text-muted-foreground">{field.label} {field.required ? "*" : "(optional)"}</p>
                              <Select
                                value={mapping[field.key] || "__none__"}
                                onValueChange={(value) => setMapping((prev) => ({ ...prev, [field.key]: value === "__none__" ? "" : value }))}
                              >
                                <SelectTrigger data-testid={`csv-map-${field.key}`}><SelectValue placeholder={`Select ${field.label} column`} /></SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="__none__">Not mapped</SelectItem>
                                  {csvHeaders.map((header) => <SelectItem key={`${field.key}-${header}`} value={header}>{header}</SelectItem>)}
                                </SelectContent>
                              </Select>
                            </div>
                          ))}
                          {requiredMissing.length > 0 ? <p className="text-sm text-danger">Missing required mappings: {requiredMissing.join(", ")}</p> : null}
                          <div
                            data-testid="csv-action-footer"
                            className="sticky bottom-0 z-20 -mx-3 mt-2 space-y-2 border-t border-border/70 bg-background/95 px-3 pb-1 pt-3 backdrop-blur"
                          >
                            <p className="text-xs text-muted-foreground">
                              Validation summary: {requiredMissing.length > 0 ? `Missing ${requiredMissing.join(", ")}` : "All required fields mapped"}
                            </p>
                            <div className="flex flex-wrap gap-2">
                              <Button
                                data-testid="csv-preview-button"
                                variant="outline"
                                disabled={!csvFile || requiredMissing.length > 0 || csvBusy}
                                onClick={async () => {
                                  if (!csvFile || requiredMissing.length > 0) return;
                                  setCsvBusy(true);
                                  try {
                                    const out = await importCsv(orgId, csvFile, selectedProfileId ? undefined : mappingToApiPayload(mapping), false, selectedProfileId || undefined);
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
                                disabled={!csvFile || requiredMissing.length > 0 || csvBusy}
                                onClick={async () => {
                                  if (!csvFile || requiredMissing.length > 0) return;
                                  setCsvBusy(true);
                                  try {
                                    const out = await importCsv(orgId, csvFile, selectedProfileId ? undefined : mappingToApiPayload(mapping), true, selectedProfileId || undefined);
                                    setCsvPreview(out.preview);
                                    const refreshText = describeAlertRefresh(out.alertRecalc);
                                    toast.toast({
                                      title: "CSV imported",
                                      description: refreshText ? `Inserted ${out.inserted_count}. ${refreshText}` : `Inserted ${out.inserted_count}`,
                                    });
                                    void query.refetch();
                                    void importHistory.refetch();
                                    setImportOpen(false);
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
                            {csvPreview ? <p className="text-sm text-muted-foreground">Rows: {csvPreview.rows} | Duplicates detected by backend: {csvPreview.detected_duplicates}</p> : null}
                            <p className="text-sm text-muted-foreground">Local duplicate hints: {localDupes}</p>
                          </div>
                        </div>
                        <div className="space-y-3">
                          <p className="text-sm font-medium">Preview</p>
                          <div className="max-h-[420px] overflow-auto rounded-2xl border border-border">
                            <table className="w-full text-xs">
                              <thead className="sticky top-0 bg-muted">
                                <tr>
                                  {csvFields.map((field) => <th key={field.key} className="px-2 py-2 text-left">{field.label}</th>)}
                                </tr>
                              </thead>
                              <tbody>
                                {mappedPreviewRows.map((row, idx) => (
                                  <tr key={idx} className="border-t">
                                    {csvFields.map((field) => <td key={`${idx}-${field.key}`} className="px-2 py-2">{row[field.key]}</td>)}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </DialogContent>
              </Dialog>

              <Dialog open={composeOpen} onOpenChange={setComposeOpen}>
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
                      try {
                        const result = await createTx.mutateAsync({
                          org_id: orgId,
                          location_id: selectedLocationId || null,
                          date: newTx.date,
                          amount: newTx.amount,
                          type: newTx.type as "REVENUE" | "EXPENSE",
                          category: newTx.category,
                          vendor: newTx.vendor || null,
                          notes: newTx.notes || null,
                        });
                        setNewTx({ date: todayISO(), amount: "", type: "EXPENSE", category: "Misc", vendor: "", notes: "" });
                        toast.toast({ title: "Transaction added", description: describeAlertRefresh(result.alertRecalc) });
                        setComposeOpen(false);
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
                    <Input placeholder="Notes" value={newTx.notes} onChange={(e) => setNewTx({ ...newTx, notes: e.target.value })} />
                    <div className="flex justify-end gap-2 md:col-span-2">
                      <Button type="button" variant="outline" onClick={() => setComposeOpen(false)}>Cancel</Button>
                      <Button type="submit">Add</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </>
          ) : undefined
        }
      />

      {!editable ? (
        <Card>
          <CardContent className="p-5 text-sm text-muted-foreground">Viewer role detected. Data remains fully visible, but create, edit, import, and delete actions are hidden.</CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader><CardTitle>Filters</CardTitle></CardHeader>
        <CardContent>
          <FiltersBar
            filters={filters}
            onChange={(next) => {
              setFilters(next);
              setPage(1);
              setBulkRemapState((prev) => ({ ...prev, from_date: next.from, to_date: next.to }));
            }}
          />
        </CardContent>
      </Card>

      {editable ? (
        <Card>
          <CardHeader><CardTitle>Bulk actions</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm text-muted-foreground">Selected rows: {selectedIds.size}</p>
              <Button
                variant="outline"
                disabled={selectedIds.size === 0 || deleteTx.isPending}
                onClick={async () => {
                  try {
                    const results = await Promise.all(Array.from(selectedIds).map((id) => deleteTx.mutateAsync(id)));
                    setSelectedIds(new Set());
                    const firstMeta = results.find((item) => item.alertRecalc)?.alertRecalc;
                    toast.toast({ title: "Selected transactions deleted", description: describeAlertRefresh(firstMeta) });
                  } catch (error) {
                    handleApiError(error, "Bulk delete failed");
                  }
                }}
              >
                Delete selected
              </Button>
              <Button variant="ghost" disabled={selectedIds.size === 0} onClick={() => setSelectedIds(new Set())}>Clear selection</Button>
            </div>

            <div className="grid gap-2 md:grid-cols-5">
              <Input
                placeholder="From category"
                data-testid="bulk-remap-from-category"
                value={bulkRemapState.from_category}
                onChange={(e) => setBulkRemapState((prev) => ({ ...prev, from_category: e.target.value }))}
              />
              <Input
                placeholder="To category"
                data-testid="bulk-remap-to-category"
                value={bulkRemapState.to_category}
                onChange={(e) => setBulkRemapState((prev) => ({ ...prev, to_category: e.target.value }))}
              />
              <Input
                type="date"
                value={bulkRemapState.from_date}
                onChange={(e) => setBulkRemapState((prev) => ({ ...prev, from_date: e.target.value }))}
              />
              <Input
                type="date"
                value={bulkRemapState.to_date}
                onChange={(e) => setBulkRemapState((prev) => ({ ...prev, to_date: e.target.value }))}
              />
              <Button
                data-testid="bulk-remap-submit"
                disabled={!bulkRemapState.from_category || !bulkRemapState.to_category || bulkRemap.isPending}
                onClick={async () => {
                  try {
                    const result = await bulkRemap.mutateAsync({
                      org_id: orgId,
                      from_category: bulkRemapState.from_category,
                      to_category: bulkRemapState.to_category,
                      from_date: bulkRemapState.from_date || undefined,
                      to_date: bulkRemapState.to_date || undefined,
                    });
                    const refreshText = describeAlertRefresh(result.alertRecalc);
                    toast.toast({
                      title: "Bulk remap applied",
                      description: refreshText ? `Updated ${result.updated_count} rows. ${refreshText}` : `Updated ${result.updated_count} rows`,
                    });
                  } catch (error) {
                    handleApiError(error, "Bulk remap failed");
                  }
                }}
              >
                Remap category
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <Card>
          <CardHeader><CardTitle>Transactions</CardTitle></CardHeader>
          <CardContent>
            {data.length === 0 ? (
              <EmptyState
                eyebrow="No data"
                title="No transactions match the current filters."
                description="Adjust the date range or add data manually or via CSV import."
                actions={editable ? [{ label: "Add transaction", onClick: () => setComposeOpen(true) }] : []}
              />
            ) : (
              <>
                <div className="rounded-2xl border border-border">
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
                  <div ref={parentRef} className="h-[520px] overflow-auto">
                    <div style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: "relative" }}>
                      {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                        const row = rows[virtualRow.index];
                        return (
                          <div key={row.id} className="absolute left-0 top-0 w-full border-b" style={{ transform: `translateY(${virtualRow.start}px)` }}>
                            <table className="w-full table-fixed text-sm">
                              <tbody>
                                <tr>
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
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">{total.toLocaleString()} records</p>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
                    <span className="text-sm">Page {page}</span>
                    <Button variant="outline" size="sm" disabled={page * pageSize >= total} onClick={() => setPage((p) => p + 1)}>Next</Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Category spend breakdown</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {categoryBreakdown.length === 0 ? (
                <p className="text-sm text-muted-foreground">No expense data in current filtered result set.</p>
              ) : (
                <>
                  <ChartFrame
                    className="h-56"
                    label="Category spend breakdown chart"
                    description="Donut chart showing expense distribution by category based on current filtered transaction results."
                  >
                    <ChartCanvas className="h-56 w-full">
                      {({ width, height }) => {
                        const radiusBase = Math.max(40, Math.min(width, height) / 2 - 12);
                        return (
                          <PieChart width={width} height={height}>
                        <Pie
                          data={categoryBreakdown}
                          dataKey="value"
                          nameKey="category"
                          cx="50%"
                          cy="50%"
                          innerRadius={Math.max(28, radiusBase * 0.6)}
                          outerRadius={Math.max(40, radiusBase)}
                          paddingAngle={2}
                          onClick={(entry) => {
                            if (!entry?.category) return;
                            setFilters((prev) => ({ ...prev, category: String(entry.category) }));
                            setPage(1);
                          }}
                        >
                          {categoryBreakdown.map((row, idx) => (
                            <Cell key={row.category} fill={categoryColors[idx % categoryColors.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(v: number) => formatMoney(v)} />
                          </PieChart>
                        );
                      }}
                    </ChartCanvas>
                  </ChartFrame>
                  <div className="space-y-2">
                    {categoryBreakdown.map((row, idx) => (
                      <button
                        key={row.category}
                        type="button"
                        className="flex w-full items-center justify-between rounded-xl border border-border/60 px-3 py-2 text-sm transition hover:bg-muted"
                        onClick={() => {
                          setFilters((prev) => ({ ...prev, category: row.category === "Other" ? "" : row.category }));
                          setPage(1);
                        }}
                      >
                        <span className="flex items-center gap-2">
                          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: categoryColors[idx % categoryColors.length] }} />
                          {row.category}
                        </span>
                        <span className="tabular-nums text-muted-foreground">{formatMoney(row.value)}</span>
                      </button>
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">Based on current filtered results.</p>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Import history</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {importHistory.data?.items?.length ? (
                importHistory.data.items.map((item) => (
                  <div key={item.id} className="rounded-[20px] border border-border/70 bg-card/70 p-4 text-sm">
                    <p className="font-medium">{item.file_name}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {item.status} | rows {item.total_rows} | inserted {item.inserted_count} | duplicates {item.duplicate_count} | errors {item.error_count}
                      {item.mapping_profile_id ? ` | profile ${item.mapping_profile_id.slice(0, 8)}` : ""}
                    </p>
                    <Button
                      variant="ghost"
                      className="mt-3 px-0"
                      onClick={async () => {
                        try {
                          const blob = await downloadImportErrors(item.id, orgId);
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = `import-errors-${item.id}.csv`;
                          a.click();
                          URL.revokeObjectURL(url);
                        } catch (error) {
                          handleApiError(error, "Error download failed");
                        }
                      }}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Download errors
                    </Button>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No imports yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={Boolean(editingRow)} onOpenChange={(open) => !open && setEditingRow(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit transaction</DialogTitle>
            <DialogDescription>Update a single row without leaving the ledger.</DialogDescription>
          </DialogHeader>
          {editingRow ? (
            <form
              className="grid gap-3 md:grid-cols-2"
              onSubmit={async (e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                try {
                  const result = await updateTx.mutateAsync({
                    id: editingRow.id,
                    payload: {
                      date: String(fd.get("date")),
                      amount: String(fd.get("amount")),
                      category: String(fd.get("category")),
                      vendor: String(fd.get("vendor") || ""),
                      notes: String(fd.get("notes") || ""),
                    },
                  });
                  toast.toast({ title: "Updated", description: describeAlertRefresh(result.alertRecalc) });
                  setEditingRow(null);
                } catch (error) {
                  handleApiError(error, "Update failed");
                }
              }}
            >
              <Input name="date" type="date" defaultValue={editingRow.date} />
              <Input name="amount" defaultValue={editingRow.amount} />
              <Input name="category" defaultValue={editingRow.category} />
              <Input name="vendor" defaultValue={editingRow.vendor || ""} />
              <Input name="notes" defaultValue={editingRow.notes || ""} className="md:col-span-2" />
              <div className="flex justify-end gap-2 md:col-span-2">
                <Button type="button" variant="outline" onClick={() => setEditingRow(null)}>Cancel</Button>
                <Button type="submit">Save</Button>
              </div>
            </form>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
