# 02 — Web to Flutter Mapping

> **Phase 1 — Mobile Migration Audit**
> Generated: 2026-05-13 | Status: Complete

---

## Screen Mapping Table

### Auth & Onboarding Screens

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 1 | `/login` | LoginPage | `/login` | LoginScreen | `POST /api/auth/login`, `GET /api/auth/google/config`, `POST /api/auth/google/verify` | Full-screen, biometric login option, Google Sign-In button |
| 2 | `/register` | RegisterPage | `/register` | RegisterScreen | `POST /api/auth/register` | Full-screen, terms checkbox, password strength indicator |
| 3 | `/forgot-password` | ForgotPasswordPage | `/forgot-password` | ForgotPasswordScreen | `POST /api/auth/forgot-password` | Simple email input + CTA. Note: API is stub only |
| 4 | `/reset-password` | ResetPasswordPage | `/reset-password` | ResetPasswordScreen | `POST /api/auth/reset-password-direct` | New password + confirm fields |
| 5 | `/onboarding` | OnboardingPage | `/onboarding` | OnboardingScreen | `POST /api/auth/onboarding` | Multi-step wizard: current score, target score, exam date, study time, weak skills. Swipeable cards on mobile |

### Core Learning Screens

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 6 | `/dashboard` | DashboardPage (22KB) | `/` (home) | DashboardScreen | `GET /api/dashboard/overview`, `GET /api/progress/history` | Bottom nav home tab. Cards: score overview, streak, weak skills, roadmap progress, recent activity |
| 7 | `/placement-test` | PlacementTestPage | `/placement-test` | PlacementTestScreen | `GET /api/diagnostic/questions`, `POST /api/diagnostic/submit` | Full-screen runner, auto-navigate after onboarding |
| 8 | `/practice` | PracticePage (36KB) | `/practice` | PracticeScreen | `GET /api/toeic/summary`, `GET /api/toeic/recommendations` | Bottom nav tab. Part grid, difficulty picker, question count selector |
| 9 | `/practice/runner` | PracticeRunnerPage (59KB) | `/practice/runner` | PracticeRunnerScreen | `GET /api/toeic/runner/part/{part}`, `GET /api/toeic/runner/mixed`, `POST /api/attempts/practice` | **Most complex screen.** Full-screen, swipe between questions, audio player, timer, flag toggle, progress bar |
| 10 | `/practice/summary` | PracticeSummaryPage (45KB) | `/practice/summary` | PracticeSummaryScreen | `GET /api/attempts/practice/{id}` | Score card, skill breakdown chart, part breakdown, per-question review list |

### Mock Test / Mini Test / Weekly Check

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 11 | `/mock-test` | MockTestPage (28KB) | `/mock-test` | MockTestScreen | `GET /api/toeic/summary` | Test catalog: mini tests + full tests, pro badge, test selector |
| 12 | `/mock-test/runner` | MockTestRunnerPage (43KB) | `/mock-test/runner` | MockTestRunnerScreen | `GET /api/toeic/runner/minitest`, `GET /api/toeic/runner/fulltest`, `POST /api/attempts/mock-test` | Full-screen runner, 2-hour timer for full test, section tabs (Listening/Reading), question navigator |
| 13 | `/mock-test/result` | MockTestResultPage (24KB) | `/mock-test/result` | MockTestResultScreen | `GET /api/attempts/mock-test/{id}` | Score card (Listening + Reading + Total), accuracy chart, per-question breakdown |
| 14 | `/mini-test/result` | MockTestResultPage (reused) | `/mini-test/result` | MockTestResultScreen (reused) | Same as above | Same component, different title |
| 15 | `/full-test/result` | MockTestResultPage (reused) | `/full-test/result` | MockTestResultScreen (reused) | Same as above | Same component, different title |
| 16 | `/weekly-check/runner` | MockTestRunnerPage (reused) | `/weekly-check/runner` | WeeklyCheckRunnerScreen | `GET /api/weekly-check/current`, `POST /api/weekly-check/submit` | Pro-only. Uses same runner UI but different data source |
| 17 | `/weekly-check/result` | MockTestResultPage (reused) | `/weekly-check/result` | WeeklyCheckResultScreen | `GET /api/weekly-check/result/{id}` | Same result UI |

### Progress & Analytics

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 18 | `/progress` | ProgressPage (30KB) | `/progress` | ProgressScreen | `GET /api/progress/summary` | Bottom nav tab. Charts: accuracy trend, weekly activity, skill radar, part stats table, recent attempts list |
| 19 | `/roadmap` | RoadmapPage (19KB) | `/roadmap` | RoadmapScreen | `GET /api/roadmap/current`, `GET /api/roadmap/evidence`, `POST /api/roadmap/generate` | Week timeline, expandable week cards, suggested sets with practice links, start/complete week buttons |

### Review Center

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 20 | `/review` | ReviewPage (64KB) | `/review` | ReviewScreen | `GET /api/review/items`, `GET /api/review/summary`, notes/highlights/bookmarks CRUD | **Second most complex screen.** Filter tabs (wrong/bookmarked/noted), per-question review cards with expand/collapse, note editor, highlight viewer |

### Flashcards & Vocabulary

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 21 | `/flashcards` | FlashcardPage (29KB) | `/flashcards` | FlashcardScreen | `GET /api/flashcards/topics`, `GET /api/flashcards/topics/{code}/cards`, `POST /api/tts/flashcard` | Topic grid, flip-card animation, TTS pronunciation, swipe navigation |

### Settings & Account

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 22 | `/settings` | SettingsPage (50KB) | `/settings` | SettingsScreen | Auth profile + learning settings + preferences + notifications + danger zone APIs | Tabbed sections: Profile, Learning, Preferences, Notifications, Danger Zone. Mobile-native form inputs |

### Payment & Pro

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 23 | `/pricing` | PricingPage (19KB) | `/pricing` | PricingScreen | `POST /api/payments/create-pro-order`, `GET /api/subscription/current` | Plan cards, price comparison, PayOS QR in WebView or deep-link |
| 24 | `/payment-success` | PaymentSuccessPage | `/payment-success` | PaymentSuccessScreen | `GET /api/payments/status/{code}` | Success confirmation + redirect to dashboard |
| 25 | `/payment-cancel` | PaymentCancelPage | `/payment-cancel` | PaymentCancelScreen | N/A | Cancel message + retry CTA |

### Marketing (Mobile-Adapted)

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 26 | `/` | LandingPage (24KB) | N/A | N/A | N/A | **Skip for mobile.** App opens directly to Login or Dashboard. Landing page is web-only. |

### Voice Reader (Deferred)

| # | Web Route | Web Page/Component | Flutter Route | Flutter Page | Required API | Mobile UX Notes |
|---|-----------|-------------------|---------------|-------------|-------------|-----------------|
| 27 | `/voice-reader` | VoiceReaderPage | `/voice-reader` (later) | VoiceReaderScreen | `POST /api/tts/tts`, `GET /api/tts/voices` | Uses browser SpeechSynthesis on web. Mobile: use `flutter_tts` or the TTS API. Lower priority. |

---

## Bottom Navigation Mapping

| Tab | Icon | Flutter Route | Primary Screen |
|-----|------|--------------|----------------|
| **Home** | 🏠 | `/` | DashboardScreen |
| **Practice** | 📝 | `/practice` | PracticeScreen |
| **Progress** | 📊 | `/progress` | ProgressScreen |
| **Review** | 🔄 | `/review` | ReviewScreen |
| **More** | ☰ | `/more` | MoreScreen (Settings, Flashcards, Roadmap, Pricing) |

---

## Navigation Flow Comparison

### Web: Sidebar Navigation
```
DashboardLayout → Sidebar (always visible on desktop)
  ├── Dashboard
  ├── Placement Test
  ├── Practice
  ├── Mock Test
  ├── Flashcards
  ├── Roadmap
  ├── Progress
  ├── Review
  └── Settings
```

### Flutter: Bottom Nav + Stack Navigation
```
BottomNavigation → 5 tabs
  ├── Home (Dashboard)
  │   └── push → PlacementTest, MockTest, WeeklyCheck
  ├── Practice
  │   └── push → PracticeRunner → PracticeSummary
  ├── Progress
  │   └── push → Roadmap (detail)
  ├── Review
  │   └── push → ReviewDetail, PracticeRunner (review-focus)
  └── More
      ├── push → Settings
      ├── push → Flashcards
      ├── push → Pricing
      ├── push → MockTest
      └── push → Roadmap
```

---

## Screens NOT Needed in Flutter

| Web Screen | Reason |
|-----------|--------|
| LandingPage (`/`) | Marketing page, web-only. App opens to Login/Dashboard |
| NotFoundPage (`*`) | Flutter uses named routes, no 404 page needed |
| Voice Reader (Phase 1) | Defer to Phase 3. Low priority feature |

---

## Component Reuse Strategy

| Web Component | Flutter Widget | Notes |
|--------------|---------------|-------|
| `DashboardLayout` (sidebar + header) | `Scaffold` + `BottomNavigationBar` | Complete redesign for mobile |
| `PracticeRunnerPage` question renderer | `QuestionCard` widget | Core reusable widget for practice/mocktest/review |
| `UserAvatar` | `CircleAvatar` with fallback | Simple port |
| `SelectionTranslator` | Long-press context menu | Mobile-native interaction |
| `ChatPanel` (AI Tutor) | `ChatScreen` or bottom sheet | FAB button to open chat overlay |
