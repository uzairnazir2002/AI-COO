"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

type Action = {
  label: string;
  href?: string;
  onClick?: () => void;
  variant?: "default" | "outline" | "ghost";
};

export function EmptyState({
  eyebrow,
  title,
  description,
  actions = [],
  className,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: Action[];
  className?: string;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("glass-panel panel-edge rounded-[28px] p-6 md:p-8", className)}
    >
      <div className="bg-grid rounded-[22px] border border-border/60 p-6">
        {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.28em] text-primary">{eyebrow}</p> : null}
        <h2 className="mt-3 max-w-xl text-2xl font-semibold text-balance md:text-3xl">{title}</h2>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground md:text-base">{description}</p>
        {actions.length > 0 ? (
          <div className="mt-6 flex flex-wrap gap-3">
            {actions.map((action) =>
              action.href ? (
                <Button key={action.label} asChild variant={action.variant ?? "default"}>
                  <Link href={action.href}>
                    {action.label} <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              ) : (
                <Button key={action.label} variant={action.variant ?? "default"} onClick={action.onClick}>
                  {action.label} <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              ),
            )}
          </div>
        ) : null}
      </div>
    </motion.section>
  );
}
