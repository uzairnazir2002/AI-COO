import type { Metadata } from "next";

import "./globals.css";

import { Providers } from "@/components/common/providers";

export const metadata: Metadata = {
  title: "AI COO",
  description: "AI COO for Small Businesses",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
