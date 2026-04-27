import { apiRequest } from "@src/services/apiClient";

export type CurrentSubscription = {
  plan: "free" | "pro" | string;
  planExpiredAt?: string | null;
};

export type EntitlementsResponse = {
  plan: "free" | "pro";
  isPro: boolean;
  expiresAt?: string | null;
  features: {
    aiChatUnlimited: boolean;
    mockTestUnlimited: boolean;
    analyticsAdvanced: boolean;
    roadmapAdvanced: boolean;
    reviewNotebook: boolean;
    freeQuotaEnabled: boolean;
  };
};

export const subscriptionService = {
  async getCurrent(): Promise<CurrentSubscription> {
    return apiRequest<CurrentSubscription>("/api/subscription/current", {
      auth: true,
    });
  },

  async getEntitlements(): Promise<EntitlementsResponse> {
    return apiRequest<EntitlementsResponse>("/api/me/entitlements", {
      auth: true,
    });
  },
};
