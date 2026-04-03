"use client";

export function InsightCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
      <p className="text-sm font-semibold">{title}</p>
      <div className="mt-2 text-xs leading-5 text-muted-foreground">{children}</div>
    </div>
  );
}

