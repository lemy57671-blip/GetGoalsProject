import type { ReactNode } from "react";

import { ThemeProvider } from "@/components/theme-provider";
import { Toaster as Sonner } from "@/components/ui/sonner";

type AppProvidersProps = {
  children: ReactNode;
};

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      {children}
      <Sonner richColors position="top-right" />
    </ThemeProvider>
  );
}
