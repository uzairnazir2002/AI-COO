"use client";

import { cn } from "@/lib/utils/cn";

export function PageContainer({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("page-container", className)}>{children}</div>;
}

