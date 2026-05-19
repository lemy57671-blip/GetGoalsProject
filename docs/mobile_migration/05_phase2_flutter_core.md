# 05 — Phase 2: Flutter Core Architecture

> **Phase 2 — Flutter Bootstrap & Core Setup**
> Generated: 2026-05-13 | Status: Complete

---

## What Was Done

Phase 2 bootstrapped the Flutter mobile project and created all foundational architecture required for feature development in Phase 3.

### 1. Flutter Project Created

```
test/getgoals_mobile/     ← Created with: flutter create --org com.getgoals --project-name getgoals_mobile --platforms android,ios
```

- **SDK**: Flutter 3.41.7 (Dart 3.11.5)
- **Platforms**: Android + iOS
- **Min Android SDK**: default (API 21+)

### 2. Packages Installed

| Package | Version | Purpose |
|---------|---------|---------|
| `go_router` | ^17.2.3 | Declarative routing with bottom nav shell |
| `flutter_riverpod` | ^3.3.1 | State management |
| `dio` | ^5.9.2 | HTTP client with interceptors |
| `flutter_secure_storage` | ^10.2.0 | Secure JWT token storage |
| `just_audio` | ^0.10.5 | Audio playback (TOEIC listening) |
| `fl_chart` | ^1.2.0 | Charts (progress, scores) |
| `intl` | ^0.20.2 | Date/number formatting |
| `url_launcher` | ^6.3.2 | External links |
| `shared_preferences` | ^2.5.5 | Lightweight non-sensitive settings |
| `cached_network_image` | ^3.4.1 | Image caching |
| `google_fonts` | ^8.1.0 | Inter font family |
| `shimmer` | ^3.0.0 | Loading skeletons |
| `json_annotation` | ^4.11.0 | Model serialization annotations |
| `build_runner` | ^2.15.0 | (dev) Code generation |
| `json_serializable` | ^6.13.2 | (dev) JSON serialization codegen |

### 3. Android Configuration

- `android:usesCleartextTraffic="true"` added to `AndroidManifest.xml` for HTTP dev server access
- `android:label` changed to "GetGoals"

### 4. Project Structure

```
getgoals_mobile/lib/
├── main.dart                          ← Entry point (ProviderScope + GetGoalsApp)
│
├── app/
│   ├── app.dart                       ← MaterialApp.router with theme + router
│   ├── router.dart                    ← go_router: 30+ routes (public + shell + full-screen)
│   ├── route_names.dart               ← Named route constants
│   └── app_shell.dart                 ← Bottom navigation (5 tabs: Home/Practice/Progress/Review/Settings)
│
├── core/
│   ├── config/app_config.dart         ← API base URL from --dart-define, defaults per platform
│   ├── network/
│   │   ├── api_client.dart            ← Dio wrapper: auth interceptor, error parsing, asset URLs
│   │   ├── api_exception.dart         ← Structured error (matches backend format)
│   │   └── endpoints.dart             ← 50+ endpoint constants
│   ├── storage/token_storage.dart     ← flutter_secure_storage for JWT
│   ├── theme/
│   │   ├── app_theme.dart             ← Material 3 light + dark ThemeData
│   │   ├── app_colors.dart            ← Brand palette, skill/part colors, gradients
│   │   └── app_text_styles.dart       ← Typography system (display → caption → score)
│   ├── utils/
│   │   ├── validators.dart            ← Input validators (email, password, name)
│   │   ├── date_formatters.dart       ← Date formatting + timeAgo
│   │   ├── asset_url_helper.dart      ← Resolve /toeic/, /audio/, /images/ to full URLs
│   │   └── extensions.dart            ← String, Context, Num extensions
│   └── constants/app_constants.dart   ← Spacing, radius, TOEIC constants
│
├── shared/
│   ├── widgets/
│   │   ├── app_button.dart            ← Button with loading state + sizes
│   │   ├── app_text_field.dart        ← Styled text input with label
│   │   ├── loading_view.dart          ← Full-screen loading
│   │   ├── error_view.dart            ← Error state with retry
│   │   ├── empty_view.dart            ← Empty state with CTA
│   │   ├── loading_skeleton.dart      ← Shimmer skeleton (card, circle variants)
│   │   ├── score_card.dart            ← Score display with icon + color
│   │   ├── skill_chip.dart            ← Colored skill/tag chip
│   │   ├── section_header.dart        ← Section title with trailing action
│   │   ├── confirm_dialog.dart        ← Confirmation dialog with destructive variant
│   │   ├── pro_feature_dialog.dart    ← Pro upgrade prompt
│   │   └── placeholder_screen.dart    ← Generic placeholder for unbuilt screens
│   ├── models/models.dart             ← (placeholder for shared data models)
│   └── providers/providers.dart       ← (placeholder for shared Riverpod providers)
│
└── features/
    ├── splash/splash_screen.dart      ← Health check + token validation + routing
    ├── auth/                          ← Phase 3
    ├── onboarding/                    ← Phase 3
    ├── diagnostic/                    ← Phase 3
    ├── dashboard/                     ← Phase 3
    ├── practice/                      ← Phase 3
    ├── attempts/                      ← Phase 3
    ├── mock_test/                     ← Phase 3
    ├── weekly_check/                  ← Phase 3
    ├── progress/                      ← Phase 3
    ├── roadmap/                       ← Phase 3
    ├── review/                        ← Phase 3
    ├── flashcards/                    ← Phase 3
    ├── chat/                          ← Phase 3
    ├── payment/                       ← Phase 3
    └── settings/                      ← Phase 3
```

---

## Key Architecture Decisions

### API Client (`core/network/api_client.dart`)

- Uses Dio with 30s request timeout and 15s connection timeout
- **Auth interceptor**: Reads `auth: true` from request extras → attaches `Authorization: Bearer <token>` from secure storage
- **Error parsing**: DioException → ApiException with status code, message, and optional error code
- **Asset URL helper**: `ApiClient.assetUrl('/audio/test1/q1.mp3')` → `http://10.0.2.2:8001/audio/test1/q1.mp3`
- **Debug logging**: Logs all requests/responses to dart:developer

### API Base URL Resolution

```
Priority:
1. --dart-define=API_BASE_URL=http://192.168.1.100:8001   (explicit)
2. Android emulator → http://10.0.2.2:8001                (auto-detect)
3. Desktop/iOS sim  → http://localhost:8001                (fallback)
```

### Token Storage

- Key: `getgoals.authToken` (matches web frontend's `localStorage` key name)
- Uses `flutter_secure_storage` with `EncryptedSharedPreferences` on Android
- Token is never stored in SharedPreferences

### Router

- **Public routes**: `/login`, `/register`, `/forgot-password`, `/reset-password`, `/pricing`
- **Full-screen routes**: `/practice/runner`, `/mock-test/runner`, etc. (overlay bottom nav)
- **Shell routes**: 5-tab `StatefulShellRoute.indexedStack` for persistent navigation
- Each tab maintains its own Navigator stack

### Splash Screen + Health Check

- On launch → calls `GET /api/health` to verify backend connectivity
- If token exists → validates with `GET /api/auth/me` → navigates to `/dashboard`
- If no token → navigates to `/login`
- On error → shows connection details (API URL), retry button, and "Skip to Login"

---

## How to Test

### Prerequisites

1. Backend running:
   ```bash
   cd test/backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

2. SQL Server with `DataGetGoals` database accessible

### Run on Android Emulator

```bash
cd test/getgoals_mobile
D:\flutter\bin\flutter.bat run
```

The app will:
1. Show splash screen with gradient background
2. Call `GET http://10.0.2.2:8001/api/health` (emulator → host machine)
3. If backend is up → navigate to Login (placeholder)
4. If backend is down → show error + retry + "Skip to Login"

### Run on Physical Phone

```bash
cd test/getgoals_mobile
D:\flutter\bin\flutter.bat run --dart-define=API_BASE_URL=http://<YOUR_COMPUTER_IP>:8001
```

### Run on Windows Desktop

```bash
cd test/getgoals_mobile
D:\flutter\bin\flutter.bat run -d windows
```

### Verify Analysis

```bash
cd test/getgoals_mobile
D:\flutter\bin\flutter.bat analyze
D:\flutter\bin\flutter.bat test
```

---

## Files Created (45 files)

### Core Framework (4)
- `lib/main.dart`
- `lib/app/app.dart`
- `lib/app/router.dart`
- `lib/app/route_names.dart`
- `lib/app/app_shell.dart`

### Network Layer (3)
- `lib/core/network/api_client.dart`
- `lib/core/network/api_exception.dart`
- `lib/core/network/endpoints.dart`

### Config & Storage (2)
- `lib/core/config/app_config.dart`
- `lib/core/storage/token_storage.dart`

### Theme (3)
- `lib/core/theme/app_theme.dart`
- `lib/core/theme/app_colors.dart`
- `lib/core/theme/app_text_styles.dart`

### Utilities (4)
- `lib/core/utils/validators.dart`
- `lib/core/utils/date_formatters.dart`
- `lib/core/utils/asset_url_helper.dart`
- `lib/core/utils/extensions.dart`

### Constants (1)
- `lib/core/constants/app_constants.dart`

### Shared Widgets (12)
- `lib/shared/widgets/app_button.dart`
- `lib/shared/widgets/app_text_field.dart`
- `lib/shared/widgets/loading_view.dart`
- `lib/shared/widgets/error_view.dart`
- `lib/shared/widgets/empty_view.dart`
- `lib/shared/widgets/loading_skeleton.dart`
- `lib/shared/widgets/score_card.dart`
- `lib/shared/widgets/skill_chip.dart`
- `lib/shared/widgets/section_header.dart`
- `lib/shared/widgets/confirm_dialog.dart`
- `lib/shared/widgets/pro_feature_dialog.dart`
- `lib/shared/widgets/placeholder_screen.dart`

### Shared Placeholders (2)
- `lib/shared/models/models.dart`
- `lib/shared/providers/providers.dart`

### Feature Screens (1 active + 15 placeholder dirs)
- `lib/features/splash/splash_screen.dart` — Active (health check)
- `lib/features/auth/` through `lib/features/settings/` — 15 placeholder directories

### Config Modified (1)
- `android/app/src/main/AndroidManifest.xml` — cleartext traffic enabled

### Docs (2)
- `docs/mobile_migration/05_phase2_flutter_core.md` — This document
- `docs/mobile_migration/phase_status.md` — Updated status tracker
