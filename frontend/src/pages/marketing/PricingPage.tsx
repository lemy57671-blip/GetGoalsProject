"use client";

import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { UpgradeProModal } from "@/components/upgrade-pro-modal";
import { freeFeatures, pricingFaqs, proFeatures } from "@src/data/pricing";
import { useAuthSession } from "@src/hooks/useAuthSession";
import { type ProPlanCode } from "@src/services/paymentsService";
import { subscriptionService } from "@src/services/subscriptionService";
import {
  ArrowLeft,
  BarChart3,
  Brain,
  Check,
  CheckCircle2,
  Crown,
  Loader2,
  Star,
  Target,
  X,
  Zap,
} from "lucide-react";

type BillingCycle = "monthly" | "quarterly" | "yearly";

type PlanOption = {
  planCode: ProPlanCode;
  planName: string;
  amount: number;
  subtitle: string;
  badge?: string;
};

const planMap: Record<BillingCycle, PlanOption> = {
  monthly: {
    planCode: "PRO_MONTHLY",
    planName: "Pro tháng",
    amount: 99000,
    subtitle: "99.000đ / tháng",
  },
  quarterly: {
    planCode: "PRO_QUARTERLY",
    planName: "Pro quý",
    amount: 249000,
    subtitle: "249.000đ / 3 tháng",
    badge: "Tiết kiệm",
  },
  yearly: {
    planCode: "PRO_YEARLY",
    planName: "Pro năm",
    amount: 899000,
    subtitle: "899.000đ / năm",
    badge: "Tốt nhất",
  },
};

function formatCurrency(value: number) {
  return `${value.toLocaleString("vi-VN")}đ`;
}

function formatExpiry(value: string | null) {
  if (!value) return "";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return date.toLocaleString("vi-VN");
}

export function PricingPage() {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);
  const [showUpgradeSuccess, setShowUpgradeSuccess] = useState(false);
  const [isPro, setIsPro] = useState(false);
  const [proExpiresAt, setProExpiresAt] = useState<string | null>(null);
  const [checkingSubscription, setCheckingSubscription] = useState(false);
  const [subscriptionError, setSubscriptionError] = useState("");
  const { displayName, isAuthenticated, isLoading, user } = useAuthSession();

  const currentPlan = useMemo(() => planMap[billingCycle], [billingCycle]);
  const dashboardTarget =
    user?.onboardingCompleted === false ? "/onboarding" : "/dashboard";
  const freePlanTarget = isAuthenticated ? dashboardTarget : "/register";

  async function refreshEntitlements() {
    if (!isAuthenticated) {
      setIsPro(false);
      setProExpiresAt(null);
      setCheckingSubscription(false);
      return;
    }

    try {
      setCheckingSubscription(true);
      setSubscriptionError("");
      const entitlements = await subscriptionService.getEntitlements();
      setIsPro(Boolean(entitlements.isPro));
      setProExpiresAt(entitlements.expiresAt || null);
    } catch (error) {
      setIsPro(false);
      setProExpiresAt(null);
      setSubscriptionError(
        error instanceof Error
          ? error.message
          : "Không kiểm tra được gói hiện tại.",
      );
    } finally {
      setCheckingSubscription(false);
    }
  }

  useEffect(() => {
    void refreshEntitlements();
  }, [isAuthenticated]);

  useEffect(() => {
    const showSuccess = () => {
      setShowUpgradeSuccess(true);
      void refreshEntitlements();

      try {
        window.localStorage.removeItem("getgoals_pro_upgrade_success");
      } catch {
        // Ignore storage failures; the payment status has already been handled.
      }
    };

    const stored = window.localStorage.getItem("getgoals_pro_upgrade_success");
    if (stored) {
      showSuccess();
    }

    const onUpgraded = () => showSuccess();

    window.addEventListener("getgoals:pro-upgraded", onUpgraded);
    return () => window.removeEventListener("getgoals:pro-upgraded", onUpgraded);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {showUpgradeSuccess ? (
        <div className="fixed inset-x-0 top-4 z-[100] flex justify-center px-4">
          <div className="w-full max-w-xl rounded-2xl border border-green-500/30 bg-green-500/10 px-5 py-4 shadow-lg backdrop-blur">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5 text-green-600" />
                <div>
                  <div className="font-semibold">
                    Đã nâng cấp lên GetGoals Pro
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Tài khoản của bạn đã được kích hoạt Pro thành công.
                  </div>
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button asChild size="sm">
                  <Link to={dashboardTarget}>Thoát</Link>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowUpgradeSuccess(false)}
                >
                  Đóng
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <nav className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur">
        <div className="relative h-16">
          <div className="absolute left-0 top-1/2 -translate-y-1/2 pl-4">
            <Button asChild variant="outline" size="sm" className="gap-2 rounded-xl">
              <Link to={dashboardTarget}>
                <ArrowLeft className="h-4 w-4" />
                Thoát
              </Link>
            </Button>
          </div>

          <div className="container mx-auto flex h-16 items-center justify-between px-4">
            <Link to="/" className="ml-24 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                <Target className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold">GetGoals</span>
            </Link>

            <div className="flex items-center gap-4">
              {isAuthenticated ? (
                <div className="hidden text-sm text-muted-foreground sm:block">
                  Xin chào,{" "}
                  <span className="font-medium text-foreground">
                    {displayName}
                  </span>
                </div>
              ) : (
                <>
                  <Link to="/login">
                    <Button variant="ghost">Đăng nhập</Button>
                  </Link>
                  <Link to="/register">
                    <Button>Đăng ký miễn phí</Button>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      <section className="relative overflow-hidden border-b bg-gradient-to-b from-primary/5 via-background to-background">
        <div className="container mx-auto px-4 pb-12 pt-10 md:pb-14">
          <div className="mx-auto max-w-3xl text-center">
            <Badge className="mb-4 border-0 bg-primary/10 text-primary">
              Bảng giá
            </Badge>
            <h1 className="mb-4 text-balance text-4xl font-bold md:text-5xl">
              Chọn gói phù hợp với bạn
            </h1>
            <p className="mx-auto max-w-2xl text-balance text-xl text-muted-foreground">
              Thanh toán được xác nhận nhanh để kích hoạt Pro cho tài khoản của
              bạn.
            </p>

            {isPro ? (
              <div className="mx-auto mt-6 max-w-2xl rounded-2xl border border-green-500/30 bg-green-500/10 p-4 text-left">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 text-green-600" />
                  <div>
                    <div className="font-semibold text-green-700">
                      Bạn đang là thành viên Pro
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Bạn không thể đăng ký thêm gói mới cho tới khi gói hiện
                      tại hết hạn.
                    </div>
                    {proExpiresAt ? (
                      <div className="mt-1 text-sm">
                        Hết hạn vào: <strong>{formatExpiry(proExpiresAt)}</strong>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}

            {subscriptionError ? (
              <div className="mx-auto mt-6 max-w-2xl rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-left text-sm text-destructive">
                {subscriptionError}
              </div>
            ) : null}

            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              {Object.entries(planMap).map(([cycle, plan]) => (
                <button
                  key={cycle}
                  type="button"
                  onClick={() => setBillingCycle(cycle as BillingCycle)}
                  className={`flex items-center gap-2 rounded-lg px-4 py-2 transition-all ${
                    billingCycle === cycle
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted hover:bg-muted-foreground/20"
                  }`}
                >
                  {cycle === "monthly"
                    ? "Hàng tháng"
                    : cycle === "quarterly"
                      ? "Hàng quý"
                      : "Hàng năm"}
                  {plan.badge ? (
                    <Badge className="bg-green-500 text-white">
                      {plan.badge}
                    </Badge>
                  ) : null}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="pb-20 pt-12">
        <div className="container mx-auto px-4">
          <div className="mx-auto grid max-w-4xl gap-8 md:grid-cols-2">
            <Card className="relative">
              <CardHeader className="pb-2 text-center">
                <CardTitle className="text-2xl">Free</CardTitle>
                <CardDescription>Dành cho người mới bắt đầu</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="text-center">
                  <span className="text-4xl font-bold">0đ</span>
                  <span className="text-muted-foreground">/tháng</span>
                </div>

                <Button variant="outline" className="w-full" size="lg" asChild>
                  <Link to={freePlanTarget}>
                    {isAuthenticated
                      ? "Quay lại lộ trình học"
                      : "Bắt đầu miễn phí"}
                  </Link>
                </Button>

                <div className="space-y-3">
                  {freeFeatures.map((feature) => (
                    <div key={feature.text} className="flex items-center gap-3">
                      {feature.included ? (
                        <Check className="h-5 w-5 shrink-0 text-green-500" />
                      ) : (
                        <X className="h-5 w-5 shrink-0 text-muted-foreground" />
                      )}
                      <span className={feature.included ? "" : "text-muted-foreground"}>
                        {feature.text}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="relative border-2 border-primary shadow-lg">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                <Badge className="gap-1 bg-primary px-4 py-1">
                  <Star className="h-3 w-3 fill-current" />
                  Phổ biến nhất
                </Badge>
              </div>
              <CardHeader className="pb-2 text-center">
                <CardTitle className="flex items-center justify-center gap-2 text-2xl">
                  <Crown className="h-6 w-6 text-yellow-500" />
                  Pro
                </CardTitle>
                <CardDescription>
                  Dành cho người nghiêm túc luyện thi
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="text-center">
                  <span className="text-4xl font-bold">
                    {formatCurrency(currentPlan.amount)}
                  </span>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {currentPlan.subtitle}
                  </p>
                </div>

                {isLoading || checkingSubscription ? (
                  <Button className="w-full gap-2" size="lg" disabled>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Đang kiểm tra gói...
                  </Button>
                ) : isPro ? (
                  <div className="space-y-3">
                    <Button className="w-full gap-2" size="lg" disabled>
                      <CheckCircle2 className="h-4 w-4" />
                      Bạn đang dùng Pro
                    </Button>
                    <Button asChild variant="outline" className="w-full">
                      <Link to={dashboardTarget}>Về dashboard</Link>
                    </Button>
                  </div>
                ) : isAuthenticated ? (
                  <Button
                    className="w-full gap-2"
                    size="lg"
                    onClick={() => setUpgradeModalOpen(true)}
                  >
                    <Zap className="h-4 w-4" />
                    Thanh toán {currentPlan.planName}
                  </Button>
                ) : (
                  <Button className="w-full gap-2" size="lg" asChild>
                    <Link to={`/login?plan=${currentPlan.planCode}`}>
                      <Zap className="h-4 w-4" />
                      Đăng nhập để thanh toán
                    </Link>
                  </Button>
                )}

                <p className="text-center text-sm text-muted-foreground">
                  {isPro
                    ? "Bạn cần chờ đến khi gói hiện tại hết hạn để đăng ký lại."
                    : "Tạo QR đúng theo gói bạn đang chọn qua FastAPI và PayOS."}
                </p>

                <div className="space-y-3">
                  {proFeatures.map((feature) => (
                    <div key={feature.text} className="flex items-center gap-3">
                      <Check className="h-5 w-5 shrink-0 text-green-500" />
                      <span>{feature.text}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <UpgradeProModal
        open={upgradeModalOpen}
        onOpenChange={setUpgradeModalOpen}
        planCode={currentPlan.planCode}
        planName={currentPlan.planName}
        amount={currentPlan.amount}
      />

      <section className="bg-muted/30 py-20">
        <div className="container mx-auto px-4">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-bold">Tại sao chọn Pro?</h2>
            <p className="mx-auto max-w-2xl text-muted-foreground">
              Học TOEIC hiệu quả hơn với AI Coach và lộ trình cá nhân hóa.
            </p>
          </div>

          <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-3">
            <Card className="text-center">
              <CardContent className="pt-6">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
                  <Brain className="h-6 w-6 text-primary" />
                </div>
                <h3 className="mb-2 font-semibold">AI Coach 24/7</h3>
                <p className="text-sm text-muted-foreground">
                  Hỏi đáp bất cứ lúc nào, được giải thích chi tiết bằng tiếng
                  Việt.
                </p>
              </CardContent>
            </Card>

            <Card className="text-center">
              <CardContent className="pt-6">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
                  <Target className="h-6 w-6 text-primary" />
                </div>
                <h3 className="mb-2 font-semibold">Roadmap cá nhân hóa</h3>
                <p className="text-sm text-muted-foreground">
                  Lộ trình học được tạo riêng theo mục tiêu và thời gian của
                  bạn.
                </p>
              </CardContent>
            </Card>

            <Card className="text-center">
              <CardContent className="pt-6">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
                  <BarChart3 className="h-6 w-6 text-primary" />
                </div>
                <h3 className="mb-2 font-semibold">Phân tích chi tiết</h3>
                <p className="text-sm text-muted-foreground">
                  Báo cáo tiến độ hằng tuần và phân tích điểm yếu để cải thiện.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-bold">Câu hỏi thường gặp</h2>
          </div>

          <div className="mx-auto max-w-2xl">
            <Accordion type="single" collapsible className="space-y-4">
              {pricingFaqs.map((faq, index) => (
                <AccordionItem
                  key={faq.q}
                  value={`item-${index}`}
                  className="rounded-xl border bg-card px-6"
                >
                  <AccordionTrigger className="text-left hover:no-underline">
                    {faq.q}
                  </AccordionTrigger>
                  <AccordionContent className="text-muted-foreground">
                    {faq.a}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </div>
      </section>
    </div>
  );
}
