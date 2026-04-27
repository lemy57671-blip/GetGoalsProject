"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
import { useAuthSession } from "@src/hooks/useAuthSession";

type DashboardLayoutProps = {
  children: ReactNode;
};

function SidebarContent({ pathname }: { pathname: string }) {
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
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="mt-6 px-3">
          <p className="mb-2 px-3 text-xs font-medium uppercase text-sidebar-foreground/50">
            Học nhanh
          </p>
          <div className="space-y-1">
            {dashboardQuickActions.map((item) => (
              <Link
                key={item.label}
                to={item.href}
                className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
              >
                <item.icon className="h-4 w-4" />
                {item.label}
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
            {dashboardUpgradeBanner.title}
          </div>
          <p className="text-xs text-sidebar-foreground/60">
            {dashboardUpgradeBanner.description}
          </p>
        </Link>
      </div>
    </div>
  );
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const pathname = location.pathname;
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { displayName, initials, isAuthenticated, isLoading, logout, planLabel } =
    useAuthSession();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate("/login", { replace: true, state: { from: pathname } });
    }
  }, [isAuthenticated, isLoading, navigate, pathname]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="grid min-h-screen place-items-center bg-background px-4">
        <div className="flex items-center gap-3 rounded-2xl border bg-card px-5 py-4 text-sm text-muted-foreground shadow-sm">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          Đang kiểm tra phiên đăng nhập...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
        <SidebarContent pathname={pathname} />
      </aside>

      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-64 bg-sidebar p-0">
          <SidebarContent pathname={pathname} />
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
                  placeholder="Tìm kiếm bài học, câu hỏi..."
                  className="h-9 w-64 bg-muted/50 pl-9"
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary" />
              </Button>

              {isAuthenticated ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="flex items-center gap-2 px-2">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-primary text-sm text-primary-foreground">
                          {initials}
                        </AvatarFallback>
                      </Avatar>
                      <div className="hidden text-left md:block">
                        <p className="text-sm font-medium text-foreground">
                          {displayName}
                        </p>
                        <p className="text-xs text-muted-foreground">{planLabel}</p>
                      </div>
                      <ChevronRight className="hidden h-4 w-4 text-muted-foreground md:block" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>Tài khoản của tôi</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link to="/settings" className="flex cursor-pointer items-center">
                        <User className="mr-2 h-4 w-4" />
                        Hồ sơ
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/settings" className="flex cursor-pointer items-center">
                        <Settings className="mr-2 h-4 w-4" />
                        Cài đặt
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/pricing" className="flex cursor-pointer items-center">
                        <Crown className="mr-2 h-4 w-4" />
                        Nâng cấp Pro
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="cursor-pointer text-destructive focus:text-destructive"
                      onClick={() => {
                        logout();
                        navigate("/pricing");
                      }}
                    >
                      <LogOut className="mr-2 h-4 w-4" />
                      Đăng xuất
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : (
                <div className="flex items-center gap-2">
                  <Button variant="ghost" asChild>
                    <Link to="/login">Đăng nhập</Link>
                  </Button>
                  <Button asChild>
                    <Link to="/register">Đăng ký</Link>
                  </Button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
