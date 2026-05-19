# 10 - Final Mobile Architecture

> Generated: 2026-05-14

## Architecture Summary

`getgoals_mobile/` is a Flutter client for the existing GetGoals FastAPI backend.

- No separate Flutter backend.
- No direct SQL Server connection from Flutter.
- JWT authentication is stored in `flutter_secure_storage`.
- API calls use `Dio` through `core/network/api_client.dart`.
- Static audio/image paths are converted to full URLs with `ApiClient.assetUrl`.
- Feature state uses Riverpod controllers and repositories.
- Navigation uses `go_router` with a bottom-navigation shell and full-screen runner routes.

## Main Feature Areas

- Auth: login, register, forgot/reset password screens, session restore.
- Dashboard: overview cards backed by real dashboard/progress data.
- Practice: TOEIC catalog, runner, submit, summary.
- Diagnostic: placement questions and result.
- Roadmap: current/generate roadmap and set launch.
- Review: review queue, notes, bookmarks, contextual AI Tutor.
- Progress: charts and analytics from `/api/progress/summary`.
- Tests: shared runner for weekly, mock, mini, and full tests.
- Flashcards: API topics/cards plus TTS pronunciation.
- Voice Reader: TTS bytes from backend played by `just_audio`.
- Chat: JSON AI Tutor endpoint with context payloads.
- Payment: PayOS checkout URL launch and subscription status.
- Settings: profile, preferences, password, logout, dev diagnostics.

## Shared Runner Strategy

Practice mode remains in `features/practice` because it shows immediate learning feedback through the existing practice result flow. Test mode lives in `features/mock_test` and is shared by Weekly Check, Mock Test, Mini Test, and Full Test.

Test mode behavior:

- Timer visible.
- Large option cards.
- Flagging and question navigator.
- Submit only at the end.
- No immediate answer reveal.
- Result screen shows score, breakdowns, weak areas, and question review.

## Pro Handling

Pro-gated endpoints may return `403` with `code: PRO_REQUIRED`. Flutter catches that through `ApiException` and shows `ProFeatureDialog` instead of raw server errors. The dialog can route to `/pricing`.

## Media Handling

- TOEIC runner audio/images use `ApiClient.assetUrl`.
- Flashcard pronunciation calls `POST /api/tts/flashcard`, then plays the returned static audio URL.
- Voice Reader calls `POST /api/tts/tts`, receives audio bytes, and plays them through a data URI with `just_audio`.

## Release Considerations

- Add mobile deep links for payment return/cancel URLs.
- Move production traffic to HTTPS.
- Add local persistence for runner drafts.
- Add pagination for large review lists.
- Add push notification registration if reminders become native notifications.
