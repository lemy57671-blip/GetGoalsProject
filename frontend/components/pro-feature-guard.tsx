import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Crown, Loader2, Lock, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  useEntitlements,
  type EntitlementFeatureKey,
} from "@src/hooks/useEntitlements";

type ProFeatureGuardProps = {
  feature: EntitlementFeatureKey;
  children: ReactNode;
  title?: string;
  description?: string;
  compact?: boolean;
};

export function ProFeatureGuard({
  feature,
  children,
  title = "Tinh nang nay danh cho Pro",
  description = "Nang cap de mo khoa trai nghiem hoc nang cao, AI Tutor va bao cao chi tiet.",
  compact = false,
}: ProFeatureGuardProps) {
  const { hasFeature, loading } = useEntitlements();

  if (loading) {
    return (
      <Card
        className={`border-primary/15 bg-gradient-to-br from-primary/5 to-background ${
          compact ? "rounded-2xl" : "rounded-3xl"
        }`}
      >
        <CardContent
          className={`flex items-center gap-3 ${compact ? "p-5" : "p-8"}`}
        >
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <div>
            <div className="font-semibold text-foreground">
              Dang kiem tra quyen truy cap
            </div>
            <div className="text-sm text-muted-foreground">
              Vui long cho mot chut...
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (hasFeature(feature)) {
    return <>{children}</>;
  }

  return (
    <Card
      className={`overflow-hidden border-primary/20 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.18),_transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] ${
        compact ? "rounded-2xl" : "rounded-3xl"
      }`}
    >
      <CardContent className={compact ? "p-5" : "p-8"}>
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge className="gap-1 bg-primary text-primary-foreground">
                <Crown className="h-3.5 w-3.5" />
                Pro
              </Badge>
              <Badge
                variant="outline"
                className="gap-1 border-primary/30 text-primary"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Locked
              </Badge>
            </div>

            <div className="flex items-start gap-3">
              <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Lock className="h-5 w-5" />
              </div>

              <div>
                <h3
                  className={`${compact ? "text-lg" : "text-2xl"} font-bold text-foreground`}
                >
                  {title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {description}
                </p>
              </div>
            </div>
          </div>

          <div className="flex shrink-0 flex-col gap-3 sm:flex-row">
            <Button asChild className="gap-2">
              <Link to="/pricing">
                <Crown className="h-4 w-4" />
                Nang cap Pro
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/dashboard">Ve dashboard</Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
