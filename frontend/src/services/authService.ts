type LoginInput = {
  email: string;
  password: string;
  remember?: boolean;
};

type RegisterInput = {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
  agreeTerms: boolean;
};

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
  avatar_url?: string;
  picture?: string;
  photoURL?: string;
  image?: string;
  googlePicture?: string;
  provider?: string;
  plan?: string;
  planExpiredAt?: string | null;
  onboardingCompleted?: boolean;
  currentScore?: number | null;
  targetScore?: number | null;
  examDate?: string | null;
  studyMinutesPerDay?: number | null;
  weakSkills?: string[];
};

type AuthResult = {
  user: AuthUser;
  nextPath: string;
};

type ForgotPasswordInput = {
  email: string;
};

type ForgotPasswordResult = {
  email: string;
  message: string;
};

type ResetPasswordDirectInput = {
  emailOrUsername: string;
  newPassword: string;
  confirmPassword: string;
};

type AuthResponse = {
  token: string;
  user: AuthUser;
};

type GoogleAuthConfig = {
  enabled: boolean;
  clientId: string;
};

type GoogleVerifyInput = {
  credential: string;
  device?: string;
};

type CompleteOnboardingInput = {
  currentScore?: number | null;
  targetScore?: number | null;
  examDate?: string | null;
  studyMinutesPerDay?: number | null;
  weakSkills?: string[];
};

type UpdateProfileInput = {
  name: string;
};

type UpdateLearningSettingsInput = CompleteOnboardingInput;

type ChangePasswordInput = {
  currentPassword: string;
  newPassword: string;
};

import {
  AUTH_TOKEN_STORAGE_KEY,
  apiRequest,
  clearAuthToken,
  getAuthToken,
  setAuthToken,
} from "@src/services/apiClient";

function buildNextPath(user: AuthUser, fallback: string) {
  return user.onboardingCompleted ? "/dashboard" : fallback;
}

let googleConfigPromise: Promise<GoogleAuthConfig> | null = null;

const authCacheKeys = [
  AUTH_TOKEN_STORAGE_KEY,
  "access_token",
  "token",
  "refresh_token",
  "getgoals.user",
  "getgoals.profile",
  "getgoals.session",
  "getgoals.authUser",
  "auth_user",
  "user",
  "profile",
];

let logoutRedirectInProgress = false;

function clearAuthCache() {
  clearAuthToken();

  if (typeof window === "undefined") return;

  for (const key of authCacheKeys) {
    window.localStorage.removeItem(key);
    window.sessionStorage.removeItem(key);
  }
}

function redirectAfterLogout(redirectTo: string) {
  if (typeof window === "undefined") return;

  logoutRedirectInProgress = true;
  window.location.replace(redirectTo);
}

export const authService = {
  async login({ email, password, remember = true }: LoginInput): Promise<AuthResult> {
    const result = await apiRequest<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, remember }),
    });

    setAuthToken(result.token);
    return {
      user: result.user,
      nextPath: buildNextPath(result.user, "/onboarding"),
    };
  },

  async register({ name, email, password }: RegisterInput): Promise<AuthResult> {
    const result = await apiRequest<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });

    setAuthToken(result.token);
    return {
      user: result.user,
      nextPath: "/onboarding",
    };
  },

  async getGoogleConfig(): Promise<GoogleAuthConfig> {
    if (!googleConfigPromise) {
      googleConfigPromise = apiRequest<GoogleAuthConfig>("/api/auth/google/config").catch(
        (error) => {
          googleConfigPromise = null;
          throw error;
        },
      );
    }

    return googleConfigPromise;
  },

  async loginWithGoogle({
    credential,
    device = "web",
  }: GoogleVerifyInput): Promise<AuthResult> {
    const result = await apiRequest<AuthResponse>("/api/auth/google/verify", {
      method: "POST",
      body: JSON.stringify({ credential, device }),
    });

    setAuthToken(result.token);
    return {
      user: result.user,
      nextPath: buildNextPath(result.user, "/onboarding"),
    };
  },

  async forgotPassword({
    email,
  }: ForgotPasswordInput): Promise<ForgotPasswordResult> {
    const result = await apiRequest<{ message: string }>("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ emailOrUsername: email }),
    });

    return {
      email,
      message: result.message,
    };
  },

  async resetPasswordDirect(payload: ResetPasswordDirectInput): Promise<{ message: string }> {
    return apiRequest<{ message: string }>("/api/auth/reset-password-direct", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async me(): Promise<AuthUser> {
    return apiRequest<AuthUser>("/api/auth/me", { auth: true });
  },

  async updateProfile(payload: UpdateProfileInput): Promise<AuthUser> {
    const result = await apiRequest<{ user: AuthUser }>("/api/auth/profile", {
      method: "PATCH",
      auth: true,
      body: JSON.stringify(payload),
    });

    return result.user;
  },

  async updateLearningSettings(
    payload: UpdateLearningSettingsInput,
  ): Promise<AuthUser> {
    const result = await apiRequest<{ user: AuthUser }>(
      "/api/auth/learning-settings",
      {
        method: "PATCH",
        auth: true,
        body: JSON.stringify(payload),
      },
    );

    return result.user;
  },

  async completeOnboarding(payload: CompleteOnboardingInput): Promise<AuthResult> {
    const result = await apiRequest<{ user: AuthUser }>("/api/auth/onboarding", {
      method: "POST",
      auth: true,
      body: JSON.stringify(payload),
    });

    return {
      user: result.user,
      nextPath: "/dashboard",
    };
  },

  async changePassword(payload: ChangePasswordInput): Promise<{ message: string }> {
    return apiRequest<{ message: string }>("/api/auth/change-password", {
      method: "POST",
      auth: true,
      body: JSON.stringify(payload),
    });
  },

  clearSession() {
    clearAuthCache();
  },

  logout(redirectTo = "/") {
    clearAuthCache();
    redirectAfterLogout(redirectTo);
  },

  isLogoutRedirectInProgress() {
    return logoutRedirectInProgress;
  },

  isAuthenticated() {
    return Boolean(getAuthToken());
  },
};
