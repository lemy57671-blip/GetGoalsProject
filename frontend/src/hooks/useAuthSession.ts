import { useCallback, useEffect, useState } from "react";
import {
  AUTH_TOKEN_STORAGE_KEY,
  ApiError,
  getAuthToken,
} from "@src/services/apiClient";
import { authService, type AuthUser } from "@src/services/authService";
import { buildUserInitials, getUserAvatarUrl } from "@src/utils/userDisplay";

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
        authService.clearSession();
        setHasToken(false);
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setHasToken(false);
    setIsLoading(false);
    authService.logout("/");
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
    initials: buildUserInitials(user?.name, user?.email),
    avatarUrl: getUserAvatarUrl(user),
    logout,
    refreshSession,
  };
}
