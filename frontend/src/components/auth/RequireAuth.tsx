import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { useAuthSession } from "@src/hooks/useAuthSession";

type RequireAuthProps = {
  children: ReactNode;
  redirectIfOnboardedTo?: string;
};

export function RequireAuth({
  children,
  redirectIfOnboardedTo,
}: RequireAuthProps) {
  const location = useLocation();
  const { user, isAuthenticated, isLoading } = useAuthSession();

  if (isLoading) {
    return (
      <div className="grid min-h-screen place-items-center bg-background px-4">
        <div className="flex items-center gap-3 rounded-2xl border bg-card px-5 py-4 text-sm text-muted-foreground shadow-sm">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          Đang kiểm tra phiên đăng nhập...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    );
  }

  if (redirectIfOnboardedTo && user?.onboardingCompleted) {
    return <Navigate to={redirectIfOnboardedTo} replace />;
  }

  return <>{children}</>;
}
