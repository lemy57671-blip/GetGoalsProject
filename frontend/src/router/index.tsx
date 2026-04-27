import { createBrowserRouter } from "react-router-dom";

import { AuthLayout } from "@src/layouts/AuthLayout";
import { DashboardLayout } from "@src/layouts/DashboardLayout";
import { MarketingLayout } from "@src/layouts/MarketingLayout";
import { RequireAuth } from "@src/components/auth/RequireAuth";
import { ForgotPasswordPage } from "@src/pages/auth/ForgotPasswordPage";
import { LoginPage } from "@src/pages/auth/LoginPage";
import { RegisterPage } from "@src/pages/auth/RegisterPage";
import { ResetPasswordPage } from "@src/pages/auth/ResetPasswordPage";
import { DashboardPage } from "@src/pages/dashboard/DashboardPage";
import { LandingPage } from "@src/pages/marketing/LandingPage";
import { PaymentCancelPage } from "@src/pages/marketing/PaymentCancelPage";
import { PaymentSuccessPage } from "@src/pages/marketing/PaymentSuccessPage";
import { PricingPage } from "@src/pages/marketing/PricingPage";
import { OnboardingPage } from "@src/pages/onboarding/OnboardingPage";
import { MockTestPage } from "@src/pages/mock-test/MockTestPage";
import { MockTestRunnerPage } from "@src/pages/mock-test/MockTestRunnerPage";
import { MockTestResultPage } from "@src/pages/mock-test/MockTestResultPage";
import { PlacementTestPage } from "@src/pages/placement/PlacementTestPage";
import { PracticePage } from "@src/pages/practice/PracticePage";
import { PracticeRunnerPage } from "@src/pages/practice/PracticeRunnerPage";
import { PracticeSummaryPage } from "@src/pages/practice/PracticeSummaryPage";
import { ProgressPage } from "@src/pages/progress/ProgressPage";
import { ReviewPage } from "@src/pages/review/ReviewPage";
import { RoadmapPage } from "@src/pages/roadmap/RoadmapPage";
import { SettingsPage } from "@src/pages/settings/SettingsPage";
import { NotFoundPage } from "@src/pages/NotFoundPage";

export const router = createBrowserRouter([
  {
    element: <MarketingLayout />,
    children: [
      {
        path: "/",
        element: <LandingPage />,
      },
      {
        path: "/pricing",
        element: <PricingPage />,
      },
      {
        path: "/onboarding",
        element: (
          <RequireAuth redirectIfOnboardedTo="/dashboard">
            <OnboardingPage />
          </RequireAuth>
        ),
      },
      {
        path: "/payment-success",
        element: <PaymentSuccessPage />,
      },
      {
        path: "/payment-cancel",
        element: <PaymentCancelPage />,
      },
    ],
  },
  {
    element: <AuthLayout />,
    children: [
      {
        path: "/login",
        element: <LoginPage />,
      },
      {
        path: "/register",
        element: <RegisterPage />,
      },
      {
        path: "/forgot-password",
        element: <ForgotPasswordPage />,
      },
      {
        path: "/reset-password",
        element: <ResetPasswordPage />,
      },
    ],
  },
  {
    path: "/dashboard",
    element: (
      <DashboardLayout>
        <DashboardPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/placement-test",
    element: (
      <DashboardLayout>
        <PlacementTestPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/practice",
    element: (
      <DashboardLayout>
        <PracticePage />
      </DashboardLayout>
    ),
  },
  {
    path: "/practice/runner",
    element: (
      <DashboardLayout>
        <PracticeRunnerPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/practice/summary",
    element: (
      <DashboardLayout>
        <PracticeSummaryPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/mock-test",
    element: (
      <DashboardLayout>
        <MockTestPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/mock-test/runner",
    element: (
      <DashboardLayout>
        <MockTestRunnerPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/mock-test/result",
    element: (
      <DashboardLayout>
        <MockTestResultPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/mini-test/result",
    element: (
      <DashboardLayout>
        <MockTestResultPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/full-test/result",
    element: (
      <DashboardLayout>
        <MockTestResultPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/weekly-check/runner",
    element: (
      <DashboardLayout>
        <MockTestRunnerPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/weekly-check/result",
    element: (
      <DashboardLayout>
        <MockTestResultPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/progress",
    element: (
      <DashboardLayout>
        <ProgressPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/roadmap",
    element: (
      <DashboardLayout>
        <RoadmapPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/review",
    element: (
      <DashboardLayout>
        <ReviewPage />
      </DashboardLayout>
    ),
  },
  {
    path: "/settings",
    element: (
      <DashboardLayout>
        <SettingsPage />
      </DashboardLayout>
    ),
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
]);
