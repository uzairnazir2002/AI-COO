"use client";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
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
        className={cn(
          "left-auto right-0 top-0 h-dvh w-full max-w-xl translate-x-0 translate-y-0 rounded-none border-l border-border p-6",
          className,
        )}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">{title}</h2>
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </div>
        {children}
      </DialogContent>
    </Dialog>
  );
}
