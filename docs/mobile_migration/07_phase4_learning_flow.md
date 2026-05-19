# 07 - Phase 4: Learning Flow

> Phase 4 - Practice, Attempts, Review, Diagnostic, Roadmap
> Generated: 2026-05-13 | Status: Complete

## Completed Scope

Phase 4 implemented the core learning flow in `getgoals_mobile/`:

- Practice Catalog backed by `GET /api/toeic/summary`
- Practice Runner backed by TOEIC runner endpoints
- Practice attempt submit backed by `POST /api/attempts/practice`
- Practice Summary backed by `GET /api/attempts/practice/{id}`
- Review Center backed by `GET /api/review/items`
- Notes and bookmarks backed by review CRUD endpoints
- Diagnostic runner backed by `GET /api/diagnostic/questions` and `POST /api/diagnostic/submit`
- Diagnostic attempt save backed by `POST /api/attempts/diagnostic`
- Basic Roadmap backed by `GET /api/roadmap/current` and `POST /api/roadmap/generate`

The Flutter app remains a pure mobile client. No Flutter-specific backend was created, and Flutter does not connect directly to SQL Server.

## Practice Endpoints Used

| Purpose | Method | Endpoint |
|---|---:|---|
| Practice catalog | GET | `/api/toeic/summary` |
| Part runner | GET | `/api/toeic/runner/part/{part}?limit=&difficulty=` |
| Mixed runner | GET | `/api/toeic/runner/mixed?parts=&count=&difficulty=` |
| Review-focus runner | GET | `/api/toeic/runner/review-focus?reviewItemId=&count=&difficulty=` |
| Roadmap set runner | GET | `/api/roadmap/week/{weekId}/set/{setId}` |

## Attempt Endpoints Used

| Purpose | Method | Endpoint |
|---|---:|---|
| Submit practice | POST | `/api/attempts/practice` |
| Fetch practice result | GET | `/api/attempts/practice/{attemptId}` |
| Save diagnostic attempt | POST | `/api/attempts/diagnostic` |

## Review Endpoints Used

| Purpose | Method | Endpoint |
|---|---:|---|
| Review items | GET | `/api/review/items?filter=&limit=` |
| Save note | POST | `/api/review/notes` |
| Toggle bookmark | POST | `/api/review/bookmarks/toggle` |
| Mark reviewed | POST | `/api/review/item/{id}/mark-reviewed` |

## Diagnostic And Roadmap Endpoints Used

| Purpose | Method | Endpoint |
|---|---:|---|
| Diagnostic questions | GET | `/api/diagnostic/questions` |
| Diagnostic submit | POST | `/api/diagnostic/submit` |
| Current roadmap | GET | `/api/roadmap/current` |
| Generate roadmap | POST | `/api/roadmap/generate` |
| Roadmap set questions | GET | `/api/roadmap/week/{weekId}/set/{setId}` |

## Files Created

Practice:

- `getgoals_mobile/lib/features/practice/data/toeic_repository.dart`
- `getgoals_mobile/lib/features/practice/data/models/toeic_question.dart`
- `getgoals_mobile/lib/features/practice/data/models/toeic_option.dart`
- `getgoals_mobile/lib/features/practice/data/models/practice_set.dart`
- `getgoals_mobile/lib/features/practice/data/models/practice_config.dart`
- `getgoals_mobile/lib/features/practice/state/practice_catalog_controller.dart`
- `getgoals_mobile/lib/features/practice/state/practice_runner_controller.dart`
- `getgoals_mobile/lib/features/practice/presentation/pages/practice_catalog_page.dart`
- `getgoals_mobile/lib/features/practice/presentation/pages/practice_runner_page.dart`
- `getgoals_mobile/lib/features/practice/presentation/pages/practice_summary_page.dart`
- `getgoals_mobile/lib/features/practice/presentation/widgets/practice_part_card.dart`
- `getgoals_mobile/lib/features/practice/presentation/widgets/question_option_card.dart`
- `getgoals_mobile/lib/features/practice/presentation/widgets/audio_player_card.dart`
- `getgoals_mobile/lib/features/practice/presentation/widgets/question_navigator.dart`

Attempts:

- `getgoals_mobile/lib/features/attempts/data/attempt_repository.dart`
- `getgoals_mobile/lib/features/attempts/data/models/submit_attempt_request.dart`
- `getgoals_mobile/lib/features/attempts/data/models/attempt_result.dart`
- `getgoals_mobile/lib/features/attempts/data/models/answer_submission.dart`
- `getgoals_mobile/lib/features/attempts/state/attempt_controller.dart`

Review:

- `getgoals_mobile/lib/features/review/data/review_repository.dart`
- `getgoals_mobile/lib/features/review/data/models/review_question.dart`
- `getgoals_mobile/lib/features/review/data/models/question_note.dart`
- `getgoals_mobile/lib/features/review/data/models/question_highlight.dart`
- `getgoals_mobile/lib/features/review/data/models/question_bookmark.dart`
- `getgoals_mobile/lib/features/review/state/review_controller.dart`
- `getgoals_mobile/lib/features/review/presentation/pages/review_page.dart`
- `getgoals_mobile/lib/features/review/presentation/widgets/review_question_card.dart`
- `getgoals_mobile/lib/features/review/presentation/widgets/note_editor.dart`
- `getgoals_mobile/lib/features/review/presentation/widgets/review_filter_bar.dart`
- `getgoals_mobile/lib/features/review/presentation/widgets/answer_explanation_card.dart`

Diagnostic:

- `getgoals_mobile/lib/features/diagnostic/data/diagnostic_repository.dart`
- `getgoals_mobile/lib/features/diagnostic/data/models/diagnostic_question.dart`
- `getgoals_mobile/lib/features/diagnostic/data/models/diagnostic_submit_request.dart`
- `getgoals_mobile/lib/features/diagnostic/data/models/diagnostic_result.dart`
- `getgoals_mobile/lib/features/diagnostic/state/diagnostic_controller.dart`
- `getgoals_mobile/lib/features/diagnostic/presentation/pages/diagnostic_page.dart`
- `getgoals_mobile/lib/features/diagnostic/presentation/pages/diagnostic_result_page.dart`

Roadmap:

- `getgoals_mobile/lib/features/roadmap/data/roadmap_repository.dart`
- `getgoals_mobile/lib/features/roadmap/data/models/roadmap.dart`
- `getgoals_mobile/lib/features/roadmap/data/models/roadmap_week.dart`
- `getgoals_mobile/lib/features/roadmap/data/models/roadmap_task.dart`
- `getgoals_mobile/lib/features/roadmap/state/roadmap_controller.dart`
- `getgoals_mobile/lib/features/roadmap/presentation/pages/roadmap_page.dart`
- `getgoals_mobile/lib/features/roadmap/presentation/widgets/roadmap_week_card.dart`

## Files Modified

- `getgoals_mobile/lib/app/router.dart`
- `getgoals_mobile/lib/app/route_names.dart`
- `getgoals_mobile/lib/core/network/endpoints.dart`
- `docs/mobile_migration/04_api_contract_needed.md`
- `docs/mobile_migration/phase_status.md`

## Mobile UX Implemented

Practice Runner supports:

- Passage text
- Image assets via `ApiClient.assetUrl()`
- Audio via `just_audio`
- Question text and A/B/C/D options
- Selected answer state
- Current question index
- Previous/next navigation
- Question navigator
- Timer
- Local flag state
- Confirm submit
- Local autosave-style in-memory answer state while the runner is open

Review Center supports:

- Wrong, Bookmarked, Notes, Highlights, and Weak Skills tabs
- Selected/correct answer display
- Explanation display
- Notes
- Bookmark toggle
- Ask AI button placeholder
- Practice similar via review-focus runner

Roadmap supports:

- Current roadmap
- Generate roadmap if missing
- Expandable week cards
- Suggested set launch into Practice Runner
- Done/pending status labels

## Missing APIs Or Fields

- `/api/review/items` still needs pagination beyond `limit`; mobile currently requests a bounded list.
- The Flutter endpoint constant was corrected to use the real mark-reviewed route: `/api/review/item/{id}/mark-reviewed`.
- Diagnostic submit and diagnostic attempt save are still separate calls; a combined authenticated endpoint would reduce mobile failure states.
- Practice runner local autosave is in-memory only. Durable resume-after-kill requires a local persistence policy or backend draft endpoint.
- Ask AI from Review is still a placeholder button; Phase 5 chat will wire it to `/api/chat`.
- Detailed Progress charts, Mock/Mini/Full Test, Weekly Check, Flashcards, TTS, Chat, Payment, and final polish remain for Phase 5.

## Verification

Run from `test/getgoals_mobile`:

```bash
D:\flutter\bin\flutter.bat analyze
D:\flutter\bin\flutter.bat test
```
