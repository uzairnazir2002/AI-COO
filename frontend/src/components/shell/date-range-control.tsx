"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { CalendarRange } from "lucide-react";

import { Input } from "@/components/ui/input";
import { useAppStore } from "@/store/appStore";

export function DateRangeControl() {
  const range = useAppStore((s) => s.globalDateRange);
  const setRange = useAppStore((s) => s.setGlobalDateRange);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const from = searchParams.get("from");
    const to = searchParams.get("to");
    if (from && to && (from !== range.from || to !== range.to)) {
      setRange({ from, to });
    }
  }, [searchParams, range.from, range.to, setRange]);

  function updateRange(next: { from: string; to: string }) {
    setRange(next);
    const params = new URLSearchParams(searchParams.toString());
    params.set("from", next.from);
    params.set("to", next.to);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-border bg-card/70 px-3 py-2">
      <CalendarRange className="h-4 w-4 text-muted-foreground" />
      <Input
        aria-label="Global from date"
        type="date"
        value={range.from}
        onChange={(event) => updateRange({ ...range, from: event.target.value })}
        className="h-8 w-auto border-0 bg-transparent px-1"
      />
      <span className="text-xs text-muted-foreground">to</span>
      <Input
        aria-label="Global to date"
        type="date"
        value={range.to}
        onChange={(event) => updateRange({ ...range, to: event.target.value })}
        className="h-8 w-auto border-0 bg-transparent px-1"
      />
    </div>
  );
}
