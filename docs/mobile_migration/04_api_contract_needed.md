# 04 — API Contract Needed

> **Phase 1 — Mobile Migration Audit**
> Generated: 2026-05-13 | Status: Complete

---

## 1. Existing Endpoints Flutter Can Reuse As-Is

These endpoints return well-structured JSON and need **no changes** for Flutter consumption:

### Auth

| Endpoint | Method | Response Format | Notes |
|----------|--------|----------------|-------|
| `/api/auth/register` | POST | `{ token, user }` | ✅ Direct reuse. Store token in `flutter_secure_storage` |
| `/api/auth/login` | POST | `{ token, user }` | ✅ Direct reuse |
| `/api/auth/me` | GET | `{ id, name, email, avatarUrl, ... }` | ✅ Direct reuse |
| `/api/auth/profile` | PATCH | `{ message, user }` | ✅ Direct reuse |
| `/api/auth/learning-settings` | PATCH | `{ message, user }` | ✅ Direct reuse |
| `/api/auth/onboarding` | POST | `{ message, user }` | ✅ Direct reuse |
| `/api/auth/change-password` | POST | `{ message }` | ✅ Direct reuse |
| `/api/auth/google/config` | GET | `{ enabled, clientId }` | ✅ Direct reuse |
| `/api/auth/google/verify` | POST | `{ token, user }` | ✅ Direct reuse (use `google_sign_in` package) |

### Dashboard & Progress

| Endpoint | Method | Response Format | Notes |
|----------|--------|----------------|-------|
| `/api/dashboard/overview` | GET | Complex nested object | ✅ Direct reuse. All fields camelCase |
| `/api/progress/summary` | GET | Nested object with arrays | ✅ Direct reuse |
| `/api/progress/history` | GET | `HistoryPointDto[]` | ✅ Direct reuse |

### TOEIC Practice

| Endpoint | Method | Response Format | Notes |
|----------|--------|----------------|-------|
| `/api/toeic/summary` | GET | `{ inventory, parts[] }` | ✅ Direct reuse |
| `/api/toeic/recommendations` | GET | `{ track, reason, recommendedPacks[] }` | ✅ Direct reuse |
| `/api/toeic/runner/part/{part}` | GET | `ToeicRunnerQuestion[]` | ✅ Direct reuse |
| `/api/toeic/runner/mixed` | GET | `ToeicRunnerQuestion[]` | ✅ Direct reuse |
| `/api/toeic/runner/questions` | GET | `ToeicRunnerQuestion[]` | ✅ Direct reuse |
| `/api/toeic/runner/minitest` | GET | `ToeicRunnerQuestion[]` | ✅ Direct reuse |
| `/api/toeic/runner/fulltest` | GET | `ToeicRunnerQuestion[]` | ✅ Direct reuse |
| `/api/toeic/runner/review-focus` | GET | `{ items[], matchStrategy, ... }` | ✅ Direct reuse |

### Attempts

| Endpoint | Method | Response Format | Notes |
|----------|--------|----------------|-------|
| `/api/attempts/practice` | POST | `{ attemptId, reviewQueuedCount, result }` | ✅ Direct reuse |
| `/api/attempts/mock-test` | POST | `{ attemptId, ... }` | ✅ Direct reuse |
| `/api/attempts/diagnostic` | POST | Result object | ✅ Direct reuse |
| `/api/attempts/practice/{id}` | GET | `PracticeAttemptResult` | ✅ Direct reuse |
| `/api/attempts/mock-test/{id}` | GET | `PracticeAttemptResult` | ✅ Direct reuse |

### Roadmap

| Endpoint | Method | Response Format | Notes |
|----------|--------|----------------|-------|
| `/api/roadmap/current` | GET | `RoadmapCurrent` | ✅ Direct reuse |
| `/api/roadmap/generate` | POST | `RoadmapCurrent` | ✅ Direct reuse |
| `/api/roadmap/evidence` | GET | `{ items[] }` | ✅ Direct reuse |
| `/api/roadmap/week/{id}/sets` | GET | Nested object | ✅ Direct reuse |
| `/api/roadmap/week/{id}/set/{setId}` | GET | `{ questions[] }` | ✅ Direct reuse |
| `/api/roadmap/week/{id}/start` | POST | Week object | ✅ Direct reuse |
| `/api/roadmap/week/{id}/complete` | POST | Week object | ✅ Direct reuse |

### Review

| Endpoint | Method | Response Format | Notes |
|----------|--------|----------------|-------|
| `/api/review/items` | GET | `ReviewItemResponse[]` | ✅ Direct reuse |
| `/api/review/summary` | GET | Summary object | ✅ Direct reuse |
| `/api/review/notes` | GET/POST | `NoteResponse[]` | ✅ Direct reuse |
| `/api/review/highlights` | GET/POST | `HighlightResponse[]` | ✅ Direct reuse |
| `/api/review/bookmarks` | GET/POST | `BookmarkResponse` | ✅ Direct reuse |

### Other

| Endpoint | Method | Response Format | Notes |
|----------|--------|----------------|-------|
| `/api/subscription/current` | GET | `{ plan, planExpiredAt }` | ✅ Direct reuse |
| `/api/me/entitlements` | GET | Feature flags | ✅ Direct reuse |
| `/api/me/profile-summary` | GET | Profile summary | ✅ Direct reuse |
| `/api/settings/preferences` | GET/PUT | Preferences object | ✅ Direct reuse |
| `/api/settings/notifications` | GET/PUT | Notification prefs | ✅ Direct reuse |
| `/api/diagnostic/questions` | GET | Question array | ✅ Direct reuse |
| `/api/diagnostic/submit` | POST | Result object | ✅ Direct reuse |
| `/api/flashcards/topics` | GET | Topic array | ✅ Direct reuse |
| `/api/flashcards/topics/{code}/cards` | GET | Card array | ✅ Direct reuse |
| `/api/tts/flashcard` | POST | `{ audio_url, source }` | ✅ Direct reuse |
| `/api/tts/voices` | GET | `{ voices[] }` | ✅ Direct reuse |
| `/api/translate` | POST | `{ translated_text }` | ✅ Direct reuse |
| `/api/health` | GET | `{ status, time }` | ✅ Direct reuse |
| `/api/weekly-check/current` | GET | Weekly check object | ✅ Direct reuse |
| `/api/weekly-check/submit` | POST | Result | ✅ Direct reuse |
| `/api/weekly-check/result/{id}` | GET | Attempt result | ✅ Direct reuse |

---

## 2. Endpoints to Verify

These endpoints work but have potential issues for Flutter:

| Endpoint | Concern | Verification Needed |
|----------|---------|-------------------|
| `/api/chat` (POST) | Uses SSE streaming (`text/event-stream`) | Test with `dio` StreamedResponse or `eventsource` package |
| `/api/tts/tts` (POST) | Returns raw `audio/mpeg` bytes | Test binary response handling with `dio` `ResponseType.bytes` |
| `/api/payments/create-pro-order` | Returns `checkoutUrl` pointing to localhost | Need to add mobile return URL support |
| `/api/payments/payos-webhook` | Server-to-server webhook | No Flutter change, but verify payment flow end-to-end |
| All static file URLs (`/toeic/`, `/audio/`, `/images/`) | Relative URLs need base URL prefix | Flutter must prepend `API_BASE_URL` to all asset paths |
| `/api/review/items` | Very large response (can be 500+ items) | Test performance with large lists, consider pagination |

---

## 3. Endpoints/Fields to Add or Improve

### New Endpoints Needed

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/app/version-check` | GET | Returns `{ minVersion, latestVersion, forceUpdate }` for mobile app version gating | High |
| `/api/auth/device-token` | POST | Register FCM/APNs device token for push notifications | High |
| `/api/auth/login` (enhancement) | POST | Add `device` and `platform` fields to login request for analytics | Medium |
| `/api/payments/create-pro-order` (enhancement) | POST | Add `platform: "mobile"` param to use mobile deep-link return URLs | High |
| `/api/me/profile-summary` (enhancement) | GET | Add `totalStudyDays`, `longestStreak` fields | Low |

### Existing Endpoint Improvements

| Endpoint | Current Issue | Suggested Improvement |
|----------|--------------|----------------------|
| `/api/review/items` | No pagination, returns up to 500 items | Add `offset` + `limit` query params |
| `/api/dashboard/summary` | Uses `userId` query param (no auth) | Migrate to JWT auth like `/overview` |
| `/api/dashboard/courses` | Uses `userId` query param (no auth) | Migrate to JWT auth |
| `/api/dashboard/weekly-hours` | Uses `userId` query param (no auth) | Migrate to JWT auth |
| `/api/progress/log` | Uses `userId` query param (no auth) | Migrate to JWT auth |
| `/api/auth/forgot-password` | Stub only, returns fake success | Implement real email sending (or OTP for mobile) |
| `/api/toeic/runner/*` | No caching headers | Add `Cache-Control` or `ETag` for question data |

### Phase 4 Learning Flow Notes

| Endpoint | Current Issue | Suggested Improvement |
|----------|--------------|----------------------|
| `/api/review/item/{id}/mark-reviewed` | This is the real backend route, while older docs referenced `/api/review/items/{id}/reviewed` | Keep Flutter and docs aligned to `/api/review/item/{id}/mark-reviewed` |
| `/api/diagnostic/submit` + `/api/attempts/diagnostic` | Mobile must call two endpoints to analyze and then persist a diagnostic attempt | Consider a single authenticated submit-and-save endpoint |
| Practice runner draft state | Backend has no draft/resume endpoint for in-progress practice | Add optional draft attempt endpoints if mobile needs resume after app kill |

---

## 4. Required Response Fields for Flutter

### User Object (from auth endpoints)

```json
{
  "id": 1,                          // int ✅
  "name": "Hoàng Mỹ",              // string ✅
  "email": "user@example.com",      // string ✅
  "avatarUrl": "",                   // string ✅
  "provider": "local",              // string ✅ "local" | "google"
  "plan": "free",                   // string ✅ "free" | "pro"
  "planExpiredAt": null,             // string? ✅ ISO 8601
  "onboardingCompleted": true,       // bool ✅
  "currentScore": 450,              // int? ✅
  "targetScore": 700,               // int? ✅
  "examDate": "2026-12-15",         // string? ✅ YYYY-MM-DD
  "studyMinutesPerDay": 30,         // int? ✅
  "weakSkills": ["vocabulary"],      // string[] ✅
  "createdAtUtc": "2026-01-01T..."  // string? ✅ ISO 8601
}
```

### Runner Question Object

```json
{
  "id": 12345,                       // int ✅ Runtime question ID
  "questionId": 67890,               // int? ✅ SQL question ID
  "section": "Listening",            // string ✅
  "part": 3,                         // int ✅
  "partLabel": "Part 3",             // string? ✅
  "type": "question",                // string ✅
  "question": "What does...",        // string ✅ Question text
  "skill": "listening_comprehension", // string ✅
  "subskill": "main_idea",          // string? ✅
  "options": ["(A)...", "(B)..."],   // string[] ✅
  "correctAnswerIndex": 2,           // int? ✅
  "correctAnswer": "C",             // string? ✅
  "explanation": "The correct...",   // string? ✅
  "explanationDetail": "...",        // string? ✅
  "audio": { "path": "/audio/..." }, // object? ✅
  "image": { "path": "/images/..." },// object? ✅
  "passage": {                       // object? ✅
    "id": 100,
    "groupCode": "P3_T1_G1",
    "title": "Conversation",
    "text": "M: Hello, I'd like...",
    "audio": { "path": "/audio/..." },
    "image": { "path": "/images/..." }
  },
  "test": 1,                         // int ✅
  "questionNumber": 15,              // int ✅
  "groupId": "P3_T1_G1"             // string? ✅
}
```

---

## 5. snake_case / camelCase Compatibility Notes

### Current Situation

The backend was built primarily for the React frontend and uses **camelCase** in most JSON responses:

| Layer | Convention | Example |
|-------|-----------|---------|
| **Database (SQL Server)** | PascalCase | `UserId`, `CorrectOptionKey` |
| **SQLAlchemy Models** | snake_case + PascalCase synonyms | `user_id` / `UserId` |
| **Pydantic Schemas** | snake_case with `alias` | `question_id` → accepts `questionId` |
| **Route Responses** | **camelCase** (manually built dicts) | `{ "avatarUrl": "", "weakSkills": [] }` |
| **Query Parameters** | **Mixed** | `userId`, `attemptId` (camelCase) / `question_id`, `attempt_id` (snake_case) |

### Backend Query Param Dual Support

Many review endpoints accept **both** cases via dual query params:

```python
attempt_id: int | None = Query(default=None, alias="attempt_id"),
attempt_id_camel: int | None = Query(default=None, alias="attemptId"),
```

### Flutter Strategy

**Recommended: Use camelCase in Dart models with `json_serializable`**

```dart
@JsonSerializable()
class User {
  final int id;
  final String name;
  final String email;
  final String? avatarUrl;           // matches backend camelCase
  final String? plan;
  final bool? onboardingCompleted;   // matches backend camelCase
  final int? currentScore;
  // ...

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
  Map<String, dynamic> toJson() => _$UserToJson(this);
}
```

### Key Fields to Watch

| Backend Field | Dart Field | Notes |
|--------------|-----------|-------|
| `avatarUrl` | `avatarUrl` | ✅ Already camelCase |
| `planExpiredAt` | `planExpiredAt` | ✅ Already camelCase |
| `onboardingCompleted` | `onboardingCompleted` | ✅ Already camelCase |
| `studyMinutesPerDay` | `studyMinutesPerDay` | ✅ Already camelCase |
| `weakSkills` | `weakSkills` | ✅ Already camelCase |
| `question_id` (query) | Use `questionId` | ✅ Both accepted |
| `runtime_question_id` (query) | Use `runtimeQuestionId` | ✅ Both accepted |
| `note_text` (Pydantic) | Use `noteText` or `note_text` | ⚠️ Check if alias exists |
| `selected_text` (Pydantic) | Use `selectedText` | ⚠️ Check if alias exists |

### Action Items

1. **No backend breaking changes needed** — responses already use camelCase
2. **Flutter models**: Use `json_serializable` with `fieldRename: FieldRename.none` (keep as-is)
3. **Request bodies**: Send camelCase (already matches React frontend format)
4. **Query params**: Prefer camelCase variants (e.g., `attemptId` instead of `attempt_id`)
5. **Verify edge cases**: A few Pydantic schemas use snake_case field names — test these endpoints from Flutter to confirm alias support

---

## 6. Authentication Contract

### Token Format

```
Authorization: Bearer <JWT>
```

### JWT Payload

```json
{
  "sub": "1",                        // User ID (string)
  "email": "user@example.com",
  "name": "Hoàng Mỹ",
  "provider": "local",
  "onboardingCompleted": "true",     // NOTE: string, not boolean
  "iss": "GetGoals",
  "aud": "GetGoals.Web",             // Consider adding "GetGoals.Mobile"
  "iat": 1718000000,
  "exp": 1718604800
}
```

### Flutter Auth Flow

```
1. POST /api/auth/login → { token, user }
2. Store token in flutter_secure_storage
3. Attach token to all authenticated requests: Authorization: Bearer <token>
4. On 401 response → clear token → navigate to login
5. On app launch → read token → GET /api/auth/me → restore session or redirect
```

### Backend Consideration

- Consider adding `"aud": "GetGoals.Mobile"` for mobile tokens
- This would require updating `security.py` to accept multiple audiences
- Alternative: Keep `"GetGoals.Web"` for both (simpler, no backend change)

---

## 7. Error Response Contract

### Current Error Format

```json
// Validation error
{
  "message": "Validation failed",
  "errors": [{ "loc": ["body", "email"], "msg": "...", "type": "..." }]
}

// Business error
{
  "message": "Email already exists"
}

// Server error
{
  "message": "Database connection failed.",
  "detail": "..."
}

// Payment error (with code)
{
  "message": "...",
  "code": "PRO_ALREADY_ACTIVE",
  "expiresAt": "2026-12-31T..."
}
```

### Flutter Error Handling

```dart
class ApiException implements Exception {
  final int statusCode;
  final String message;
  final String? code;        // domain error code
  final dynamic detail;      // raw error detail

  // Parse from response body
  factory ApiException.fromResponse(int status, Map<String, dynamic> body) {
    return ApiException(
      statusCode: status,
      message: body['message'] ?? 'Request failed',
      code: body['code'],
      detail: body['detail'],
    );
  }
}
```
