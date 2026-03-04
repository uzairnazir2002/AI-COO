"use client";

import { AnimatePresence, motion } from "framer-motion";

import { useToastStore } from "@/components/common/use-toast";
import { cn } from "@/lib/utils/cn";

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const remove = useToastStore((s) => s.remove);

  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className={cn(
              "pointer-events-auto rounded-md border bg-card p-3 shadow-trust",
              toast.variant === "danger" && "border-danger/30",
            )}
            onAnimationEnd={() => {
              setTimeout(() => remove(toast.id), 2500);
            }}
          >
            <p className="text-sm font-medium">{toast.title}</p>
            {toast.description ? <p className="text-xs text-muted-foreground">{toast.description}</p> : null}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
