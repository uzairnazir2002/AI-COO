"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function MobileBottomSheet({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen) onClose(); }}>
      <DialogContent className="left-0 right-0 top-auto bottom-0 h-[82dvh] w-full max-w-none translate-x-0 translate-y-0 rounded-t-3xl border-t border-border p-6 md:hidden">
        <DialogHeader className="mb-4 flex-row items-center justify-between space-y-0">
          <DialogTitle className="text-xl font-semibold">{title}</DialogTitle>
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}

