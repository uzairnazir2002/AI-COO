"use client";

import { cn } from "@/lib/utils/cn";

export function PageActionBar({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("flex flex-wrap items-center gap-2", className)}>{children}</div>;
}

