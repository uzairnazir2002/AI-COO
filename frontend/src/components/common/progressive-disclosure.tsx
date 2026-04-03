"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

export function ProgressiveDisclosure({
  title = "Show more",
  hideLabel = "Show less",
  defaultOpen = false,
  className,
  children,
}: {
  title?: string;
  hideLabel?: string;
  defaultOpen?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={cn("space-y-3", className)}>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? (
          <>
            {hideLabel}
            <ChevronUp className="ml-2 h-4 w-4" />
          </>
        ) : (
          <>
            {title}
            <ChevronDown className="ml-2 h-4 w-4" />
          </>
        )}
      </Button>
      {open ? <div className="space-y-4">{children}</div> : null}
    </section>
  );
}

