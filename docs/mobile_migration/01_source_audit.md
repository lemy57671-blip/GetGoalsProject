# 01 — Source Audit: GetGoals Codebase

> **Phase 1 — Mobile Migration Audit**
> Generated: 2026-05-13 | Status: Complete

---

## 1. Current Repository Overview

```
test/
├── backend/          ← Shared FastAPI backend (Python 3.10+)
├── frontend/         ← React web frontend (Vite + TypeScript)
├── module/           ← Supporting modules (AI translate, English reading, flashcard data)
├── .gitignore
└── (future) getgoals_mobile/  ← Flutter mobile app (Phase 2+)
```

### Tech Stack Summary

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Backend** | FastAPI 0.x, SQLAlchemy, pyodbc | Connects to SQL Server via ODBC Driver 18 |
| **Database** | SQL Server (`DataGetGoals`) | PascalCase column names with SQLAlchemy synonyms |
| **Frontend** | React 19, Vite 7, TypeScript 5.7 | TailwindCSS 4, shadcn/ui (Radix), react-router-dom 7 |
| **Auth** | JWT (HS256) via `PyJWT` + `passlib` | Bearer token, localStorage, 7-30 day expiry |
| **Payment** | PayOS (VN payment gateway) | Webhook-based payment confirmation |
| **AI/NLP** | Edge TTS, custom translator model | AI translation module in `module/aidich/` |

---

## 2. Role of `backend/`

The backend is the **single shared API server** for the entire GetGoals platform.

### Structure

```
backend/app/
├── main.py              ← FastAPI app, CORS, exception handlers, static mounts
├── api/
│   ├── router.py        ← Central router (20 route modules)
│   ├── deps/            ← Auth dependencies (get_current_user, require_pro_user)
│   └── routes/          ← 20 route files
├── core/
│   ├── config.py        ← Settings (env vars, paths, JWT keys, PayOS keys)
│   ├── security.py      ← JWT create/decode, password hashing (pbkdf2_sha256)
│   ├── errors.py        ← Custom ApiError
│   └── logging.py       ← Logging config
├── db/
│   ├── session.py       ← SQLAlchemy engine (mssql+pyodbc), SessionLocal
│   └── migrations/      ← DB migration scripts
├── models/
│   ├── entities.py      ← 24+ SQLAlchemy ORM models (706 lines)
│   └── __init__.py      ← Model re-exports
├── schemas/             ← Pydantic request/response schemas (12 files)
├── services/            ← Business logic (17 files, ~300K+ total code)
├── utils/               ← JSON helpers
└── ml_models/           ← Machine learning models directory
```

### Key Design Decisions

- **CORS**: Allows `localhost:3000`, `localhost:5173`, and configurable origins
- **Static Files**: Mounts `/toeic`, `/audio`, `/images` from `runtime/` directory
- **DB Dialect**: SQL Server with `supports_sane_rowcount = False` workaround
- **Column Naming**: DB uses PascalCase (`UserId`), Python uses snake_case with synonyms

### All Backend API Endpoints (50+)

#### Auth & User (`/api/auth/...`, `/api/me/...`, `/api/users`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | No | Register new user |
| POST | `/api/auth/login` | No | Login with email/password |
| GET | `/api/auth/me` | Yes | Get current user profile |
| PATCH | `/api/auth/profile` | Yes | Update user name |
| PATCH | `/api/auth/learning-settings` | Yes | Update learning preferences |
| POST | `/api/auth/onboarding` | Yes | Complete onboarding |
| POST | `/api/auth/change-password` | Yes | Change password |
| POST | `/api/auth/forgot-password` | No | Forgot password (stub) |
| POST | `/api/auth/reset-password-direct` | No | Direct password reset |
| GET | `/api/auth/google/config` | No | Google OAuth config |
| POST | `/api/auth/google/verify` | No | Google Sign-In verify |
| POST | `/api/auth/google/exchange` | No | Google token exchange |
| GET | `/api/me/entitlements` | Yes | User plan/feature flags |
| GET | `/api/me/profile-summary` | Yes | Learning profile summary |
| GET | `/api/users` | No | List all users (admin/debug) |

#### Dashboard (`/api/dashboard/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/dashboard/overview` | Yes | Main dashboard data + roadmap |
| GET | `/api/dashboard/summary` | No* | Course completion summary |
| GET | `/api/dashboard/courses` | No* | Enrolled courses list |
| GET | `/api/dashboard/weekly-hours` | No* | Weekly study hours chart |

> *Uses `userId` query param, not JWT auth

#### TOEIC Practice (`/api/toeic/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/toeic/summary` | No | Question bank summary by part |
| GET | `/api/toeic/import-status` | No | DB import status |
| GET | `/api/toeic/recommendations` | Yes | AI-based practice recommendations |
| GET | `/api/toeic/runner/part/{part}` | Yes | Questions by part |
| GET | `/api/toeic/runner/mixed` | Yes | Mixed-part questions |
| GET | `/api/toeic/runner/questions` | Yes | Questions by IDs |
| GET | `/api/toeic/runner/review-focus` | Yes | Review-focused questions |
| GET | `/api/toeic/runner/minitest` | Pro | Mini test questions |
| GET | `/api/toeic/runner/fulltest` | Pro | Full test (200 questions) |

#### Attempts (`/api/attempts/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/attempts/practice` | Yes | Save practice attempt |
| POST | `/api/attempts/mock-test` | Pro | Save mock test attempt |
| POST | `/api/attempts/diagnostic` | Yes | Save diagnostic attempt |
| GET | `/api/attempts/practice/{id}` | Yes | Get practice result |
| GET | `/api/attempts/mock-test/{id}` | Pro | Get mock test result |

#### Progress (`/api/progress/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/progress/summary` | Yes | Full progress summary |
| GET | `/api/progress/history` | Yes | Day-by-day history |
| POST | `/api/progress/log` | No* | Log course progress |

#### Roadmap (`/api/roadmap/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/roadmap/generate` | Yes | Generate personalized roadmap |
| GET | `/api/roadmap/current` | Yes | Get active roadmap |
| GET | `/api/roadmap/evidence` | Yes | Practice evidence for roadmap |
| GET | `/api/roadmap/week/{id}/sets` | Yes | Week's practice sets |
| GET | `/api/roadmap/week/{id}/set/{setId}` | Yes | Set questions |
| POST | `/api/roadmap/week/{id}/start` | Yes | Start a week |
| POST | `/api/roadmap/week/{id}/complete` | Yes | Complete a week |

#### Review Center (`/api/review/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/review/items` | Yes | Review queue items (hydrated) |
| GET | `/api/review/summary` | Yes | Review statistics |
| GET | `/api/review/item/{id}` | Yes | Single review item detail |
| POST | `/api/review/items/{id}/reviewed` | Yes | Mark item reviewed |
| GET/POST | `/api/review/notes` | Yes | CRUD notes |
| PUT/DELETE | `/api/review/notes/{id}` | Yes | Update/delete note |
| GET/POST | `/api/review/highlights` | Yes | CRUD highlights |
| DELETE | `/api/review/highlights/{id}` | Yes | Delete highlight |
| GET/POST | `/api/review/bookmarks` | Yes | Get/toggle bookmarks |

#### Payments & Subscription (`/api/payments/...`, `/api/subscription/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/payments/create-pro-order` | Yes | Create PayOS payment |
| GET | `/api/payments/config-status` | No | Payment config check |
| POST | `/api/payments/payos-webhook` | No | PayOS webhook callback |
| GET | `/api/payments/status/{code}` | Yes | Check payment status |
| GET | `/api/payments/{code}` | Yes | Get order details |
| GET | `/api/subscription/current` | Yes | Current subscription |

#### Settings (`/api/settings/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET/PUT | `/api/settings/preferences` | Yes | Experience preferences |
| GET/PUT | `/api/settings/notifications` | Yes | Notification preferences |
| POST | `/api/settings/reset-progress` | Yes | Reset all progress |
| POST | `/api/settings/delete-history` | Yes | Delete attempt history |
| DELETE | `/api/settings/account` | Yes | Soft delete account |

#### Weekly Check (`/api/weekly-check/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/weekly-check/current` | Pro | Get current weekly check |
| POST | `/api/weekly-check/submit` | Pro | Submit weekly check |
| GET | `/api/weekly-check/result/{id}` | Pro | Get result |

#### Diagnostic (`/api/diagnostic/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/diagnostic/questions` | No | Placement test questions |
| POST | `/api/diagnostic/submit` | No | Submit diagnostic |

#### Flashcards (`/api/flashcards/...`)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/flashcards/topics` | No | All flashcard topics |
| GET | `/api/flashcards/topics/{code}/cards` | No | Cards by topic |

#### AI Services
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/chat` | Yes | AI tutor chat (SSE streaming) |
| POST | `/api/tts/tts` | No | Text-to-speech (edge-tts) |
| POST | `/api/tts/flashcard` | No | Flashcard TTS with caching |
| GET | `/api/tts/voices` | No | Available TTS voices |
| POST | `/api/translate` | No | AI English-Vietnamese translation |

#### System
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health` | No | Health check |

---

## 3. Role of `frontend/`

The React web frontend is a **single-page application** built with Vite.

### Structure

```
frontend/src/
├── main.tsx              ← App entry (AppProviders + RouterProvider)
├── router/index.tsx      ← 25+ routes with React Router v7
├── layouts/              ← AuthLayout, DashboardLayout, MarketingLayout
├── pages/                ← 13 page directories, 20+ page components
├── components/           ← Shared components (auth, chat, runner, UI)
├── services/             ← 14 API service files
├── hooks/                ← useAuthSession, useEntitlements, useHighlightSelection
├── providers/            ← AppProviders (Theme + Language + Sonner)
├── contexts/             ← LanguageContext (i18n)
├── data/                 ← Static page data/configs (13 files)
├── i18n/                 ← Internationalization
├── styles/               ← Global CSS
└── utils/                ← Utility functions
```

### Dependencies

- **UI**: shadcn/ui (Radix primitives), Lucide icons, Recharts, Embla Carousel
- **Forms**: react-hook-form + zod
- **Theming**: next-themes (dark/light mode)
- **Notifications**: Sonner toast library

---

## 4. Role of `module/`

Contains **supporting modules** that are independent of the main backend:

| Directory | Contents | Purpose |
|-----------|----------|---------|
| `module/aidich/` | `translate.py`, `train.py`, `test.py`, `gui.py`, `cache.json` | AI English-Vietnamese translation model (custom ML) |
| `module/doctienganh/` | `server.py`, `audio/`, `frontend/` | English reading/listening practice server (standalone) |
| `module/latthe/` | 41 JSON files (1.4MB+ vocab data) | Flashcard vocabulary data (organized by topic categories) |

### Flutter Relevance

- **`module/latthe/`**: Flashcard JSON data could be bundled into the Flutter app for offline use
- **`module/aidich/`**: Translation service is exposed through `/api/translate` endpoint (already available)
- **`module/doctienganh/`**: Standalone module, not currently integrated with main backend

---

## 5. Existing Web Screens

| # | Route | Page Component | Category |
|---|-------|---------------|----------|
| 1 | `/` | LandingPage | Marketing |
| 2 | `/pricing` | PricingPage | Marketing |
| 3 | `/payment-success` | PaymentSuccessPage | Marketing |
| 4 | `/payment-cancel` | PaymentCancelPage | Marketing |
| 5 | `/login` | LoginPage | Auth |
| 6 | `/register` | RegisterPage | Auth |
| 7 | `/forgot-password` | ForgotPasswordPage | Auth |
| 8 | `/reset-password` | ResetPasswordPage | Auth |
| 9 | `/onboarding` | OnboardingPage | Onboarding |
| 10 | `/dashboard` | DashboardPage | Core |
| 11 | `/placement-test` | PlacementTestPage | Core |
| 12 | `/practice` | PracticePage | Core |
| 13 | `/practice/runner` | PracticeRunnerPage | Core |
| 14 | `/practice/summary` | PracticeSummaryPage | Core |
| 15 | `/mock-test` | MockTestPage | Core |
| 16 | `/mock-test/runner` | MockTestRunnerPage | Core |
| 17 | `/mock-test/result` | MockTestResultPage | Core |
| 18 | `/mini-test/result` | MockTestResultPage (reused) | Core |
| 19 | `/full-test/result` | MockTestResultPage (reused) | Core |
| 20 | `/weekly-check/runner` | MockTestRunnerPage (reused) | Core |
| 21 | `/weekly-check/result` | MockTestResultPage (reused) | Core |
| 22 | `/progress` | ProgressPage | Core |
| 23 | `/roadmap` | RoadmapPage | Core |
| 24 | `/review` | ReviewPage | Core |
| 25 | `/settings` | SettingsPage | Core |
| 26 | `/flashcards` | FlashcardPage | Core |
| 27 | `/voice-reader` | VoiceReaderPage | Core |
| 28 | `*` | NotFoundPage | System |

---

## 6. Existing Frontend Services

| Service File | API Domain | Key Methods |
|-------------|------------|-------------|
| `apiClient.ts` | Core | `apiRequest()`, token management |
| `authService.ts` | Auth | login, register, googleAuth, onboarding, changePassword |
| `dashboardService.ts` | Dashboard | getOverview, getProgressHistory, getSummary |
| `toeicService.ts` | TOEIC | getSummary, getPartRunner, getMixedRunner, getMiniTestRunner, getFullTestRunner |
| `attemptsService.ts` | Attempts | submitPracticeAttempt, submitMockTestAttempt, getResults |
| `progressService.ts` | Progress | getSummary (mapped to ProgressView) |
| `roadmapService.ts` | Roadmap | getCurrent, generateCurrent, startWeek, completeWeek, getSetRunner |
| `reviewService.ts` | Review | getItems, getSummary, notes CRUD, highlights CRUD, bookmarks |
| `paymentsService.ts` | Payments | createProOrder, getPaymentStatus, getConfigStatus |
| `subscriptionService.ts` | Subscription | getCurrent |
| `settingsService.ts` | Settings | preferences CRUD, notifications, dangerZone |
| `weeklyCheckService.ts` | Weekly Check | getCurrent, submitWeeklyCheck, getResult |
| `diagnosticService.ts` | Diagnostic | getQuestions, submit |
| `chatService.ts` | AI Chat | sendMessage (SSE stream), conversation management |

---

## 7. Features with Real API (Working)

| Feature | API Status | Notes |
|---------|-----------|-------|
| User Registration / Login | ✅ Real API | JWT + pbkdf2_sha256 |
| Google Sign-In | ✅ Real API | google-auth via verify endpoint |
| Onboarding Flow | ✅ Real API | Saves to User table |
| Dashboard Overview | ✅ Real API | Aggregates from multiple tables |
| TOEIC Practice (Part/Mixed) | ✅ Real API | Queries ToeicPracticeQuestions |
| Practice Runner | ✅ Real API | Full question rendering + answer submit |
| Practice Submission | ✅ Real API | Saves PracticeAttempt + PracticeAttemptAnswers |
| Practice Summary/Results | ✅ Real API | Full score breakdown |
| Mini Test / Full Test | ✅ Real API | Pro-gated, saves MockTestAttempt |
| Weekly Check | ✅ Real API | Pro-gated, auto-generated from weak skills |
| Diagnostic/Placement Test | ✅ Real API | IRT-based scoring |
| Roadmap Generation | ✅ Real API | Rule-based from skill analytics |
| Roadmap Progress | ✅ Real API | Week start/complete, evidence tracking |
| Review Queue | ✅ Real API | Complex hydration from multiple question sources |
| Notes / Highlights / Bookmarks | ✅ Real API | Full CRUD per question |
| Progress Analytics | ✅ Real API | Skill profiles, part stats, history |
| Payment (PayOS) | ✅ Real API | QR code, webhook, subscription activation |
| Subscription Management | ✅ Real API | Plan check, entitlements |
| Settings (Preferences) | ✅ Real API | Experience + notification prefs |
| Account Management | ✅ Real API | Soft delete, reset progress |
| AI Chat (Tutor) | ✅ Real API | SSE streaming, context-aware |
| TTS (Text-to-Speech) | ✅ Real API | edge-tts, file caching |
| Translation | ✅ Real API | Custom ML model |
| Flashcards | ✅ Real API | DB-backed topics + cards |

## 8. Features Using Mock/Hardcoded Data

| Feature | Status | Details |
|---------|--------|---------|
| Forgot Password | ⚠️ Stub | Always returns success, no email sent |
| Voice Reader Page | ⚠️ Client-only | Uses browser SpeechSynthesis API, no backend |
| Notification Bell | ⚠️ UI-only | Badge shown but no notification system |
| Search Bar | ⚠️ UI-only | Input rendered but non-functional |
| Dashboard Courses | ⚠️ Legacy | Uses Enrollment/Course tables (not TOEIC-specific) |
| Static page data | Hardcoded | `src/data/` files contain marketing copy, onboarding steps |

---

## 9. Missing APIs for Flutter

| Feature | What's Needed | Priority |
|---------|--------------|----------|
| **Push Notifications** | Device token registration, notification preferences | High |
| **Offline Mode** | Sync endpoint, last-synced timestamp, delta fetch | Medium |
| **App Version Check** | `/api/app/version-check` for force-update | Medium |
| **Mobile Payment Flow** | Deep-link return URLs (not web redirect) | High |
| **Audio Streaming** | Byte-range support for mobile audio player | Medium |
| **Image Optimization** | Thumbnail/compressed image variants | Low |
| **Pagination** | Many list endpoints lack proper pagination | Medium |
| **Error Codes** | Standardized error code enum for mobile parsing | Medium |

---

## 10. Migration Risks

### High Risk

| Risk | Details |
|------|---------|
| **camelCase / snake_case mix** | Backend responses use camelCase (built for React). Flutter convention is snake_case. Need to verify all response field names and decide on a serialization strategy. |
| **Chat SSE Streaming** | `/api/chat` uses Server-Sent Events. Flutter needs a robust SSE client (e.g., `http` + `StreamedResponse` or `eventsource` package). |
| **Payment Deep Links** | PayOS returns redirect URLs (`returnUrl`/`cancelUrl`) pointing to `localhost:5173`. Flutter needs custom scheme deep links or in-app WebView. |
| **Audio Player Complexity** | Practice runner plays question audio from static file URLs. Mobile needs proper audio session management, background playback control. |
| **Large Practice Runner** | `PracticeRunnerPage.tsx` is 59KB, `MockTestRunnerPage.tsx` is 42KB. These are the most complex screens and will require careful Flutter re-implementation. |

### Medium Risk

| Risk | Details |
|------|---------|
| **Auth Token Storage** | Web uses localStorage. Flutter should use `flutter_secure_storage`. Same JWT format works. |
| **CORS for Mobile** | Mobile HTTP clients don't enforce CORS, but backend CORS config may need `*` or explicit mobile origins. |
| **Static Asset URLs** | Images/audio reference `/toeic/`, `/audio/`, `/images/` paths. Flutter needs full base URL resolution. |
| **Review System Complexity** | Review route is 2945 lines with complex hydration logic. Flutter must handle the same response shapes. |
| **Real-time Features** | No WebSocket support. If Flutter needs real-time updates, backend would need enhancement. |

### Low Risk

| Risk | Details |
|------|---------|
| **Auth API** | Standard JWT bearer token. Works identically from any HTTP client. |
| **REST API Contract** | All endpoints return JSON. Flutter can consume them directly with `dio` or `http`. |
| **Database** | No changes needed. Flutter never touches DB directly. |
| **Module isolation** | `module/` is independent. No risk of breaking it. |

---

## 11. Where `getgoals_mobile/` Will Be Created

```
test/
├── backend/           ← NO CHANGES (shared)
├── frontend/          ← NO CHANGES
├── module/            ← NO CHANGES
├── getgoals_mobile/   ← NEW Flutter project
│   ├── lib/
│   │   ├── main.dart
│   │   ├── app/
│   │   ├── core/
│   │   ├── features/
│   │   ├── services/
│   │   └── widgets/
│   ├── android/
│   ├── ios/
│   ├── pubspec.yaml
│   └── ...
└── docs/
    └── mobile_migration/  ← These planning documents
```

> The Flutter app will be a **pure mobile client** consuming the same FastAPI backend. No separate backend, no direct DB connection.
