import type { ReactNode } from "react";

import { ThemeProvider } from "@/components/theme-provider";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { LanguageProvider } from "@src/contexts/LanguageContext";

type AppProvidersProps = {
  children: ReactNode;
};

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      <LanguageProvider>
        {children}
        <Sonner richColors position="top-right" />
      </LanguageProvider>
    </ThemeProvider>
  );
}
