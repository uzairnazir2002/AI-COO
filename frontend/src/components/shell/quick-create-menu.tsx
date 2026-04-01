"use client";

import { useEffect, useRef, useState } from "react";
import { Plus, ReceiptText, Upload, FilePlus2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

type ActionItem = {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick: () => void;
};

export function QuickCreateMenu({
  onAddTransaction,
  onImportCsv,
  onGenerateReport,
  className,
}: {
  onAddTransaction: () => void;
  onImportCsv: () => void;
  onGenerateReport: () => void;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEscape);
    };
  }, []);

  const actions: ActionItem[] = [
    { key: "add", label: "Add transaction", icon: ReceiptText, onClick: onAddTransaction },
    { key: "import", label: "Import CSV", icon: Upload, onClick: onImportCsv },
    { key: "report", label: "Generate report", icon: FilePlus2, onClick: onGenerateReport },
  ];

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <Button variant="outline" className="rounded-2xl" onClick={() => setOpen((value) => !value)} aria-label="Quick create">
        <Plus className="mr-2 h-4 w-4" />
        Quick create
      </Button>
      {open ? (
        <div className="absolute right-0 z-50 mt-2 w-56 rounded-2xl border border-border bg-card p-2 shadow-xl">
          {actions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.key}
                type="button"
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition hover:bg-muted"
                onClick={() => {
                  setOpen(false);
                  action.onClick();
                }}
              >
                <Icon className="h-4 w-4 text-primary" />
                {action.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
