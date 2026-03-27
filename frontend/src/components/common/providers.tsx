"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";

import { GlobalApiFeedback } from "@/components/common/global-api-feedback";
import { Toaster } from "@/components/common/toaster";
import { createQueryClient } from "@/lib/query/queryClient";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => createQueryClient());
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={client}>
        {children}
        <GlobalApiFeedback />
        <Toaster />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
