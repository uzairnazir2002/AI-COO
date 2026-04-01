"use client";

import { PageHeader } from "@/components/layout/page-header";

export function SectionHeader({
  title,
  description,
  actions,
  eyebrow,
  scopeChips,
  className,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  eyebrow?: string;
  scopeChips?: string[];
  className?: string;
}) {
  return (
    <PageHeader
      title={title}
      description={description}
      actions={actions}
      eyebrow={eyebrow}
      scopeChips={scopeChips}
      className={className}
    />
  );
}
