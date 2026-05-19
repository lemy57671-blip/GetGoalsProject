# GetGoals Mobile

Flutter client for the GetGoals TOEIC app. The app uses the shared FastAPI backend in `../backend`; it does not create its own backend, connect directly to SQL Server, or store database credentials.

## Requirements

- Flutter SDK 3.41.7 or newer
- Dart 3.11 or newer
- Android Studio or an Android emulator for mobile testing
- Windows desktop tooling if running `-d windows`
- Running GetGoals backend and SQL Server database

## Run The Backend

From `test/backend`:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Run Flutter

Android emulator:

```bash
cd getgoals_mobile
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8001
```

Windows/Desktop:

```bash
cd getgoals_mobile
flutter run --dart-define=API_BASE_URL=http://localhost:8001
```

Physical phone:

```bash
cd getgoals_mobile
flutter run --dart-define=API_BASE_URL=http://<COMPUTER_IP>:8001
```

`API_BASE_URL` is the FastAPI server origin. Use `10.0.2.2` for Android emulator because emulator `localhost` points to the emulator itself. Use your computer LAN IP for physical phones.

## Folder Structure

- `lib/app`: router, shell, app entry
- `lib/core`: config, network, storage, theme, utilities
- `lib/shared`: reusable widgets and shared placeholders
- `lib/features/auth`: login, register, session restore
- `lib/features/dashboard`: real API dashboard
- `lib/features/practice`: TOEIC catalog, runner, summary
- `lib/features/attempts`: submit/result models
- `lib/features/review`: review center, notes, bookmarks, contextual AI
- `lib/features/diagnostic`: placement test
- `lib/features/roadmap`: roadmap view and generation
- `lib/features/progress`: charts and analytics
- `lib/features/mock_test`: shared timed test runner/result
- `lib/features/weekly_check`: weekly check entry point
- `lib/features/flashcards`: topics, cards, TTS audio
- `lib/features/voice_reader`: TTS text reader
- `lib/features/chat`: AI Tutor chat
- `lib/features/payment`: pricing, checkout, subscription status
- `lib/features/settings`: profile, preferences, logout

## Architecture

The mobile app is a pure Flutter client. Repositories call FastAPI with `Dio`; authenticated requests use the JWT from `flutter_secure_storage`. Static assets from `/toeic`, `/audio`, and `/images` are resolved through `ApiClient.assetUrl()`. Riverpod controllers own screen state, and `go_router` handles bottom navigation plus full-screen runner routes.

## Common Errors

- Backend not running: start FastAPI on port `8001`.
- Android emulator cannot reach `localhost`: use `http://10.0.2.2:8001`.
- Physical phone cannot reach backend: use `http://<COMPUTER_IP>:8001` and keep both devices on the same network.
- Android HTTP blocked: `usesCleartextTraffic` is enabled for dev HTTP; use HTTPS for production.
- Token expired: log out and log back in.
- Audio/image not loading: confirm the backend serves `/audio`, `/images`, and `/toeic`, and that `API_BASE_URL` points to the same backend.
- Raw 403/Pro errors: Pro-gated screens show the Pro dialog or a friendly locked state.

## Verification

```bash
flutter analyze
flutter test
flutter build apk --debug
```
