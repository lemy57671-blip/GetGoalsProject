# Phase 7 / UI Beautification - GetGoals Mobile

> Date: 2026-05-16 UTC+7

## Goal

Upgrade the Flutter app from a functional MVP look to a smoother premium mobile learning experience without changing backend architecture or business logic.

## Scope Completed

- Added a real Flutter design system:
  - `lib/core/theme/app_colors.dart`
  - `lib/core/theme/app_spacing.dart`
  - `lib/core/theme/app_radius.dart`
  - `lib/core/theme/app_shadows.dart`
  - `lib/core/theme/app_text_styles.dart`
  - `lib/core/theme/app_theme.dart`
- Moved the app theme to Material 3 through `flex_color_scheme`.
- Kept system/bundled platform fonts only. No runtime Google Fonts download is required.
- Added shared polished widgets:
  - `AppScaffold`
  - `AppTopBar`
  - `AppButton`
  - `AppCard`
  - `AppTextField`
  - `AppChip`
  - `AppLoadingView`
  - `AppErrorView`
  - `AppEmptyView`
  - `ExitConfirmDialog`
  - `ProFeatureDialog`
- Added friendly error handling through `friendlyError()` so raw `DioException` text is logged to debug output instead of shown to users.

## Packages Used

- `flex_color_scheme`: Material 3 theme generation and component subthemes.
- `flutter_animate`: light fade/slide/scale motion on cards, buttons, and learning surfaces.
- `animations`: shared-axis page transition wrapper inside `AppScaffold`.
- `lucide_icons_flutter`: premium line icon system across nav, runners, dashboard, tests, settings, and dialogs.
- `flutter_svg`: inline friendly empty/error illustrations.
- `skeletonizer`: dashboard/progress/catalog style loading placeholders through `AppLoadingView`.
- `smooth_page_indicator`: onboarding multi-step progress.
- `fl_chart`: existing progress charts retained.
- `percent_indicator`: dashboard goal progress and result score hero.
- `cached_network_image`: cached question images in runner/test media.
- `gap`: consistent readable widget spacing.

## Screens Redesigned

- Onboarding:
  - Converted to a 3-step mobile flow.
  - Added smooth page indicator, animated cards, validation by step, logout option, retry, and polished submit state.
  - Still submits to `POST /api/auth/onboarding`.
- Dashboard:
  - Added premium score hero, goal progress, today's plan, weak skill signal, roadmap preview, quick actions, recent attempts, and skeleton loading.
- Practice Catalog:
  - Split Listening and Reading.
  - Redesigned Part 1-7 cards and session setup controls.
- Practice Runner:
  - Added X exit with confirmation.
  - Added progress bar, timer pill, larger answer cards, cached media, and friendly submit errors.
- Test Runner:
  - Same runner polish as practice, with test-mode copy and exit confirmation.
- Practice Result:
  - Added score hero, weak-area next steps, breakdown cards, review mistakes, Ask AI, and repeat practice actions.
- Voice Reader:
  - Friendly TTS errors.
  - Play/Pause only appears after successful generation.
  - Voice dropdown shows human label while sending the real voice id.
- Review, Progress, Roadmap, Flashcards, Chat, Pricing, Settings:
  - Moved to the shared app scaffold/top-bar pattern.
  - Added friendly error behavior and clearer back affordances for pushed routes.

## Navigation Improvements

- Root tabs remain:
  - Dashboard
  - Practice
  - Progress
  - Review
  - Settings
- Non-root pushed screens now have a back affordance through `AppScaffold(showBack: true)`.
- Practice and test runners now have explicit X exit buttons with `ExitConfirmDialog`.
- Pricing, Chat, Voice Reader, Flashcards, Roadmap, Diagnostic, and Test pages are no longer visual dead ends.

## Error/Empty/Loading UX

- `ErrorView` now converts raw technical errors to friendly copy.
- Technical details are sent to `debugPrint`.
- `AppLoadingView` uses skeleton cards instead of blank loading screens.
- Empty states use friendly illustrations through `flutter_svg`.

## Backend Changes

None.

The Flutter app continues to use the shared FastAPI backend and does not connect directly to SQL Server.

## Verification

Run from `test/getgoals_mobile`:

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

## Remaining UI TODOs

- Add final brand illustration assets if a dedicated GetGoals visual identity pack is created.
- Add deeper dark-mode QA on physical Android devices.
- Add screenshot/golden tests for dashboard, onboarding, runner, and result pages.
- Add mobile payment return deep-link polish after payment provider callbacks are finalized.
