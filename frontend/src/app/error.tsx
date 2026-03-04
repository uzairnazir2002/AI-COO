"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto mt-20 max-w-xl rounded-lg border border-border bg-card p-6 text-center">
      <h2 className="text-xl font-semibold">Something went wrong</h2>
      <p className="mt-2 text-sm text-muted-foreground">Please try again. If it persists, report this issue.</p>
      <div className="mt-4 flex justify-center gap-3">
        <Button onClick={() => reset()}>Try again</Button>
        <Button variant="outline" onClick={() => window.location.href = "mailto:support@example.com"}>Report issue</Button>
      </div>
    </div>
  );
}
