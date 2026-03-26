"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import * as Dialog from "@radix-ui/react-dialog";
import { Activity, Boxes, Calculator, ChevronRight, FileText, Landmark, MessageSquare, PiggyBank, Search, Settings, Wallet, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Command = {
  id: string;
  label: string;
  keywords: string;
  icon: React.ComponentType<{ className?: string }>;
  run: () => void;
};

export function CommandPalette({
  onAddTransaction,
  onOpenInventory,
  onImportCsv,
  onGenerateReport,
}: {
  onAddTransaction?: () => void;
  onOpenInventory?: () => void;
  onImportCsv?: () => void;
  onGenerateReport?: () => void;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const commands = useMemo<Command[]>(
    () => [
      { id: "dashboard", label: "Go to Dashboard", keywords: "kpi alerts summary", icon: Landmark, run: () => router.push("/app/dashboard") },
      { id: "activity", label: "Go to Activity", keywords: "jobs workers automation outbox", icon: Activity, run: () => router.push("/app/activity") },
      { id: "transactions", label: "Go to Transactions", keywords: "ledger import csv table", icon: Wallet, run: () => router.push("/app/transactions") },
      { id: "inventory", label: "Go to Inventory", keywords: "stock items purchase orders forecast", icon: Boxes, run: () => router.push("/app/inventory") },
      { id: "budgets", label: "Go to Budgets", keywords: "budget variance planning category", icon: PiggyBank, run: () => router.push("/app/budgets") },
      { id: "forecast", label: "Go to Forecast", keywords: "runway scenario overrides", icon: Calculator, run: () => router.push("/app/forecast") },
      { id: "assistant", label: "Go to AI Chat", keywords: "assistant grounded fallback chat", icon: MessageSquare, run: () => router.push("/app/assistant") },
      { id: "reports", label: "Go to Reports", keywords: "weekly report download", icon: FileText, run: () => router.push("/app/reports") },
      { id: "settings", label: "Go to Settings", keywords: "members billing invite", icon: Settings, run: () => router.push("/app/settings") },
      ...(onAddTransaction ? [{ id: "new-tx", label: "Add transaction", keywords: "create expense revenue", icon: Wallet, run: onAddTransaction }] : []),
      ...(onOpenInventory ? [{ id: "open-inventory", label: "Open inventory", keywords: "stock events demand forecast", icon: Boxes, run: onOpenInventory }] : []),
      ...(onImportCsv ? [{ id: "import-csv", label: "Import CSV", keywords: "upload mapping preview", icon: Wallet, run: onImportCsv }] : []),
      ...(onGenerateReport ? [{ id: "generate-report", label: "Generate weekly report", keywords: "regenerate export", icon: FileText, run: onGenerateReport }] : []),
    ],
    [onAddTransaction, onGenerateReport, onImportCsv, onOpenInventory, router],
  );

  const filtered = commands.filter((command) => {
    const haystack = `${command.label} ${command.keywords}`.toLowerCase();
    return haystack.includes(query.toLowerCase());
  });

  useEffect(() => {
    setOpen(false);
    setQuery("");
  }, [pathname]);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button variant="outline" className="hidden min-w-48 justify-between md:inline-flex">
          <span className="flex items-center gap-2">
            <Search className="h-4 w-4" />
            Command menu
          </span>
          <span className="text-xs text-muted-foreground">Ctrl K</span>
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[90] bg-background/65 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-[14vh] z-[100] w-[min(92vw,720px)] -translate-x-1/2 rounded-[28px] border border-border bg-card p-4 shadow-2xl">
          <Dialog.Title className="sr-only">Command palette</Dialog.Title>
          <Dialog.Description className="sr-only">
            Search and execute navigation or quick actions across the app.
          </Dialog.Description>
          <div className="flex items-center gap-3 border-b border-border pb-3">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              aria-label="Search commands"
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search navigation and quick actions"
              className="border-0 bg-transparent px-0"
            />
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close command palette">
                <X className="h-4 w-4" />
              </Button>
            </Dialog.Close>
          </div>
          <div className="mt-3 max-h-[420px] overflow-auto">
            {filtered.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                No matching command.
              </div>
            ) : (
              filtered.map((command) => {
                const Icon = command.icon;
                return (
                  <button
                    key={command.id}
                    type="button"
                    className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left transition hover:bg-muted"
                    onClick={() => {
                      command.run();
                      setOpen(false);
                    }}
                  >
                    <div className="rounded-xl bg-primary/10 p-2 text-primary">
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="flex-1 text-sm font-medium">{command.label}</span>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </button>
                );
              })
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
