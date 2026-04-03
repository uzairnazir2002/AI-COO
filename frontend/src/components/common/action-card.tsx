"use client";

export function ActionCard({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="rounded-[22px] border border-border/70 bg-card/70 p-4">
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-2 text-xs leading-5 text-muted-foreground">{description}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

