"use client";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils/cn";

export function DetailDrawer({
  open,
  title,
  onClose,
  children,
  className,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen) onClose(); }}>
      <DialogContent
        data-testid="detail-drawer"
        className={cn(
          "left-0 right-0 top-auto bottom-0 h-[82dvh] w-full max-w-none translate-x-0 translate-y-0 rounded-t-3xl border-t border-border p-6",
          "md:left-auto md:bottom-auto md:top-0 md:h-dvh md:max-w-xl md:rounded-none md:border-l md:border-t-0",
          className,
        )}
      >
        <DialogHeader className="mb-4 flex-row items-center justify-between space-y-0">
          <DialogTitle className="text-xl font-semibold">{title}</DialogTitle>
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}
