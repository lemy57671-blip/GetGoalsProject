# 06 - Phase 3: Auth, Splash, Guard, Dashboard

> Phase 3 - Flutter Auth & Dashboard
> Generated: 2026-05-13 | Status: Complete

## Completed Scope

Phase 3 implemented the first real Flutter feature layer in `getgoals_mobile/`:

- Auth data models, repository, and Riverpod controller
- Login, register, forgot-password, and reset-password pages
- Splash startup flow using secure storage and the real current-user endpoint
- Router auth guard for public, private, and onboarding routes
- Dashboard repository/controller/page backed by real FastAPI endpoints

The Flutter app remains a pure mobile client. No separate backend was created, and Flutter does not connect directly to SQL Server.

## Auth Endpoints Used

| Purpose | Method | Endpoint | Notes |
|---|---:|---|---|
| Login | POST | `/api/auth/login` | Body: `{ email, password, remember }`; returns `{ token, user }` |
| Register | POST | `/api/auth/register` | Body: `{ name, email, password }`; returns `{ token, user }` |
| Current user | GET | `/api/auth/me` | Bearer token required |
| Forgot password | POST | `/api/auth/forgot-password` | Backend currently accepts request but is a stub; no email is sent |
| Reset password | POST | `/api/auth/reset-password-direct` | Direct reset endpoint; no token/OTP contract is present |
| Onboarding status | GET | `/api/auth/me` | Uses `user.onboardingCompleted` from the current-user response |

Related user endpoints found but not implemented in Phase 3 UI:

- `PATCH /api/auth/profile`
- `PATCH /api/auth/learning-settings`
- `POST /api/auth/onboarding`
- `POST /api/auth/change-password`
- `GET /api/me/entitlements`
- `GET /api/me/profile-summary`

TODO: Replace `/api/auth/forgot-password` and `/api/auth/reset-password-direct` with a real email/OTP/token reset contract before production mobile release.

## Dashboard Endpoints Used

| Purpose | Method | Endpoint | Notes |
|---|---:|---|---|
| Dashboard overview | GET | `/api/dashboard/overview` | Bearer token required; primary dashboard data source |
| Recent attempts | GET | `/api/progress/summary` | Bearer token required; used only because overview does not include recent attempts |

Legacy dashboard endpoints were inspected but not used for the mobile dashboard:

- `GET /api/dashboard/summary?userId=...`
- `GET /api/dashboard/courses?userId=...`
- `GET /api/dashboard/weekly-hours?userId=...`

Those legacy endpoints rely on a `userId` query parameter and are not JWT-first, so Phase 3 avoids them.

## Files Created

Auth:

- `getgoals_mobile/lib/features/auth/data/auth_repository.dart`
- `getgoals_mobile/lib/features/auth/data/models/auth_user.dart`
- `getgoals_mobile/lib/features/auth/data/models/login_request.dart`
- `getgoals_mobile/lib/features/auth/data/models/register_request.dart`
- `getgoals_mobile/lib/features/auth/data/models/auth_response.dart`
- `getgoals_mobile/lib/features/auth/state/auth_controller.dart`
- `getgoals_mobile/lib/features/auth/presentation/pages/login_page.dart`
- `getgoals_mobile/lib/features/auth/presentation/pages/register_page.dart`
- `getgoals_mobile/lib/features/auth/presentation/pages/forgot_password_page.dart`
- `getgoals_mobile/lib/features/auth/presentation/pages/reset_password_page.dart`
- `getgoals_mobile/lib/features/auth/presentation/widgets/auth_page_shell.dart`

Splash:

- `getgoals_mobile/lib/features/splash/presentation/pages/splash_page.dart`

Dashboard:

- `getgoals_mobile/lib/features/dashboard/data/dashboard_repository.dart`
- `getgoals_mobile/lib/features/dashboard/data/models/dashboard_summary.dart`
- `getgoals_mobile/lib/features/dashboard/state/dashboard_controller.dart`
- `getgoals_mobile/lib/features/dashboard/presentation/pages/dashboard_page.dart`

Docs:

- `docs/mobile_migration/06_phase3_auth_dashboard.md`

## Files Modified

- `getgoals_mobile/lib/app/app.dart`
- `getgoals_mobile/lib/app/router.dart`
- `getgoals_mobile/lib/core/storage/token_storage.dart`
- `docs/mobile_migration/phase_status.md`

## Auth Flow

Startup:

1. `/` shows splash.
2. `AuthController.checkSession()` reads token from `flutter_secure_storage`.
3. No token redirects to `/login`.
4. Token exists calls `GET /api/auth/me`.
5. Valid onboarded user redirects to `/dashboard`.
6. Valid not-onboarded user redirects to `/onboarding`.
7. `401` or `403` clears the token and redirects to `/login`.

Router guard:

- Unauthenticated users visiting private routes are redirected to `/login`.
- Authenticated users visiting `/login`, `/register`, `/forgot-password`, or `/reset-password` are redirected to `/dashboard`, or `/onboarding` if onboarding is incomplete.
- Authenticated users with incomplete onboarding are redirected to `/onboarding` from private app routes.

## Dashboard UX Implemented

The dashboard is mobile-first and uses large cards with clean spacing:

- Greeting user
- Estimated TOEIC score from latest diagnostic, falling back to current score
- Recent accuracy
- Streak
- Today goal from learning settings
- Weak skill/weak part
- Roadmap preview
- Recent practice attempts
- Quick actions: Start Practice, Review Mistakes, Mock Test
- Loading, empty, error, pull-to-refresh, and retry states

Detailed charts remain deferred to the Progress feature.

## Verification

Commands run from `test/getgoals_mobile`:

```bash
D:\flutter\bin\flutter.bat analyze
D:\flutter\bin\flutter.bat test
```

Result:

- Analyzer: no issues found
- Tests: all tests passed

## Remaining Issues

- Forgot password is backend-stubbed and does not send email.
- Reset password uses `/api/auth/reset-password-direct`; this is not a production-safe tokenized reset flow.
- Onboarding route still points to the Phase 2 placeholder screen. Phase 3 guard supports it, but the full onboarding form remains for a later pass.
- Dashboard recent attempts come from `/api/progress/summary` because `/api/dashboard/overview` does not include a recent-attempt list.
- Google Sign-In endpoints exist but the Flutter Google Sign-In UI/package flow was not implemented in this phase.

## Next Phase

Phase 4 will implement Practice Catalog, Runner, Attempt Submit, Result, Review, Diagnostic, and Roadmap.
