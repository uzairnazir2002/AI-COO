"use client";

import { cn } from "@/lib/utils/cn";

export function RightRail({
  children,
  className,
  sticky,
}: {
  children: React.ReactNode;
  className?: string;
  sticky?: boolean;
}) {
  return (
    <aside className={cn("space-y-4", sticky ? "xl:sticky xl:top-4" : "", className)}>
      {children}
    </aside>
  );
}

