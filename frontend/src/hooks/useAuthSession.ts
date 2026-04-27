import { useCallback, useEffect, useState } from "react";
import {
  AUTH_TOKEN_STORAGE_KEY,
  ApiError,
  getAuthToken,
} from "@src/services/apiClient";
import { authService, type AuthUser } from "@src/services/authService";

function normalizePlan(plan?: string) {
  const normalized = plan?.trim().toLowerCase();

  if (!normalized) {
    return "Free Plan";
  }

  if (normalized === "pro") {
    return "Pro Plan";
  }

  if (normalized === "free") {
    return "Free Plan";
  }

  return `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)} Plan`;
}

function buildInitials(user: AuthUser | null) {
  const source = user?.name?.trim() || user?.email?.trim() || "";

  if (!source) {
    return "GG";
  }

  const parts = source.split(/\s+/).filter(Boolean);

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0]}${parts[parts.length - 1]?.[0] ?? ""}`.toUpperCase();
}

export function useAuthSession() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [hasToken, setHasToken] = useState(() => Boolean(getAuthToken()));
  const [isLoading, setIsLoading] = useState(() => Boolean(getAuthToken()));

  const refreshSession = useCallback(async () => {
    const token = getAuthToken();
    const nextHasToken = Boolean(token);

    setHasToken(nextHasToken);

    if (!nextHasToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);

    try {
      const sessionUser = await authService.me();
      setUser(sessionUser);
    } catch (error) {
      if (
        error instanceof ApiError &&
        (error.status === 401 || error.status === 403)
      ) {
        authService.logout();
        setHasToken(false);
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    setHasToken(false);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (!event.key || event.key === AUTH_TOKEN_STORAGE_KEY) {
        void refreshSession();
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [refreshSession]);

  return {
    user,
    hasToken,
    isLoading,
    isAuthenticated: hasToken || Boolean(user),
    displayName: user?.name?.trim() || user?.email?.trim() || "Tài khoản của bạn",
    planLabel: normalizePlan(user?.plan),
    initials: buildInitials(user),
    logout,
    refreshSession,
  };
}
