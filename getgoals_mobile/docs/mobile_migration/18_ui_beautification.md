# Mobile UI Beautification Migration

## Scope

This pass upgrades the Flutter mobile app toward a premium TOEIC learning app UI while preserving existing API, auth, state, audio, and entitlement behavior.

## Packages

The requested UI package set is present in `pubspec.yaml`:

- `flex_color_scheme`
- `flutter_animate`
- `lucide_icons_flutter`
- `gap`
- `skeletonizer`
- `smooth_page_indicator`
- `cached_network_image`
- `percent_indicator`
- `fl_chart`
- `lottie`
- `webview_flutter`

## Design System

The mobile design system lives in `lib/core/theme/`:

- `app_colors.dart`
- `app_spacing.dart`
- `app_radius.dart`
- `app_shadows.dart`
- `app_text_styles.dart`
- `app_theme.dart`

The system uses a soft light background, white rounded cards, indigo/blue-violet primary surfaces, emerald/cyan accents, 20-24px card radii, 52px buttons, large touch targets, Material 3 theme defaults, and local system fonts to avoid GoogleFonts runtime loading.

## Shared Widgets

The shared UI foundation lives in `lib/shared/widgets/`:

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

Compatibility wrappers such as `loading_view.dart`, `error_view.dart`, and `empty_view.dart` route older screen code into the new friendly states.

## Screens Improved

- Splash uses a branded gradient startup surface with friendly retry copy.
- Login/Register/Forgot/Reset use a premium auth shell; secondary auth pages include Back.
- Onboarding uses smooth page indicators, card transitions, large controls, and step cards.
- Dashboard uses animated hero, metric cards, quick actions, empty state, and friendly errors.
- Practice Catalog preserves local part selection state and does not reload on part changes.
- Practice Runner keeps audio cards inside the existing runner lifecycle and adds X Exit confirmation.
- Practice Result uses score rings, smart next steps, breakdowns, and review actions.
- Mock/Test Runner uses X Exit confirmation and Pro-required dialog handling.
- Test Result now uses app cards, score hero, review/practice actions, and readable question review.
- Progress uses app cards, chart cards, empty chart states, and metric tiles.
- Review keeps the smart review queue with friendly loading/error/empty states.
- Flashcards uses a premium study card, progress bar, audio controls, and topic chips.
- Voice Reader uses app cards, friendly errors, and generated audio controls.
- Payment/Pricing disables upgrade actions for Pro users and shows a Pro-aware plan surface.
- Payment Status uses app navigation, friendly status loading/errors, and dashboard/plan actions.
- Settings uses app cards, large list targets, profile header, and no dead-end navigation.

## Navigation

- Root tabs: Dashboard, Practice, Progress, Review, Settings.
- Non-root feature screens expose Back through `AppScaffold` or Close/Exit where appropriate.
- Runner/test flows use X Exit and `ExitConfirmDialog`.
- Payment status includes explicit next actions back to Dashboard or Plans.

## Error, Loading, Empty

- `friendlyError()` prevents raw Dio/Socket/API exception details from being displayed to users.
- Shared loading states use `Skeletonizer`.
- Shared empty/error states use polished cards, icons, friendly copy, and optional retry/action buttons.

## Protected Behaviors

- Practice part selection stays local and does not reload the screen.
- Practice audio remains inside the existing runner/audio player widgets and is not rebuilt into a scrolling-global player.
- Pro users see disabled plan buttons and cannot trigger another upgrade checkout from Pricing.
- No backend, SQL Server, API contract, auth state, or React web frontend changes were made.

## Remaining UI TODOs

- Add richer Lottie assets once final brand motion is available.
- Add more detailed chart tooltips and legends for Progress.
- Add visual QA screenshots for common Android device sizes.
- Consider replacing compatibility wrappers with direct `App*` widget imports in a later cleanup pass.
