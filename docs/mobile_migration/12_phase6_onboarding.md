# 12 - Phase 6: Flutter Onboarding

> Phase 6 - Real Mobile Onboarding
> Generated: 2026-05-16 | Status: Complete

## Completed Scope

Phase 6 replaced the `/onboarding` placeholder with a real Flutter onboarding form backed by the shared FastAPI backend.

Completed:

- Real mobile-first `OnboardingPage`.
- Current score input with an "unknown score" option.
- Target score input.
- Exam date picker.
- Study minutes per day selection.
- Weak skills multi-select.
- Validation, loading, error, retry, submit, and logout states.
- Backend submit through `POST /api/auth/onboarding`.
- Auth refresh through `GET /api/auth/me` after submit.
- Router guard update so onboarded users cannot remain on `/onboarding`.
- Debug logs for page entry, submit start, payload, API success/failure, refreshed onboarding value, and navigation target.

## Endpoint Used

`POST /api/auth/onboarding`

The backend schema in `backend/app/api/routes/auth.py` uses camelCase fields:

```json
{
  "currentScore": 450,
  "targetScore": 750,
  "examDate": "2026-08-30",
  "studyMinutesPerDay": 45,
  "weakSkills": ["grammar", "vocabulary"]
}
```

`currentScore` may be `null` when the user does not know their score yet.

## Files Created

- `getgoals_mobile/lib/features/onboarding/data/onboarding_repository.dart`
- `getgoals_mobile/lib/features/onboarding/data/models/onboarding_request.dart`
- `getgoals_mobile/lib/features/onboarding/data/models/onboarding_response.dart`
- `getgoals_mobile/lib/features/onboarding/state/onboarding_controller.dart`
- `getgoals_mobile/lib/features/onboarding/presentation/pages/onboarding_page.dart`

## Files Modified

- `getgoals_mobile/lib/app/router.dart`
- `getgoals_mobile/lib/features/auth/state/auth_controller.dart`
- `docs/mobile_migration/phase_status.md`

## Navigation Behavior

- Unauthenticated users trying to visit `/onboarding` are redirected to `/login`.
- Authenticated users with `onboardingCompleted=false` are redirected to `/onboarding`.
- Authenticated users with `onboardingCompleted=true` are redirected away from `/onboarding` to `/dashboard`.
- After successful onboarding:
  - Flutter refreshes the user with `GET /api/auth/me`.
  - If refreshed `currentScore` is missing or `<= 0`, the app navigates to `/placement-test`.
  - Otherwise the app navigates to `/dashboard`.

## Backend Changes

No backend changes were made. The app uses the existing shared FastAPI endpoint and keeps all SQL Server access on the backend.

## How To Test

1. Register a new user or set an existing user to `OnboardingCompleted = 0`.
2. Log in on Android emulator.
3. Confirm the app redirects to `/onboarding`.
4. Fill target score, exam date, study minutes, and weak skills.
5. Submit.
6. Confirm backend returns success.
7. Confirm `/api/auth/me` returns `onboardingCompleted=true`.
8. Confirm navigation:
   - Unknown current score goes to `/placement-test`.
   - Known current score goes to `/dashboard`.

## Remaining TODOs

- Add Google Sign-In UI for mobile.
- Add production password reset with email/OTP/token.
- Add deeper onboarding personalization if backend later exposes a diagnostic-required flag.
