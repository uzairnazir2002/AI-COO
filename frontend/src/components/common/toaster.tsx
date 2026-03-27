"use client";

import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";

import { useToastStore } from "@/components/common/use-toast";

const iconByVariant = {
  default: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
} as const;

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const remove = useToastStore((s) => s.remove);

  useEffect(() => {
    const timers = toasts.map((toast) => {
      const ms = Math.max(0, toast.dismissAt - Date.now());
      return window.setTimeout(() => remove(toast.id), ms);
    });
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [remove, toasts]);

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[120] flex w-[min(92vw,380px)] flex-col gap-3">
      <AnimatePresence>
        {toasts.map((toast) => {
          const Icon = iconByVariant[toast.variant ?? "default"];
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 16, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.98 }}
              className="pointer-events-auto rounded-[22px] border border-border/70 bg-card/95 p-4 shadow-2xl backdrop-blur-xl"
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5 rounded-xl bg-primary/10 p-2 text-primary">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold">{toast.title}</p>
                  {toast.description ? <p className="mt-1 text-xs leading-5 text-muted-foreground">{toast.description}</p> : null}
                </div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
