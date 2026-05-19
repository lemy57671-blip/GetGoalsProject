# Phase A - UI Foundation + Navigation Redesign

> Date: 2026-05-16 UTC+7

## Implementation Plan

Phase A is intentionally limited to the Flutter UI foundation and navigation consistency. It does not implement Google Sign-In, runner chat tools, review grouping, placement-test AI scoring, or backend changes.

Steps:

1. Verify the current app shell, router, theme tokens, shared widgets, and recent bug fixes.
2. Keep the existing shared FastAPI backend integration unchanged.
3. Complete the shared UI foundation by adding any missing primitives, especially a reusable bottom navigation widget.
4. Ensure non-root surfaces have back or close affordances through the shared scaffold/top bar pattern.
5. Ensure runner/test screens keep their X exit confirmation.
6. Keep friendly user-facing errors and debug-only technical logging.
7. Preserve the recent fixes:
   - Practice part selection must not rebuild/reload the page through scaffold animation keys.
   - Practice audio must remain alive while scrolling.
   - Pro checkout must open inside the app and already-Pro users must not be able to upgrade again.
8. Run Flutter verification.

## Packages Added

No new packages were added in Phase A. The needed UI packages were already present:

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

## Design System Summary

The Flutter app now has a centralized design foundation in `lib/core/theme/`:

- `app_colors.dart`: indigo/blue-violet primary, cyan/emerald accents, soft backgrounds, light/dark surfaces, semantic colors, gradients.
- `app_spacing.dart`: shared spacing scale and button height.
- `app_radius.dart`: shared radii for cards, inputs, buttons, and sheets.
- `app_shadows.dart`: soft card and lifted shadows.
- `app_text_styles.dart`: GetGoals text hierarchy.
- `app_theme.dart`: Material 3 theme with `flex_color_scheme`, system `Roboto`, rounded controls, soft inputs, and modern nav styling.

Google Fonts runtime loading is not used.

## Shared Widgets

Shared UI primitives live in `lib/shared/widgets/`:

- `app_scaffold.dart`
- `app_top_bar.dart`
- `app_bottom_nav.dart`
- `app_button.dart`
- `app_card.dart`
- `app_text_field.dart`
- `app_chip.dart`
- `app_loading_view.dart`
- `app_error_view.dart`
- `app_empty_view.dart`
- `exit_confirm_dialog.dart`
- `pro_feature_dialog.dart`

Compatibility wrappers remain for older imports:

- `loading_view.dart`
- `error_view.dart`
- `empty_view.dart`

## Navigation / Back / Exit Improvements

Root tabs:

- Dashboard
- Practice
- Progress
- Review
- Settings

Navigation rules:

- Root tabs are rendered through the reusable `AppBottomNav`.
- Non-root pushed screens use the shared `AppScaffold(showBack: true)` pattern where already applied.
- Practice and test runners keep explicit X exit buttons with confirmation.
- Placeholder/fallback screens include a clear action instead of leaving the user stranded.

## What Was Intentionally Not Changed Yet

Deferred to later phases:

- Google Sign-In Flutter UI/plugin integration.
- Placement test audio and AI scoring.
- Practice runner Ask AI chatbox, highlight, and notebook tools.
- Review grouping by Practice / Full Test / Mini Test / Weekly Check.
- Voice Reader deep TTS debugging beyond foundation error UX.
- Backend API changes.
- React frontend changes.

## Verification

Run from `test/getgoals_mobile`:

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

## Next Recommended Phase

Phase B should polish the main screens visually without changing business logic:

- Splash
- Login/Register
- Onboarding
- Dashboard
- Practice Catalog
