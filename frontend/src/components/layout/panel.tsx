import { cn } from "@/lib/utils/cn";

export function Panel({ className, children }: { className?: string; children: React.ReactNode }) {
  return <section className={cn("rounded-3xl border border-border/70 bg-card/85 shadow-sm", className)}>{children}</section>;
}

export function PanelHeader({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("border-b border-border/60 px-5 py-4", className)}>{children}</div>;
}

export function PanelBody({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("px-5 py-4", className)}>{children}</div>;
}

export function PanelFooter({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("border-t border-border/60 px-5 py-4", className)}>{children}</div>;
}
