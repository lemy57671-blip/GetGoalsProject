# Phase Status - GetGoals Mobile Migration

> Last Updated: 2026-05-16 UTC+7

## Phase 1: Audit & Plan - COMPLETE

- `01_source_audit.md`
- `02_web_to_flutter_mapping.md`
- `03_mobile_ux_plan.md`
- `04_api_contract_needed.md`

## Phase 2: Bootstrap Flutter Core - COMPLETE

Core Flutter project, routing, API client, token storage, theme, shared widgets, and placeholder feature routes were created.

Details: `05_phase2_flutter_core.md`

## Phase 3: Auth, Splash, Guard, Dashboard - COMPLETED

Completed:

- Login/register/forgot/reset screens.
- Secure JWT storage and session restore.
- Auth route guard.
- Dashboard using real API data.

Details: `06_phase3_auth_dashboard.md`

Endpoints used:

- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password-direct`
- `GET /api/dashboard/overview`
- `GET /api/progress/summary`

## Phase 4: Practice, Review, Diagnostic, Roadmap - COMPLETED

Completed:

- Practice catalog.
- Practice runner.
- Submit attempt.
- Result page.
- Review Center.
- Diagnostic.
- Roadmap.

Details: `07_phase4_learning_flow.md`

Endpoints used:

- `GET /api/toeic/summary`
- `GET /api/toeic/runner/part/{part}`
- `GET /api/toeic/runner/mixed`
- `GET /api/toeic/runner/review-focus`
- `GET /api/roadmap/week/{weekId}/set/{setId}`
- `POST /api/attempts/practice`
- `GET /api/attempts/practice/{attemptId}`
- `POST /api/attempts/diagnostic`
- `GET /api/review/items`
- `POST /api/review/notes`
- `POST /api/review/bookmarks/toggle`
- `POST /api/review/item/{id}/mark-reviewed`
- `GET /api/diagnostic/questions`
- `POST /api/diagnostic/submit`
- `GET /api/roadmap/current`
- `POST /api/roadmap/generate`

## Phase 5: Expanded Learning, Media, Monetization, Polish - COMPLETED

Phase 5 completed the remaining Flutter surfaces and final docs.

Completed Flutter features:

- Progress analytics with `fl_chart` trend charts.
- Weekly Check page, shared runner, submit, and result.
- Mock Test, Mini Test, and Full Test using shared test-mode runner.
- Flashcards with TTS pronunciation, swipe/next/previous, and learned state.
- Voice Reader with backend TTS and `just_audio` playback.
- AI Tutor full-screen chat and contextual Review bottom sheet.
- Payment/Pricing flow with subscription check, PayOS checkout URL launch, and payment status check.
- Settings/Profile with preferences, password change, app version, API base debug info, and logout.
- README and final architecture/completion docs.

Endpoints used:

- `GET /api/progress/summary`
- `GET /api/weekly-check/current`
- `POST /api/weekly-check/submit`
- `GET /api/weekly-check/result/{id}`
- `GET /api/toeic/runner/minitest`
- `GET /api/toeic/runner/fulltest`
- `POST /api/attempts/mock-test`
- `GET /api/attempts/mock-test/{id}`
- `GET /api/flashcards/topics`
- `GET /api/flashcards/topics/{code}/cards`
- `POST /api/tts/flashcard`
- `POST /api/tts/tts`
- `GET /api/tts/voices`
- `POST /api/chat`
- `GET /api/subscription/current`
- `POST /api/payments/create-pro-order`
- `GET /api/payments/status/{code}`
- `GET /api/settings/preferences`
- `PUT /api/settings/preferences`
- `GET /api/settings/notifications`
- `POST /api/auth/change-password`

Backend changes:

- None by Phase 5. The Flutter app continues to use the existing shared FastAPI backend.

Remaining TODOs:

- Add mobile payment return/cancel deep links in the backend/payment provider config.
- Add durable local runner draft/resume.
- Add backend pagination for large review queues.
- Add production password reset contract.
- Add full onboarding UI and Google Sign-In in Flutter.
- Add push notification registration and app version checks before store release.

## Full App Testing Guide

1. Start backend from `test/backend`:

   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

2. Run Flutter on Android emulator:

   ```bash
   cd getgoals_mobile
   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8001
   ```

3. Or run Flutter on Windows/Desktop:

   ```bash
   flutter run --dart-define=API_BASE_URL=http://localhost:8001
   ```

4. Or run on a physical phone:

   ```bash
   flutter run --dart-define=API_BASE_URL=http://<COMPUTER_IP>:8001
   ```

5. Verify:

- Login/register/me works.
- Dashboard uses real API.
- Practice Runner works.
- Submit Attempt works.
- Result page works.
- Review works and Ask AI opens with context.
- Diagnostic works.
- Roadmap works.
- Progress works.
- Weekly/mock/mini/full test reuse runner.
- Flashcards/TTS/audio works.
- Voice Reader can generate and play/pause audio.
- Chat works with `/api/chat`, or shows Pro dialog if gated.
- Payment/subscription flow is clear.
- Settings/Profile and logout work.
- No separate database or direct SQL connection from Flutter.

6. Automated checks from `test/getgoals_mobile`:

   ```bash
   flutter analyze
   flutter test
   flutter build apk --debug
   ```

## Phase 6: Real Flutter Onboarding - COMPLETED

Phase 6 replaced the `/onboarding` placeholder with a real mobile onboarding form connected to the existing shared FastAPI backend.

Details: `12_phase6_onboarding.md`

Completed:

- Current score input with unknown-score option.
- Target score input.
- Exam date picker.
- Study minutes per day selection.
- Weak skills multi-select.
- Validation, loading, error, retry, submit, and logout states.
- Auth refresh after submit.
- Router guard update for `/onboarding`.

Endpoint used:

- `POST /api/auth/onboarding`
- `GET /api/auth/me`

Exact payload used:

```json
{
  "currentScore": 450,
  "targetScore": 750,
  "examDate": "2026-08-30",
  "studyMinutesPerDay": 45,
  "weakSkills": ["grammar", "vocabulary"]
}
```

Backend changes:

- None. Flutter uses the existing shared FastAPI backend.

Remaining TODOs:

- Google Sign-In UI for Flutter.
- Production password reset with email/OTP/token.
- Optional backend diagnostic-required flag if onboarding navigation needs server-side control.

## Phase 7: Premium Mobile UI Beautification - COMPLETED

Phase 7 upgraded the Flutter UI/UX to a premium mobile learning app style while preserving existing API integrations and shared backend architecture.

Details: `13_ui_beautification.md`

Completed:

- Design system tokens for colors, spacing, radius, shadows, text, and Material 3 theme.
- Shared polished widgets for scaffold, top bar, buttons, cards, text fields, chips, loading, error, empty, exit confirm, and Pro upsell dialogs.
- `flex_color_scheme` Material 3 theme using system `Roboto` or platform fonts only.
- Lucide icon treatment across nav, dashboard, practice, tests, voice, settings, dialogs, and result surfaces.
- Skeleton loading states through `skeletonizer`.
- Light `flutter_animate` transitions for cards, buttons, dashboard sections, onboarding, practice, and results.
- Multi-step onboarding with `smooth_page_indicator`.
- Cached media rendering in runners through `cached_network_image`.
- Progress-to-goal and result score hero through `percent_indicator`.
- Friendly user-facing errors that avoid raw `DioException`.
- X exit confirmation for practice/test runners.
- Back affordances for pushed non-root screens.

Packages used:

- `flex_color_scheme`
- `flutter_animate`
- `animations`
- `lucide_icons_flutter`
- `flutter_svg`
- `skeletonizer`
- `smooth_page_indicator`
- `fl_chart`
- `percent_indicator`
- `cached_network_image`
- `gap`

Backend changes:

- None. Flutter still uses the existing shared FastAPI backend only.

Remaining TODOs:

- Add screenshot/golden UI tests.
- Add final brand illustration assets if the product gets a dedicated asset pack.
- Add deeper dark-mode QA on physical devices.
- Add payment return/cancel deep-link polish after provider callback config is finalized.

## Phase A: UI Foundation + Navigation Redesign - COMPLETED

Phase A is a scoped follow-up that stabilizes the Flutter UI foundation and navigation shell before deeper screen redesign work.

Details: `18_ui_foundation_redesign.md`

Completed:

- Added reusable `AppBottomNav` for the five root tabs: Dashboard, Practice, Progress, Review, and Settings.
- Kept root tab switching in `StatefulNavigationShell` without reintroducing scaffold transition keys.
- Added `AppScaffold.backFallbackRoute` so non-root screens can safely fall back to a known route when there is no navigation stack.
- Reworked `PlaceholderScreen` into a friendly fallback using `AppScaffold` and `AppEmptyView` with a clear action.
- Added a direct action from the diagnostic result fallback back to the placement test.
- Preserved runner/test X exit confirmation behavior.
- Preserved recent fixes for practice part selection, audio scroll persistence, in-app checkout, and already-Pro upgrade state.

Packages added:

- None. Existing UI packages remain in use.

Backend changes:

- None. Flutter continues to use the existing shared FastAPI backend only.

Remaining TODOs:

- Phase B: polish Splash, Login/Register, Onboarding, Dashboard, and Practice Catalog.
- Phase C: runner Ask AI chatbox, highlight, notebook/notes, and bookmark polish.
- Phase D: review grouping and Voice Reader deep fixes.
- Phase E: Google Sign-In and placement test audio/scoring improvements.
- Phase F: final Pro/payment polish.
