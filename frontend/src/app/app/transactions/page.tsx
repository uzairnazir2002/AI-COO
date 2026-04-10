"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { type TxFilters } from "@/components/common/filters-bar";
import { SectionHeader } from "@/components/common/section-header";
import { RowActionMenu } from "@/components/data-surface/row-action-menu";
import { useToast } from "@/components/common/use-toast";
import { TabNav } from "@/components/layout/tab-nav";
import { Panel, PanelBody } from "@/components/layout/panel";
import { StatusStrip } from "@/components/layout/status-strip";
import { SuccessStateCard } from "@/components/states/success-state-card";
import { chartPalette } from "@/components/charts/theme";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { canEdit } from "@/lib/auth/rbac";
import { buildCategoryBreakdown } from "@/lib/utils/chart";
import { formatDate, formatMoney, startOfMonthISO, todayISO } from "@/lib/utils/format";
import { useAppStore } from "@/store/appStore";
import type { Transaction } from "@/types/domain";
import { TransactionsWorkspaceContainer } from "@/features/transactions/containers/transactions-workspace-container";
import { CreateTransactionDialog } from "@/features/transactions/panels/create-transaction-dialog";
import { EditTransactionDialog } from "@/features/transactions/panels/edit-transaction-dialog";
import { TransactionsImportDialog } from "@/features/transactions/panels/transactions-import-dialog";
import { autoDetectMapping, csvFields, csvMaxBytes, type CsvMapping, type CsvRawRow, mappingToApiPayload, parseCsvContent } from "@/features/transactions/services/csv";
import { loadSavedTransactionViews, persistActiveTransactionView, persistSavedTransactionViews, type SavedTransactionView } from "@/features/transactions/services/saved-views";
import { useBudgets } from "@/features/budgets/hooks";
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

export default function TransactionsPage() {
  const router = useRouter();
  const role = useAppStore((s) => s.orgs.find((o) => o.org_id === s.selectedOrgId)?.role);
  const orgId = useAppStore((s) => s.selectedOrgId);
  const selectedLocationId = useAppStore((s) => s.selectedLocationId);
  const editable = canEdit(role);
  const toast = useToast();

  const [filters, setFilters] = useState<TxFilters>({ from: startOfMonthISO(), to: todayISO(), type: "", category: "", q: "" });
  const [savedViews, setSavedViews] = useState<SavedTransactionView[]>([]);
  const [activeSavedViewId, setActiveSavedViewId] = useState("");
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [workspaceTab, setWorkspaceTab] = useState<"transactions" | "budgets" | "imports">("transactions");
  const [activeTxId, setActiveTxId] = useState<string | null>(null);
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
  const [hasImportedOnce, setHasImportedOnce] = useState(false);
  const [bulkRemapState, setBulkRemapState] = useState({ from_category: "", to_category: "", from_date: filters.from, to_date: filters.to });

  const pageSize = 100;
  const budgetPeriod = `${filters.from.slice(0, 7)}-01`;
  const query = useTransactions({ ...filters, page, page_size: pageSize });
  const budgetPreview = useBudgets(budgetPeriod, "EXPENSE", true);
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
  const activeTransaction = data.find((item) => item.id === activeTxId) ?? null;

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
        enableHiding: false,
        header: () =>
          editable ? (
            <input
              aria-label="Select all rows"
              type="checkbox"
              checked={data.length > 0 && selectedIds.size === data.length}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => setSelectedIds(e.target.checked ? new Set(data.map((row) => row.id)) : new Set())}
            />
          ) : null,
        cell: ({ row }) =>
          editable ? (
            <input
              aria-label={`Select ${row.original.id}`}
              type="checkbox"
              checked={selectedIds.has(row.original.id)}
              onClick={(e) => e.stopPropagation()}
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
        cell: ({ row }) =>
          editable ? (
            <RowActionMenu
              triggerAriaLabel={`Actions for transaction ${row.original.id}`}
              actions={[
                {
                  id: "edit",
                  label: "Edit",
                  onSelect: () => setEditingRow(row.original),
                },
                {
                  id: "delete",
                  label: "Delete",
                  onSelect: () => {
                    void (async () => {
                      try {
                        const result = await deleteTx.mutateAsync(row.original.id);
                        toast.toast({ title: "Deleted", description: describeAlertRefresh(result.alertRecalc) });
                      } catch (error) {
                        handleApiError(error, "Delete failed");
                      }
                    })();
                  },
                },
              ]}
            />
          ) : null,
      }),
    ],
    [data, deleteTx, describeAlertRefresh, editable, handleApiError, selectedIds, toast],
  );
  const csvStep = !csvFile ? 1 : requiredMissing.length > 0 ? 2 : !csvPreview ? 3 : 4;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const searchParams = new URLSearchParams(window.location.search);
    const action = searchParams.get("action");
    const tab = searchParams.get("tab");
    if (tab === "transactions" || tab === "budgets" || tab === "imports") {
      setWorkspaceTab(tab);
      router.replace("/app/transactions");
    }
    if (action === "compose") {
      setComposeOpen(true);
      router.replace("/app/transactions");
    }
    if (action === "import") {
      setImportOpen(true);
      router.replace("/app/transactions");
    }
  }, [router]);

  useEffect(() => {
    if (typeof window === "undefined" || !orgId) return;
    setHasImportedOnce(window.localStorage.getItem(`tx-import-success-${orgId}`) === "1");
  }, [orgId]);

  useEffect(() => {
    if (typeof window === "undefined" || !orgId) return;
    const { views, activeViewId } = loadSavedTransactionViews(orgId);
    setSavedViews(views);
    setActiveSavedViewId(activeViewId);
    const activeView = views.find((view) => view.id === activeViewId);
    if (activeView) {
      setFilters(activeView.filters);
      setPage(1);
      setBulkRemapState((prev) => ({
        ...prev,
        from_date: activeView.filters.from,
        to_date: activeView.filters.to,
      }));
    }
  }, [orgId]);

  useEffect(() => {
    if (!orgId) return;
    persistSavedTransactionViews(orgId, savedViews);
  }, [orgId, savedViews]);

  useEffect(() => {
    if (!orgId) return;
    persistActiveTransactionView(orgId, activeSavedViewId);
  }, [activeSavedViewId, orgId]);

  const applyFilters = useCallback((next: TxFilters) => {
    setFilters(next);
    setPage(1);
    setBulkRemapState((prev) => ({ ...prev, from_date: next.from, to_date: next.to }));
  }, []);

  const handleSelectSavedView = useCallback((viewId: string) => {
    setActiveSavedViewId(viewId);
    if (!viewId) return;
    const selected = savedViews.find((view) => view.id === viewId);
    if (!selected) return;
    applyFilters(selected.filters);
  }, [applyFilters, savedViews]);

  const handleSaveSavedView = useCallback((name: string, existingId?: string) => {
    if (!orgId) return;
    const trimmed = name.trim();
    if (!trimmed) return;
    if (existingId) {
      setSavedViews((prev) =>
        prev.map((view) =>
          view.id === existingId
            ? { ...view, name: trimmed, filters: { ...filters } }
            : view,
        ),
      );
      setActiveSavedViewId(existingId);
      toast.toast({ title: "Saved view updated" });
      return;
    }
    const newView: SavedTransactionView = {
      id: `view-${Date.now().toString(36)}`,
      name: trimmed,
      filters: { ...filters },
    };
    setSavedViews((prev) => [newView, ...prev]);
    setActiveSavedViewId(newView.id);
    toast.toast({ title: "Saved view created" });
  }, [filters, orgId, toast]);

  const handleDeleteSavedView = useCallback((viewId: string) => {
    setSavedViews((prev) => prev.filter((view) => view.id !== viewId));
    setActiveSavedViewId((prev) => (prev === viewId ? "" : prev));
    toast.toast({ title: "Saved view deleted" });
  }, [toast]);

  const handleDeleteSelected = useCallback(async () => {
    try {
      const results = await Promise.all(Array.from(selectedIds).map((id) => deleteTx.mutateAsync(id)));
      setSelectedIds(new Set());
      const firstMeta = results.find((item) => item.alertRecalc)?.alertRecalc;
      toast.toast({ title: "Selected transactions deleted", description: describeAlertRefresh(firstMeta) });
    } catch (error) {
      handleApiError(error, "Bulk delete failed");
    }
  }, [deleteTx, describeAlertRefresh, handleApiError, selectedIds, toast]);

  const handleBulkRemap = useCallback(async () => {
    if (!orgId) return;
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
  }, [bulkRemap, bulkRemapState, describeAlertRefresh, handleApiError, orgId, toast]);

  const handleDownloadImportErrors = useCallback(async (importId: string) => {
    if (!orgId) return;
    try {
      const blob = await downloadImportErrors(importId, orgId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `import-errors-${importId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      handleApiError(error, "Error download failed");
    }
  }, [handleApiError, orgId]);

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
        eyebrow="Money"
        title="Transactions"
        description="Unified workspace for transactions, budgets, and imports."
        scopeChips={[
          role ? `Role: ${role}` : "Role: unknown",
          selectedLocationId ? "Location scope: filtered" : "Location scope: all",
          `${filters.from} to ${filters.to}`,
        ]}
        actions={
          editable ? (
            <>
              <TransactionsImportDialog
                open={importOpen}
                onOpenChange={setImportOpen}
                csvStep={csvStep}
                onFileSelected={handleCsvFile}
                csvHeaders={csvHeaders}
                selectedProfileId={selectedProfileId}
                onSelectProfile={(value) => {
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
                profiles={profiles.data || []}
                profileName={profileName}
                setProfileName={setProfileName}
                profileShared={profileShared}
                setProfileShared={setProfileShared}
                onDeleteProfile={async () => {
                  if (!selectedProfileId) return;
                  try {
                    await deleteProfile.mutateAsync(selectedProfileId);
                    setSelectedProfileId("");
                    toast.toast({ title: "Profile deleted" });
                  } catch (error) {
                    handleApiError(error, "Delete profile failed");
                  }
                }}
                onSaveProfile={async () => {
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
                saveProfilePending={createProfile.isPending || updateProfile.isPending}
                deleteProfilePending={deleteProfile.isPending}
                mapping={mapping}
                setMapping={setMapping}
                requiredMissing={requiredMissing}
                selectedProfileExists={Boolean(selectedProfile)}
                previewRows={mappedPreviewRows}
                csvPreview={csvPreview}
                localDupes={localDupes}
                csvBusy={csvBusy}
                onPreview={async () => {
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
                onConfirm={async () => {
                  if (!csvFile || requiredMissing.length > 0) return;
                  if (!csvPreview) {
                    toast.toast({ title: "Preview required", description: "Run Preview Import before confirming.", variant: "warning" });
                    return;
                  }
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
                    setHasImportedOnce(true);
                    if (typeof window !== "undefined") {
                      window.localStorage.setItem(`tx-import-success-${orgId}`, "1");
                    }
                    setImportOpen(false);
                  } catch (error) {
                    handleApiError(error, "CSV import failed");
                  } finally {
                    setCsvBusy(false);
                  }
                }}
              />

              <CreateTransactionDialog
                open={composeOpen}
                onOpenChange={setComposeOpen}
                draft={newTx}
                onDraftChange={setNewTx}
                onSubmit={async () => {
                  try {
                    const amount = Number(newTx.amount);
                    if (!Number.isFinite(amount)) {
                      throw new ApiError("Amount must be a valid number (example: 12.34).", 400);
                    }
                    if (!newTx.date) {
                      throw new ApiError("Date is required.", 400);
                    }
                    if (!newTx.category.trim()) {
                      throw new ApiError("Category is required.", 400);
                    }
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
              />
            </>
          ) : undefined
        }
      />

      {!editable ? (
        <Panel>
          <PanelBody className="text-sm text-muted-foreground">Viewer role detected. Data remains fully visible, but create, edit, import, and delete actions are hidden.</PanelBody>
        </Panel>
      ) : null}

      <StatusStrip
        items={[
          { label: "Rows", value: total.toLocaleString(), tone: "neutral" },
          { label: "Selected", value: selectedIds.size.toString(), tone: selectedIds.size > 0 ? "warning" : "neutral" },
          { label: "Imports", value: String(importHistory.data?.total ?? 0), tone: "neutral" },
        ]}
      />

      {hasImportedOnce ? (
        <SuccessStateCard
          title="Import pipeline is active"
          description="CSV import has completed successfully for this organization. Mapping profiles and import history are now available for repeat operations."
        />
      ) : null}

      <TabNav
        active={workspaceTab}
        onChange={(value) => setWorkspaceTab(value as "transactions" | "budgets" | "imports")}
        items={[
          { id: "transactions", label: "Transactions" },
          { id: "budgets", label: "Budgets" },
          { id: "imports", label: "Imports" },
        ]}
      />

      {workspaceTab === "transactions" ? (
        <TransactionsWorkspaceContainer
          editable={editable}
          filters={filters}
          onFiltersChange={applyFilters}
          savedViews={savedViews.map((view) => ({ id: view.id, name: view.name }))}
          activeSavedViewId={activeSavedViewId}
          onSelectSavedView={handleSelectSavedView}
          onSaveSavedView={handleSaveSavedView}
          onDeleteSavedView={handleDeleteSavedView}
          selectedCount={selectedIds.size}
          deletePending={deleteTx.isPending}
          remapPending={bulkRemap.isPending}
          bulkRemapState={bulkRemapState}
          onBulkRemapStateChange={setBulkRemapState}
          onDeleteSelected={handleDeleteSelected}
          onClearSelection={() => setSelectedIds(new Set())}
          onRemap={handleBulkRemap}
          total={total}
          isFetching={query.isFetching}
          csvBusy={csvBusy}
          page={page}
          pageSize={pageSize}
          onPrevPage={() => setPage((p) => p - 1)}
          onNextPage={() => setPage((p) => p + 1)}
          data={data}
          columns={columns}
          onRowSelect={setActiveTxId}
          onAddTransaction={() => setComposeOpen(true)}
          activeTransaction={activeTransaction}
          onEditTransaction={setEditingRow}
          categoryBreakdown={categoryBreakdown}
          categoryColors={categoryColors}
          onSelectCategory={(category) => {
            setFilters((prev) => ({ ...prev, category }));
            setPage(1);
          }}
          importHistoryItems={importHistory.data?.items ?? []}
          onDownloadErrors={handleDownloadImportErrors}
        />
      ) : null}

      {workspaceTab === "budgets" ? (
        <Panel>
          <PanelBody className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold">Budget snapshot ({budgetPeriod})</p>
                <p className="text-xs text-muted-foreground">Direct budget management remains available on the full Budgets route.</p>
              </div>
              <Button asChild variant="outline">
                <Link href="/app/budgets">Open full budgets workspace</Link>
              </Button>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <BudgetTile label="Budget rows" value={String(budgetPreview.data?.length ?? 0)} />
              <BudgetTile label="Current period" value={budgetPeriod} />
              <BudgetTile label="Filtered range" value={`${filters.from} to ${filters.to}`} />
            </div>
          </PanelBody>
        </Panel>
      ) : null}

      {workspaceTab === "imports" ? (
        <Panel>
          <PanelBody className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold">Import center</p>
                <p className="text-xs text-muted-foreground">Guided CSV flow, mapping profiles, and import issue recovery.</p>
              </div>
              <Button onClick={() => setImportOpen(true)}>Start import</Button>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <BudgetTile label="Latest imports" value={String(importHistory.data?.total ?? 0)} />
              <BudgetTile label="Detected local duplicates" value={String(localDupes)} />
              <BudgetTile label="Missing required mappings" value={String(requiredMissing.length)} />
            </div>
            <div className="space-y-2">
              {(importHistory.data?.items ?? []).slice(0, 6).map((item) => (
                <div key={item.id} className="rounded-xl border border-border/70 bg-card/70 px-3 py-2 text-sm">
                  <p className="font-medium">{item.file_name || item.id}</p>
                  <p className="text-xs text-muted-foreground">
                    inserted {item.inserted_count} · status {item.status}
                  </p>
                </div>
              ))}
            </div>
          </PanelBody>
        </Panel>
      ) : null}

      <EditTransactionDialog
        transaction={editingRow}
        onClose={() => setEditingRow(null)}
        onSave={async (payload) => {
          if (!editingRow) return;
          try {
            const amount = Number(payload.amount);
            if (!Number.isFinite(amount)) {
              throw new ApiError("Amount must be a valid number (example: 12.34).", 400);
            }
            if (!payload.date) {
              throw new ApiError("Date is required.", 400);
            }
            if (!payload.category.trim()) {
              throw new ApiError("Category is required.", 400);
            }
            const result = await updateTx.mutateAsync({
              id: editingRow.id,
              payload,
            });
            toast.toast({ title: "Updated", description: describeAlertRefresh(result.alertRecalc) });
            setEditingRow(null);
          } catch (error) {
            handleApiError(error, "Update failed");
          }
        }}
      />
    </div>
  );
}

function BudgetTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card/70 px-4 py-3">
      <p className="text-xs uppercase text-muted-foreground">{label}</p>
      <p className="mt-2 text-base font-semibold">{value}</p>
    </div>
  );
}
