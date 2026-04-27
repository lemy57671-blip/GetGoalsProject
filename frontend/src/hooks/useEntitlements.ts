import { useEffect, useMemo, useState } from "react";

import {
  subscriptionService,
  type EntitlementsResponse,
} from "@src/services/subscriptionService";

type EntitlementFeatures = EntitlementsResponse["features"];
export type EntitlementFeatureKey = keyof EntitlementFeatures;

const freeEntitlements: EntitlementsResponse = {
  plan: "free",
  isPro: false,
  expiresAt: null,
  features: {
    aiChatUnlimited: false,
    mockTestUnlimited: false,
    analyticsAdvanced: false,
    roadmapAdvanced: false,
    reviewNotebook: false,
    freeQuotaEnabled: true,
  },
};

export function useEntitlements() {
  const [entitlements, setEntitlements] =
    useState<EntitlementsResponse>(freeEntitlements);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const data = await subscriptionService.getEntitlements();
        if (cancelled) return;
        setEntitlements(data);
        setError("");
      } catch (err) {
        if (cancelled) return;
        setEntitlements(freeEntitlements);
        setError(
          err instanceof Error
            ? err.message
            : "Khong tai duoc quyen truy cap.",
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();

    const handleUpgrade = () => {
      setLoading(true);
      void load();
    };

    window.addEventListener("getgoals:pro-upgraded", handleUpgrade);
    window.addEventListener("storage", handleUpgrade);

    return () => {
      cancelled = true;
      window.removeEventListener("getgoals:pro-upgraded", handleUpgrade);
      window.removeEventListener("storage", handleUpgrade);
    };
  }, []);

  const hasFeature = useMemo(
    () => (feature: EntitlementFeatureKey) =>
      Boolean(entitlements.features?.[feature]),
    [entitlements.features],
  );

  return {
    entitlements,
    loading,
    error,
    isPro: entitlements.isPro,
    hasFeature,
  };
}
