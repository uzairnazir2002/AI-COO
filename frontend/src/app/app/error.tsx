"use client";

import { Button } from "@/components/ui/button";

export default function AppError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h2 className="text-lg font-semibold">Could not load this page</h2>
      <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
      <Button className="mt-4" onClick={() => reset()}>Try again</Button>
    </div>
  );
}
