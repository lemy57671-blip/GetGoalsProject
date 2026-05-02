"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  Bell,
  ChevronRight,
  Crown,
  Loader2,
  LogOut,
  Menu,
  Search,
  Settings,
  Target,
  User,
} from "lucide-react";
import {
  dashboardNavigation,
  dashboardQuickActions,
  dashboardUpgradeBanner,
} from "@src/data/dashboard";
import { useLanguage } from "@src/contexts/LanguageContext";
import { UserAvatar } from "@src/components/UserAvatar";
import { useAuthSession } from "@src/hooks/useAuthSession";
import { SelectionTranslator } from "@/components/SelectionTranslator";
import { authService } from "@src/services/authService";
import { isProtectedPath } from "@src/utils/authRoutes";
import type { TranslationKey } from "@src/i18n";

type DashboardLayoutProps = {
  children: ReactNode;
};

const navLabelKeys: Record<string, TranslationKey> = {
  "/dashboard": "nav.dashboard",
  "/placement-test": "nav.placementTest",
  "/practice": "nav.practice",
  "/mock-test": "nav.mockTest",
  "/roadmap": "nav.roadmap",
  "/progress": "nav.progress",
  "/review": "nav.review",
  "/settings": "nav.settings",
};

const quickActionLabelKeys: Record<string, TranslationKey> = {
  Listening: "nav.listening",
  Reading: "nav.reading",
  "Mini Test": "nav.miniTest",
};

function SidebarContent({
  pathname,
  t,
}: {
  pathname: string;
  t: (key: TranslationKey) => string;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-sidebar-border p-4">
        <Link to="/dashboard" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Target className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-lg font-semibold text-sidebar-foreground">
            GetGoals
          </span>
        </Link>
      </div>

      <ScrollArea className="flex-1 py-4">
        <nav className="space-y-1 px-3">
          {dashboardNavigation.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                }`}
              >
                <item.icon className="h-5 w-5" />
                {t(navLabelKeys[item.href] || "nav.dashboard")}
              </Link>
            );
          })}
        </nav>

        <div className="mt-6 px-3">
          <p className="mb-2 px-3 text-xs font-medium uppercase text-sidebar-foreground/50">
            {t("nav.quickLearning")}
          </p>

          <div className="space-y-1">
            {dashboardQuickActions.map((item) => (
              <Link
                key={item.label}
                to={item.href}
                className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
              >
                <item.icon className="h-4 w-4" />
                {t(quickActionLabelKeys[item.label] || "nav.practice")}
              </Link>
            ))}
          </div>
        </div>
      </ScrollArea>

      <div className="border-t border-sidebar-border p-3">
        <Link
          to={dashboardUpgradeBanner.href}
          className="block rounded-xl border border-primary/20 bg-gradient-to-r from-primary/10 to-primary/5 p-4"
        >
          <div className="mb-1 flex items-center gap-2 text-sm font-medium text-primary">
            <dashboardUpgradeBanner.icon className="h-4 w-4" />
            {t("nav.upgradeTitle")}
          </div>
          <p className="text-xs text-sidebar-foreground/60">
            {t("nav.upgradeDescription")}
          </p>
        </Link>
      </div>
    </div>
  );
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useLanguage();
  const pathname = location.pathname;

  const [sidebarOpen, setSidebarOpen] = useState(false);

  const {
    avatarUrl,
    displayName,
    isAuthenticated,
    isLoading,
    logout,
    planLabel,
    user,
  } = useAuthSession();

  useEffect(() => {
    if (
      !isLoading &&
      !isAuthenticated &&
      isProtectedPath(pathname) &&
      !authService.isLogoutRedirectInProgress()
    ) {
      navigate("/login", { replace: true, state: { from: pathname } });
    }
  }, [isAuthenticated, isLoading, navigate, pathname]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="grid min-h-screen place-items-center bg-background px-4">
        <div className="flex items-center gap-3 rounded-2xl border bg-card px-5 py-4 text-sm text-muted-foreground shadow-sm">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          {t("auth.checking")}
        </div>
      </div>
    );
  }

  const handleLogout = () => {
    logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
        <SidebarContent pathname={pathname} t={t} />
      </aside>

      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-64 bg-sidebar p-0">
          <SidebarContent pathname={pathname} t={t} />
        </SheetContent>
      </Sheet>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur">
          <div className="flex h-16 items-center justify-between px-4 lg:px-6">
            <div className="flex items-center gap-4">
              <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" className="lg:hidden">
                    <Menu className="h-5 w-5" />
                  </Button>
                </SheetTrigger>
              </Sheet>

              <div className="relative hidden md:block">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder={t("topbar.search")}
                  className="h-9 w-64 bg-muted/50 pl-9"
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary" />
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    className="flex items-center gap-2 px-2"
                  >
                    <UserAvatar
                      name={user?.name}
                      email={user?.email}
                      avatarUrl={avatarUrl}
                      size="sm"
                    />

                    <div className="hidden text-left md:block">
                      <p className="text-sm font-medium text-foreground">
                        {displayName}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {planLabel}
                      </p>
                    </div>

                    <ChevronRight className="hidden h-4 w-4 text-muted-foreground md:block" />
                  </Button>
                </DropdownMenuTrigger>

                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>{t("auth.myAccount")}</DropdownMenuLabel>
                  <DropdownMenuSeparator />

                  <DropdownMenuItem asChild>
                    <Link to="/settings" className="flex cursor-pointer items-center">
                      <User className="mr-2 h-4 w-4" />
                      {t("auth.profile")}
                    </Link>
                  </DropdownMenuItem>

                  <DropdownMenuItem asChild>
                    <Link to="/settings" className="flex cursor-pointer items-center">
                      <Settings className="mr-2 h-4 w-4" />
                      {t("auth.settings")}
                    </Link>
                  </DropdownMenuItem>

                  <DropdownMenuItem asChild>
                    <Link to="/pricing" className="flex cursor-pointer items-center">
                      <Crown className="mr-2 h-4 w-4" />
                      {t("auth.upgrade")}
                    </Link>
                  </DropdownMenuItem>

                  <DropdownMenuSeparator />

                  <DropdownMenuItem
                    className="cursor-pointer text-destructive focus:text-destructive"
                    onClick={handleLogout}
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    {t("auth.logout")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        <main className="p-4 lg:p-6">{children}</main>

        <SelectionTranslator />
      </div>
    </div>
  );
}