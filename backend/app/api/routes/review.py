from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models import (
    MockTestAttempt,
    MockTestAttemptAnswer,
    PracticeAttempt,
    PracticeAttemptAnswer,
    ReviewQueueItem,
    ToeicQuestion,
    UserQuestionBookmark,
    UserQuestionHighlight,
    UserQuestionNote,
)
from app.schemas.review import (
    ReviewAssetResponse,
    BookmarkResponse,
    BookmarkToggleRequest,
    HighlightCreate,
    HighlightResponse,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    ReviewItemResponse,
    ReviewOptionResponse,
    ReviewPassageResponse,
)
from app.services.learning_analytics import get_review_item_detail, get_review_summary, mark_review_item_reviewed
from app.services.review_schema import ensure_review_schema


router = APIRouter()
logger = logging.getLogger(__name__)
RUNTIME_REVIEW_SOURCES = {"practice", "fulltest", "minitest", "weeklycheck"}
REVIEW_SOURCE_ORDER = {"practice": 0, "fulltest": 1, "minitest": 2, "weeklycheck": 3, "diagnostic": 4}
_OPTION_WARNING_KEYS: set[tuple[int, str]] = set()


@router.get("/api/review/debug/question-context")
def debug_review_question_context(
    source: str | None = Query(default=None),
    attempt_id: int | None = Query(default=None, alias="attempt_id"),
    attempt_id_camel: int | None = Query(default=None, alias="attemptId"),
    runtime_question_id: int | None = Query(default=None, alias="runtime_question_id"),
    runtime_question_id_camel: int | None = Query(default=None, alias="runtimeQuestionId"),
    question_id: int | None = Query(default=None, alias="question_id"),
    question_id_camel: int | None = Query(default=None, alias="questionId"),
    question_number: int | None = Query(default=None, alias="questionNumber"),
    part: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    from app.api.routes.chat import get_review_question_context

    resolved_attempt_id = attempt_id if attempt_id is not None else attempt_id_camel
    resolved_runtime_id = runtime_question_id if runtime_question_id is not None else runtime_question_id_camel
    resolved_question_id = question_id if question_id is not None else question_id_camel
    context = get_review_question_context(
        db,
        user_id=user_id,
        source=source,
        attempt_id=resolved_attempt_id,
        runtime_question_id=resolved_runtime_id,
        question_id=resolved_question_id,
        part=part,
        question_number=question_number,
        frontend_context={
            "context_type": "review",
            "source": source,
            "attempt_id": resolved_attempt_id,
            "runtime_question_id": resolved_runtime_id,
            "question_id": resolved_question_id,
            "part": part,
            "question_number": question_number,
        },
    )
    return {
        "source": context.get("source"),
        "attemptId": context.get("attempt_id"),
        "runtimeQuestionId": context.get("runtime_question_id"),
        "questionId": context.get("question_id"),
        "questionNumber": context.get("question_number"),
        "part": context.get("part"),
        "questionText": context.get("question_text") or context.get("question_text_en"),
        "options": context.get("options") or [],
        "correctOptionKey": context.get("correct_option_key") or context.get("correct_option_label"),
        "correctAnswerText": context.get("correct_answer_text"),
        "detailedExplanation": context.get("detailed_explanation"),
        "optionExplanations": context.get("option_explanations") or {},
        "translation": context.get("question_translation"),
        "vocabulary": context.get("vocabulary") or {},
        "passageText": context.get("passage_text"),
        "sqlSource": context.get("sql_source"),
    }


@router.get("/api/review/notes", response_model=list[NoteResponse])
def get_notes_route(
    question_id: int = Query(..., gt=0),
    source: str | None = Query(default=None),
    attempt_id: int | None = Query(default=None, alias="attempt_id"),
    attempt_id_camel: int | None = Query(default=None, alias="attemptId"),
    runtime_question_id: int | None = Query(default=None, alias="runtime_question_id"),
    runtime_question_id_camel: int | None = Query(default=None, alias="runtimeQuestionId"),
    diagnostic_question_id: int | None = Query(default=None, alias="diagnostic_question_id"),
    diagnostic_question_id_camel: int | None = Query(default=None, alias="diagnosticQuestionId"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    resolved_attempt_id = attempt_id if attempt_id is not None else attempt_id_camel
    review_source, runtime_question_id, diagnostic_question_id, canonical_question_id = _normalize_review_identity(
        question_id=question_id,
        source=source,
        runtime_question_id=runtime_question_id or runtime_question_id_camel,
        diagnostic_question_id=diagnostic_question_id or diagnostic_question_id_camel,
    )
    conditions = [
        UserQuestionNote.user_id == user_id,
        UserQuestionNote.is_active == True,
        *_identity_filter(UserQuestionNote, review_source, canonical_question_id, runtime_question_id, diagnostic_question_id),
    ]
    if resolved_attempt_id is not None:
        conditions.extend(_attempt_filter(UserQuestionNote, resolved_attempt_id))
    return db.scalars(
        select(UserQuestionNote)
        .where(*conditions)
        .order_by(UserQuestionNote.updated_at.desc(), UserQuestionNote.id.desc())
    ).all()


@router.post("/api/review/notes", response_model=NoteResponse)
def save_note_route(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    note_text = payload.note_text.strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required.")
    review_source, runtime_question_id, diagnostic_question_id, canonical_question_id = _normalize_review_identity(
        question_id=payload.question_id,
        source=payload.source,
        runtime_question_id=payload.runtime_question_id,
        diagnostic_question_id=payload.diagnostic_question_id,
    )

    note = db.scalar(
        select(UserQuestionNote).where(
            UserQuestionNote.user_id == user_id,
            UserQuestionNote.is_active == True,
            *_identity_filter(UserQuestionNote, review_source, canonical_question_id, runtime_question_id, diagnostic_question_id),
            *_attempt_filter(UserQuestionNote, payload.attempt_id),
        )
    )
    now = datetime.utcnow()
    if note is None:
        note = UserQuestionNote(
            user_id=user_id,
            question_id=canonical_question_id,
            source=review_source,
            attempt_id=payload.attempt_id,
            runtime_question_id=runtime_question_id,
            diagnostic_question_id=diagnostic_question_id,
            note_text=note_text,
            created_at=now,
            updated_at=now,
            created_at_utc=now,
            updated_at_utc=now,
            is_active=True,
        )
        db.add(note)
    else:
        note.note_text = note_text
        note.attempt_id = payload.attempt_id or note.attempt_id
        note.source = review_source
        note.runtime_question_id = runtime_question_id
        note.diagnostic_question_id = diagnostic_question_id
        note.question_id = canonical_question_id
        note.updated_at = now
        note.updated_at_utc = now
        note.is_active = True
    _upsert_review_queue_marker(
        db,
        user_id=user_id,
        source=review_source,
        question_id=canonical_question_id,
        runtime_question_id=runtime_question_id,
        diagnostic_question_id=diagnostic_question_id,
        attempt_id=payload.attempt_id,
        review_reason="noted",
        at_utc=now,
    )
    db.commit()
    db.refresh(note)
    return note


@router.put("/api/review/notes/{note_id}", response_model=NoteResponse)
def update_note_route(
    note_id: int,
    payload: NoteUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    note = db.scalar(select(UserQuestionNote).where(UserQuestionNote.id == note_id, UserQuestionNote.user_id == user_id))
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    note_text = payload.note_text.strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required.")
    note.note_text = note_text
    note.updated_at = datetime.utcnow()
    note.updated_at_utc = note.updated_at
    db.commit()
    db.refresh(note)
    return note


@router.delete("/api/review/notes/{note_id}")
def delete_note_route(
    note_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    note = db.scalar(select(UserQuestionNote).where(UserQuestionNote.id == note_id, UserQuestionNote.user_id == user_id))
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    note.is_active = False
    note.updated_at = datetime.utcnow()
    note.updated_at_utc = note.updated_at
    _deactivate_review_queue_marker_if_empty(
        db,
        user_id=user_id,
        source=note.source,
        question_id=note.question_id,
        runtime_question_id=note.runtime_question_id,
        diagnostic_question_id=note.diagnostic_question_id,
        attempt_id=note.attempt_id,
        review_reason="noted",
        model=UserQuestionNote,
        exclude_id=note.id,
    )
    db.commit()
    return {"deleted": True, "id": note_id}


@router.get("/api/review/highlights", response_model=list[HighlightResponse])
def get_highlights_route(
    question_id: int = Query(..., gt=0),
    source: str | None = Query(default=None),
    attempt_id: int | None = Query(default=None, alias="attempt_id"),
    attempt_id_camel: int | None = Query(default=None, alias="attemptId"),
    runtime_question_id: int | None = Query(default=None, alias="runtime_question_id"),
    runtime_question_id_camel: int | None = Query(default=None, alias="runtimeQuestionId"),
    diagnostic_question_id: int | None = Query(default=None, alias="diagnostic_question_id"),
    diagnostic_question_id_camel: int | None = Query(default=None, alias="diagnosticQuestionId"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    resolved_attempt_id = attempt_id if attempt_id is not None else attempt_id_camel
    review_source, runtime_question_id, diagnostic_question_id, canonical_question_id = _normalize_review_identity(
        question_id=question_id,
        source=source,
        runtime_question_id=runtime_question_id or runtime_question_id_camel,
        diagnostic_question_id=diagnostic_question_id or diagnostic_question_id_camel,
    )
    conditions = [
        UserQuestionHighlight.user_id == user_id,
        UserQuestionHighlight.is_active == True,
        *_identity_filter(UserQuestionHighlight, review_source, canonical_question_id, runtime_question_id, diagnostic_question_id),
    ]
    if resolved_attempt_id is not None:
        conditions.extend(_attempt_filter(UserQuestionHighlight, resolved_attempt_id))
    return db.scalars(
        select(UserQuestionHighlight)
        .where(*conditions)
        .order_by(UserQuestionHighlight.updated_at.desc(), UserQuestionHighlight.id.desc())
    ).all()


@router.post("/api/review/highlights", response_model=HighlightResponse)
def create_highlight_route(
    payload: HighlightCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    selected_text = payload.selected_text.strip()
    if not selected_text:
        raise HTTPException(status_code=400, detail="selected_text is required.")
    now = datetime.utcnow()
    review_source, runtime_question_id, diagnostic_question_id, canonical_question_id = _normalize_review_identity(
        question_id=payload.question_id,
        source=payload.source,
        runtime_question_id=payload.runtime_question_id,
        diagnostic_question_id=payload.diagnostic_question_id,
    )
    highlight = UserQuestionHighlight(
        user_id=user_id,
        question_id=canonical_question_id,
        source=review_source,
        attempt_id=payload.attempt_id,
        runtime_question_id=runtime_question_id,
        diagnostic_question_id=diagnostic_question_id,
        target_type=(payload.target_type or "question_text").strip()[:50],
        target_key=(payload.target_key or "").strip()[:20] or None,
        selected_text=selected_text,
        highlight_text=selected_text,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        color=(payload.color or "yellow").strip()[:30],
        note_text=payload.note_text.strip() if payload.note_text and payload.note_text.strip() else None,
        created_at=now,
        updated_at=now,
        created_at_utc=now,
        updated_at_utc=now,
        is_active=True,
    )
    db.add(highlight)
    _upsert_review_queue_marker(
        db,
        user_id=user_id,
        source=review_source,
        question_id=canonical_question_id,
        runtime_question_id=runtime_question_id,
        diagnostic_question_id=diagnostic_question_id,
        attempt_id=payload.attempt_id,
        review_reason="highlighted",
        at_utc=now,
    )
    db.commit()
    db.refresh(highlight)
    return highlight


@router.delete("/api/review/highlights/{highlight_id}")
def delete_highlight_route(
    highlight_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    highlight = db.scalar(
        select(UserQuestionHighlight).where(
            UserQuestionHighlight.id == highlight_id,
            UserQuestionHighlight.user_id == user_id,
        )
    )
    if highlight is None:
        raise HTTPException(status_code=404, detail="Highlight not found.")
    highlight.is_active = False
    highlight.updated_at = datetime.utcnow()
    highlight.updated_at_utc = highlight.updated_at
    _deactivate_review_queue_marker_if_empty(
        db,
        user_id=user_id,
        source=highlight.source,
        question_id=highlight.question_id,
        runtime_question_id=highlight.runtime_question_id,
        diagnostic_question_id=highlight.diagnostic_question_id,
        attempt_id=highlight.attempt_id,
        review_reason="highlighted",
        model=UserQuestionHighlight,
        exclude_id=highlight.id,
    )
    db.commit()
    return {"deleted": True, "id": highlight_id}


@router.get("/api/review/bookmarks", response_model=BookmarkResponse)
def get_bookmark_route(
    question_id: int = Query(..., gt=0),
    source: str | None = Query(default=None),
    attempt_id: int | None = Query(default=None, alias="attempt_id"),
    attempt_id_camel: int | None = Query(default=None, alias="attemptId"),
    runtime_question_id: int | None = Query(default=None, alias="runtime_question_id"),
    runtime_question_id_camel: int | None = Query(default=None, alias="runtimeQuestionId"),
    diagnostic_question_id: int | None = Query(default=None, alias="diagnostic_question_id"),
    diagnostic_question_id_camel: int | None = Query(default=None, alias="diagnosticQuestionId"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    resolved_attempt_id = attempt_id if attempt_id is not None else attempt_id_camel
    review_source, runtime_question_id, diagnostic_question_id, canonical_question_id = _normalize_review_identity(
        question_id=question_id,
        source=source,
        runtime_question_id=runtime_question_id or runtime_question_id_camel,
        diagnostic_question_id=diagnostic_question_id or diagnostic_question_id_camel,
    )
    conditions = [
        UserQuestionBookmark.user_id == user_id,
        UserQuestionBookmark.is_active == True,
        *_identity_filter(UserQuestionBookmark, review_source, canonical_question_id, runtime_question_id, diagnostic_question_id),
    ]
    if resolved_attempt_id is not None:
        conditions.extend(_attempt_filter(UserQuestionBookmark, resolved_attempt_id))
    bookmarked = db.scalar(
        select(UserQuestionBookmark.id).where(*conditions)
    )
    return BookmarkResponse(
        question_id=canonical_question_id,
        source=review_source,
        runtime_question_id=runtime_question_id,
        diagnostic_question_id=diagnostic_question_id,
        bookmarked=bookmarked is not None,
    )


@router.post("/api/review/bookmarks", response_model=BookmarkResponse)
@router.post("/api/review/bookmarks/toggle", response_model=BookmarkResponse)
def toggle_bookmark_route(
    payload: BookmarkToggleRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    review_source, runtime_question_id, diagnostic_question_id, canonical_question_id = _normalize_review_identity(
        question_id=payload.question_id,
        source=payload.source,
        runtime_question_id=payload.runtime_question_id,
        diagnostic_question_id=payload.diagnostic_question_id,
    )
    existing = db.scalar(
        select(UserQuestionBookmark).where(
            UserQuestionBookmark.user_id == user_id,
            UserQuestionBookmark.is_active == True,
            *_identity_filter(UserQuestionBookmark, review_source, canonical_question_id, runtime_question_id, diagnostic_question_id),
            *_attempt_filter(UserQuestionBookmark, payload.attempt_id),
        )
    )
    now = datetime.utcnow()
    if existing is not None:
        existing.is_active = False
        existing.updated_at_utc = now
        _set_review_queue_marker_active(
            db,
            user_id=user_id,
            source=review_source,
            question_id=canonical_question_id,
            runtime_question_id=runtime_question_id,
            diagnostic_question_id=diagnostic_question_id,
            attempt_id=existing.attempt_id,
            review_reason="bookmarked",
            is_active=False,
            at_utc=now,
        )
        db.commit()
        return BookmarkResponse(
            question_id=canonical_question_id,
            source=review_source,
            runtime_question_id=runtime_question_id,
            diagnostic_question_id=diagnostic_question_id,
            bookmarked=False,
        )

    inactive = db.scalar(
        select(UserQuestionBookmark).where(
            UserQuestionBookmark.user_id == user_id,
            UserQuestionBookmark.is_active == False,
            *_identity_filter(UserQuestionBookmark, review_source, canonical_question_id, runtime_question_id, diagnostic_question_id),
            *_attempt_filter(UserQuestionBookmark, payload.attempt_id),
        )
    )
    if inactive is not None:
        inactive.is_active = True
        inactive.attempt_id = payload.attempt_id or inactive.attempt_id
        inactive.source = review_source
        inactive.question_id = canonical_question_id
        inactive.runtime_question_id = runtime_question_id
        inactive.diagnostic_question_id = diagnostic_question_id
        inactive.updated_at_utc = now
        bookmark = inactive
    else:
        bookmark = UserQuestionBookmark(
            user_id=user_id,
            question_id=canonical_question_id,
            source=review_source,
            attempt_id=payload.attempt_id,
            runtime_question_id=runtime_question_id,
            diagnostic_question_id=diagnostic_question_id,
            created_at=now,
            created_at_utc=now,
            updated_at_utc=now,
            is_active=True,
        )
        db.add(bookmark)

    _upsert_review_queue_marker(
        db,
        user_id=user_id,
        source=review_source,
        question_id=canonical_question_id,
        runtime_question_id=runtime_question_id,
        diagnostic_question_id=diagnostic_question_id,
        attempt_id=payload.attempt_id,
        review_reason="bookmarked",
        at_utc=now,
    )
    db.commit()
    return BookmarkResponse(
        question_id=canonical_question_id,
        source=review_source,
        runtime_question_id=runtime_question_id,
        diagnostic_question_id=diagnostic_question_id,
        bookmarked=True,
    )


@router.get("/api/review/items", response_model=list[ReviewItemResponse])
def get_review_items_route(
    filter: str = Query("all"),
    source: str = Query("all"),
    attemptId: int | None = Query(default=None),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    normalized_filter = _normalize_filter(filter)
    normalized_source = _normalize_source_filter(source)
    effective_attempt_id = _effective_attempt_id(normalized_source, attemptId)
    if attemptId is not None and effective_attempt_id is None:
        logger.debug("Review items ignored attemptId=%s because source=%s", attemptId, normalized_source)
    queue_items = _load_review_queue_items(db, user_id, normalized_filter, normalized_source, effective_attempt_id, limit)
    if not queue_items:
        return []

    runtime_question_ids = sorted(
        {
            int(item.runtime_question_id or item.question_id)
            for item in queue_items
            if _canonical_source_type(item.source or item.source_attempt_type) in RUNTIME_REVIEW_SOURCES
            and (item.runtime_question_id or item.question_id)
        }
    )
    diagnostic_question_ids = sorted(
        {
            int(item.diagnostic_question_id or item.question_id)
            for item in queue_items
            if _canonical_source_type(item.source or item.source_attempt_type) == "diagnostic"
            and (item.diagnostic_question_id or item.question_id)
        }
    )

    question_rows = _load_practice_questions(db, runtime_question_ids)
    option_rows = _load_practice_options(db, runtime_question_ids)
    asset_rows = _load_practice_assets(db, runtime_question_ids)
    explanation_rows = _load_practice_explanations(db, runtime_question_ids)

    diagnostic_rows = _load_diagnostic_questions(db, diagnostic_question_ids)
    diagnostic_options = _load_diagnostic_options(db, diagnostic_question_ids)
    notes_by_identity = _load_notes_by_identity(db, user_id, queue_items)
    highlights_by_identity = _load_highlights_by_identity(db, user_id, queue_items)
    bookmarked_identities = _load_bookmarked_identities(db, user_id, queue_items)
    display_question_numbers = _display_question_numbers_by_identity(queue_items)

    result: list[ReviewItemResponse] = []
    for item in queue_items:
        source_type = _canonical_source_type(item.source or item.source_attempt_type)
        runtime_question_id = item.runtime_question_id or (item.question_id if source_type in RUNTIME_REVIEW_SOURCES else None)
        if source_type in RUNTIME_REVIEW_SOURCES and not runtime_question_id:
            logger.debug(
                "ReviewQueue item missing RuntimeQuestionId id=%s userId=%s source=%s questionId=%s",
                item.id,
                user_id,
                source_type,
                item.question_id,
            )
        diagnostic_question_id = item.diagnostic_question_id or (item.question_id if source_type == "diagnostic" else None)
        question_id = runtime_question_id or diagnostic_question_id or item.question_id
        identity = _queue_identity_key(item)
        display_question_number = display_question_numbers.get(identity)
        review_reasons = _review_reasons_for_identity(item, notes_by_identity, highlights_by_identity, bookmarked_identities)
        has_note = bool(notes_by_identity.get(identity))
        has_highlight = bool(highlights_by_identity.get(identity))
        is_bookmarked = identity in bookmarked_identities
        question = question_rows.get(int(runtime_question_id)) if runtime_question_id else None
        if question is None and diagnostic_question_id:
            question = diagnostic_rows.get(int(diagnostic_question_id))
        if not question:
            logger.debug(
                "ReviewQueue hydrate failed id=%s userId=%s source=%s runtimeQuestionId=%s diagnosticQuestionId=%s",
                item.id,
                user_id,
                source_type,
                runtime_question_id,
                diagnostic_question_id,
            )
            result.append(
                ReviewItemResponse(
                    id=item.id,
                    source=source_type,
                    question_id=question_id or item.question_id,
                    attempt_id=item.attempt_id or item.source_attempt_id,
                    runtime_question_id=runtime_question_id,
                    diagnostic_question_id=diagnostic_question_id,
                    question_number=display_question_number or item.question_number,
                    part=item.part,
                    part_number=item.part,
                    section=item.section,
                    question_text_en="",
                    question_text="",
                    options=[],
                    user_selected_option_label=item.selected_option_key,
                    selected_option_key=item.selected_option_key,
                    correct_option_key=item.correct_option_key,
                    is_correct=item.is_correct,
                    is_skipped=bool(item.is_skipped),
                    review_reason=item.review_reason,
                    review_reasons=review_reasons,
                    has_note=has_note,
                    has_highlight=has_highlight,
                    is_bookmarked=is_bookmarked,
                    bookmarked=is_bookmarked,
                    notes=notes_by_identity.get(identity, []),
                    highlights=highlights_by_identity.get(identity, []),
                    source_attempt_id=item.attempt_id or item.source_attempt_id,
                    source_type=source_type,
                    source_label=_source_label(source_type),
                    attempt_type=source_type,
                    source_queue_id=item.id,
                    status=item.status or "active",
                    missing_reason=f"Runtime question not found for runtimeQuestionId={runtime_question_id}",
                )
            )
            continue
        is_runtime = runtime_question_id is not None and source_type in RUNTIME_REVIEW_SOURCES
        hydrate_id = int(runtime_question_id or diagnostic_question_id or question_id)
        assets = asset_rows.get(hydrate_id, {}) if is_runtime else {}
        raw_explanation = explanation_rows.get(hydrate_id, {}) if is_runtime else {}
        passage_audio_path = _normalize_review_asset_path(
            assets.get("passage_audio_path") or question.get("PassageAudioPath"),
            "audio",
        )
        passage_image_path = _normalize_review_asset_path(
            assets.get("passage_image_path") or question.get("PassageImagePath"),
            "image",
        )
        question_audio_path = _normalize_review_asset_path(
            assets.get("audio_path") or passage_audio_path,
            "audio",
        )
        question_image_path = _normalize_review_asset_path(
            assets.get("image_path") or passage_image_path,
            "image",
        )
        passage_text = question.get("PassageText") or raw_explanation.get("PassageText")
        passage = None
        if question.get("PassageId") or question.get("PassageGroupCode") or passage_text or passage_audio_path or passage_image_path:
            passage = ReviewPassageResponse(
                id=question.get("PassageId"),
                group_code=question.get("PassageGroupCode"),
                title=question.get("PassageTitle") or question.get("PassageGroupCode"),
                text=passage_text,
                passage_text=passage_text,
                audio_path=passage_audio_path,
                image_path=passage_image_path,
                audio=_review_asset(passage_audio_path),
                image=_review_asset(passage_image_path),
            )
        result.append(
            ReviewItemResponse(
                id=item.id,
                source=source_type,
                question_id=hydrate_id,
                attempt_id=item.attempt_id or item.source_attempt_id,
                runtime_question_id=runtime_question_id if is_runtime else None,
                diagnostic_question_id=diagnostic_question_id,
                question_number=display_question_number or question.get("QuestionNumber") or item.question_number,
                part=question.get("PartNumber") or item.part,
                part_number=question.get("PartNumber") or item.part,
                section=question.get("Section") or item.section,
                part_label=question.get("PartLabel"),
                question_type=question.get("QuestionType"),
                skill_code=question.get("SkillCode") or item.skill_code or item.skill,
                subskill_code=question.get("SubskillCode"),
                topic=question.get("Topic"),
                difficulty=question.get("Difficulty"),
                test_number=question.get("TestNumber"),
                question_text_en=question.get("QuestionTextEn") or "",
                question_text=question.get("QuestionTextEn") or "",
                passage_text=passage_text,
                passage=passage,
                audio=_review_asset(question_audio_path),
                image=_review_asset(question_image_path),
                options=(option_rows if is_runtime else diagnostic_options).get(hydrate_id, []),
                correct_option_label=item.correct_option_key or question.get("CorrectOptionLabel"),
                correct_option_key=item.correct_option_key or question.get("CorrectOptionLabel"),
                correct_answer_text=question.get("CorrectAnswerText"),
                explanation_detail=question.get("ExplanationDetail") or raw_explanation.get("ExplanationText"),
                option_analysis=question.get("OptionAnalysis"),
                vocabulary_notes=question.get("VocabularyNotes"),
                raw_explanation=raw_explanation.get("ExplanationText"),
                raw_block=raw_explanation.get("RawBlock"),
                translation_vi=question.get("TranslationVi"),
                final_translation_vi=question.get("FinalTranslationVi"),
                user_selected_option_label=item.selected_option_key,
                selected_option_key=item.selected_option_key,
                is_correct=item.is_correct,
                is_skipped=bool(item.is_skipped),
                review_reason=item.review_reason,
                review_reasons=review_reasons,
                has_note=has_note,
                has_highlight=has_highlight,
                is_bookmarked=is_bookmarked,
                bookmarked=is_bookmarked,
                notes=notes_by_identity.get(identity, []),
                highlights=highlights_by_identity.get(identity, []),
                source_attempt_id=item.attempt_id or item.source_attempt_id,
                source_type=source_type,
                source_label=_source_label(source_type),
                attempt_type=source_type,
                source_queue_id=item.id,
                status=item.status or "active",
            )
        )
    sorted_result = sorted(result, key=_review_response_order_key)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Review items source=%s filter=%s attemptId=%s effectiveAttemptId=%s queue=%s result=%s first=%s last=%s",
            normalized_source,
            normalized_filter,
            attemptId,
            effective_attempt_id,
            len(queue_items),
            len(sorted_result),
            (
                sorted_result[0].source,
                sorted_result[0].attempt_id,
                sorted_result[0].question_number,
            )
            if sorted_result
            else None,
            (
                sorted_result[-1].source,
                sorted_result[-1].attempt_id,
                sorted_result[-1].question_number,
            )
            if sorted_result
            else None,
        )
    return sorted_result


@router.get("/api/review/summary")
def get_review_summary_route(
    filter: str = Query("all"),
    source: str = Query("all"),
    attemptId: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if not user_id:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    ensure_review_schema(db)
    normalized_filter = _normalize_filter(filter)
    normalized_source = _normalize_source_filter(source)
    effective_attempt_id = _effective_attempt_id(normalized_source, attemptId)
    if attemptId is not None and effective_attempt_id is None:
        logger.debug("Review summary ignored attemptId=%s because source=%s", attemptId, normalized_source)
    return _build_review_summary(db, user_id, normalized_filter, normalized_source, effective_attempt_id)


@router.get("/api/review/item/{review_item_id}")
def get_review_item_route(
    review_item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    item = get_review_item_detail(db, user_id, review_item_id)
    if item is None:
        return JSONResponse(status_code=404, content={"message": "Review item not found."})
    return item


@router.get("/api/review/debug/item/{review_item_id}")
def debug_review_item_route(
    review_item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    raw_item = db.get(ReviewQueueItem, review_item_id)
    hydrated_items = get_review_items_route(
        filter="all",
        source="all",
        attemptId=None,
        limit=200,
        db=db,
        user_id=user_id,
    )
    hydrated = next(
        (
            item
            for item in hydrated_items
            if item.source_queue_id == review_item_id
            or (raw_item is not None and item.question_id == raw_item.question_id)
        ),
        None,
    )
    return {
        "rawReviewItem": {
            "id": raw_item.id,
            "questionId": raw_item.question_id,
            "part": raw_item.part,
            "skill": raw_item.skill,
            "status": raw_item.status,
            "sourceAttemptType": raw_item.source_attempt_type,
            "sourceAttemptId": raw_item.source_attempt_id,
        }
        if raw_item is not None
        else None,
        "hydratedQuestion": hydrated.model_dump(mode="json") if hydrated is not None else None,
        "missingReason": None if hydrated is not None else f"Review item not found or not hydrateable for reviewItemId={review_item_id}",
    }


@router.get("/api/review/debug/items")
def debug_review_items_route(
    source: str = Query("all"),
    attemptId: int | None = Query(default=None),
    filter: str = Query("wrong"),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    normalized_source = _normalize_source_filter(source)
    normalized_filter = _normalize_filter(filter)
    attempt_debug: dict[str, Any] | None = None

    if attemptId:
        practice_attempt = db.scalar(
            select(PracticeAttempt).where(PracticeAttempt.id == attemptId, PracticeAttempt.user_id == user_id)
        )
        mock_attempt = db.scalar(
            select(MockTestAttempt).where(MockTestAttempt.id == attemptId, MockTestAttempt.user_id == user_id)
        )
        attempt_debug = {
            "practice": {
                "exists": practice_attempt is not None,
                "type": _source_type_for_practice_attempt(practice_attempt) if practice_attempt else None,
                "title": practice_attempt.title if practice_attempt else None,
                "mode": practice_attempt.mode if practice_attempt else None,
            },
            "mock": {
                "exists": mock_attempt is not None,
                "type": _source_type_for_mock_attempt(db, mock_attempt) if mock_attempt else None,
                "title": mock_attempt.title if mock_attempt else None,
                "totalQuestions": mock_attempt.total_questions if mock_attempt else None,
            },
        }

    items = get_review_items_route(
        filter=normalized_filter,
        source=normalized_source,
        attemptId=attemptId,
        limit=limit,
        db=db,
        user_id=user_id,
    )
    debug_question_ids = [item.runtime_question_id or item.question_id for item in items[:5]]
    set_meta_by_question = _load_review_debug_set_meta(db, debug_question_ids)
    return {
        "sourceQuery": source,
        "normalizedSource": normalized_source,
        "attemptId": attemptId,
        "attempt": attempt_debug,
        "totalItems": len(items),
        "items": [
            {
                "id": item.id,
                "questionId": item.question_id,
                "runtimeQuestionId": item.runtime_question_id,
                "questionNumber": item.question_number,
                "part": item.part,
                "source": item.source_type,
                "sourceLabel": item.source_label,
                "attemptId": item.source_attempt_id or item.attempt_id,
                "setId": set_meta_by_question.get(item.runtime_question_id or item.question_id, {}).get("SetId"),
                "setType": set_meta_by_question.get(item.runtime_question_id or item.question_id, {}).get("SetType"),
                "status": item.status,
            }
            for item in items[:5]
        ],
    }


@router.get("/api/review/debug/counts")
def debug_review_counts_route(
    source: str = Query("all"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    normalized_source = _normalize_source_filter(source)
    sources = ["practice", "fulltest", "minitest", "weeklycheck", "diagnostic"]
    requested_sources = sources if normalized_source == "all" else [normalized_source]
    by_source = {
        item_source: _build_review_summary(db, user_id, "all", item_source, None)
        for item_source in requested_sources
        if item_source in sources
    }
    all_counts = _build_review_summary(db, user_id, "all", "all", None)
    duplicate_rows = db.execute(
        text(
            """
            SELECT TOP 100
                UserId,
                [Source],
                RuntimeQuestionId,
                DiagnosticQuestionId,
                QuestionId,
                ReviewReason,
                ISNULL(AttemptId, 0) AS AttemptIdKey,
                COUNT(*) AS Cnt
            FROM dbo.ReviewQueue
            WHERE UserId = :user_id
              AND IsActive = 1
            GROUP BY UserId, [Source], RuntimeQuestionId, DiagnosticQuestionId, QuestionId, ReviewReason, ISNULL(AttemptId, 0)
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, [Source], ReviewReason
            """
        ),
        {"user_id": user_id},
    ).mappings().all()
    return {
        "source": normalized_source,
        "all": all_counts,
        "totalDistinct": all_counts.get("totalReviewQuestions", 0),
        "bySource": by_source,
        "duplicateReviewQueue": [dict(row) for row in duplicate_rows],
        "duplicateKeys": [dict(row) for row in duplicate_rows],
    }
    sources = ["practice", "fulltest", "minitest", "weeklycheck", "diagnostic"]
    by_source: dict[str, dict[str, Any]] = {
        source: {
            "total": 0,
            "wrong": 0,
            "skipped": 0,
            "noted": 0,
            "highlighted": 0,
            "bookmarked": 0,
            "distinctRuntimeQuestionIds": 0,
            "recentAttempts": [],
        }
        for source in sources
    }
    total_review_queue = int(
        db.execute(
            text("SELECT COUNT(*) FROM dbo.ReviewQueue WHERE UserId = :user_id"),
            {"user_id": user_id},
        ).scalar()
        or 0
    )
    active_review_queue = int(
        db.execute(
            text("SELECT COUNT(*) FROM dbo.ReviewQueue WHERE UserId = :user_id AND IsActive = 1"),
            {"user_id": user_id},
        ).scalar()
        or 0
    )
    rows = db.execute(
        text(
            """
            SELECT
                [Source],
                COUNT(*) AS Total,
                SUM(CASE WHEN ReviewReason = N'wrong' THEN 1 ELSE 0 END) AS WrongCount,
                SUM(CASE WHEN ReviewReason = N'skipped' THEN 1 ELSE 0 END) AS SkippedCount,
                SUM(CASE WHEN ReviewReason = N'noted' THEN 1 ELSE 0 END) AS NotedCount,
                SUM(CASE WHEN ReviewReason = N'highlighted' THEN 1 ELSE 0 END) AS HighlightedCount,
                SUM(CASE WHEN ReviewReason = N'bookmarked' THEN 1 ELSE 0 END) AS BookmarkedCount,
                COUNT(DISTINCT RuntimeQuestionId) AS DistinctRuntimeQuestionIds
            FROM dbo.ReviewQueue
            WHERE UserId = :user_id
              AND IsActive = 1
            GROUP BY [Source]
            """
        ),
        {"user_id": user_id},
    ).mappings().all()
    for row in rows:
        source = _canonical_source_type(row["Source"])
        if source not in by_source:
            by_source[source] = {}
        by_source[source].update(
            {
                "total": int(row["Total"] or 0),
                "wrong": int(row["WrongCount"] or 0),
                "skipped": int(row["SkippedCount"] or 0),
                "noted": int(row["NotedCount"] or 0),
                "highlighted": int(row["HighlightedCount"] or 0),
                "bookmarked": int(row["BookmarkedCount"] or 0),
                "distinctRuntimeQuestionIds": int(row["DistinctRuntimeQuestionIds"] or 0),
            }
        )

    source_reason_rows = db.execute(
        text(
            """
            SELECT [Source], ReviewReason, COUNT(*) AS Total
            FROM dbo.ReviewQueue
            WHERE UserId = :user_id
              AND IsActive = 1
            GROUP BY [Source], ReviewReason
            ORDER BY [Source], ReviewReason
            """
        ),
        {"user_id": user_id},
    ).mappings().all()
    by_source_reason = [
        {
            "source": _canonical_source_type(row["Source"]),
            "reviewReason": row["ReviewReason"],
            "total": int(row["Total"] or 0),
        }
        for row in source_reason_rows
    ]

    attempt_rows = db.execute(
        text(
            """
            SELECT TOP 100
                [Source],
                AttemptId,
                COUNT(*) AS Total,
                MAX(UpdatedAtUtc) AS LastUpdatedAtUtc
            FROM dbo.ReviewQueue
            WHERE UserId = :user_id
              AND IsActive = 1
              AND AttemptId IS NOT NULL
            GROUP BY [Source], AttemptId
            ORDER BY MAX(UpdatedAtUtc) DESC
            """
        ),
        {"user_id": user_id},
    ).mappings().all()
    by_attempt = [
        {
            "source": _canonical_source_type(row["Source"]),
            "attemptId": int(row["AttemptId"]),
            "total": int(row["Total"] or 0),
            "lastUpdatedAtUtc": row["LastUpdatedAtUtc"],
        }
        for row in attempt_rows
    ]
    for row in attempt_rows:
        source = _canonical_source_type(row["Source"])
        if source not in by_source or len(by_source[source].get("recentAttempts", [])) >= 5:
            continue
        by_source[source]["recentAttempts"].append(
            {
                "attemptId": int(row["AttemptId"]),
                "total": int(row["Total"] or 0),
                "lastUpdatedAtUtc": row["LastUpdatedAtUtc"],
            }
        )

    latest_rows = [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT TOP 10
                    Id,
                    UserId,
                    [Source],
                    AttemptId,
                    RuntimeQuestionId,
                    DiagnosticQuestionId,
                    QuestionId,
                    QuestionNumber,
                    Part,
                    Section,
                    ReviewReason,
                    SelectedOptionKey,
                    CorrectOptionKey,
                    IsCorrect,
                    IsSkipped,
                    IsActive,
                    CreatedAtUtc,
                    UpdatedAtUtc
                FROM dbo.ReviewQueue
                WHERE UserId = :user_id
                ORDER BY COALESCE(UpdatedAtUtc, LastAnsweredAtUtc, CreatedAtUtc) DESC, Id DESC
                """
            ),
            {"user_id": user_id},
        ).mappings().all()
    ]

    required_columns = {
        "ReviewQueue": [
            "Id",
            "UserId",
            "Source",
            "AttemptId",
            "AttemptIdKey",
            "RuntimeQuestionId",
            "QuestionId",
            "QuestionNumber",
            "Part",
            "Section",
            "Skill",
            "SkillCode",
            "ReviewReason",
            "SelectedOptionKey",
            "CorrectOptionKey",
            "IsCorrect",
            "IsSkipped",
            "IsActive",
            "LastAnsweredAtUtc",
            "CreatedAtUtc",
            "UpdatedAtUtc",
        ],
        "UserQuestionNotes": ["UserId", "Source", "AttemptId", "RuntimeQuestionId", "QuestionId", "NoteText", "CreatedAtUtc", "UpdatedAtUtc", "IsActive"],
        "UserQuestionHighlights": ["UserId", "Source", "AttemptId", "RuntimeQuestionId", "QuestionId", "HighlightText", "CreatedAtUtc", "UpdatedAtUtc", "IsActive"],
        "UserQuestionBookmarks": ["UserId", "Source", "AttemptId", "RuntimeQuestionId", "QuestionId", "CreatedAtUtc", "UpdatedAtUtc", "IsActive"],
    }
    schema_rows = db.execute(
        text(
            """
            SELECT t.name AS TableName, c.name AS ColumnName
            FROM sys.tables t
            JOIN sys.schemas s ON s.schema_id = t.schema_id
            JOIN sys.columns c ON c.object_id = t.object_id
            WHERE s.name = N'dbo'
              AND t.name IN (N'ReviewQueue', N'UserQuestionNotes', N'UserQuestionHighlights', N'UserQuestionBookmarks')
            """
        )
    ).mappings().all()
    actual_columns: dict[str, set[str]] = {}
    for row in schema_rows:
        actual_columns.setdefault(str(row["TableName"]), set()).add(str(row["ColumnName"]))
    schema_check = {
        table: {
            "exists": table in actual_columns,
            "missingColumns": [column for column in columns if column not in actual_columns.get(table, set())],
            "requiredColumns": columns,
        }
        for table, columns in required_columns.items()
    }

    return {
        **by_source,
        "totalReviewQueue": total_review_queue,
        "activeReviewQueue": active_review_queue,
        "bySource": by_source,
        "bySourceReason": by_source_reason,
        "byAttempt": by_attempt,
        "latestRows": latest_rows,
        "schemaCheck": schema_check,
    }


@router.get("/api/review/debug/by-attempt")
def debug_review_by_attempt_route(
    source: str = Query(...),
    attemptId: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    normalized_source = _normalize_source_filter(source)
    if normalized_source == "all":
        raise HTTPException(status_code=400, detail="source must be practice, fulltest, minitest, or weeklycheck.")
    rows = db.execute(
        text(
            """
            SELECT TOP 500
                Id,
                [Source],
                AttemptId,
                RuntimeQuestionId,
                DiagnosticQuestionId,
                QuestionId,
                QuestionNumber,
                Part,
                Section,
                Skill,
                ReviewReason,
                SelectedOptionKey,
                CorrectOptionKey,
                IsCorrect,
                IsSkipped,
                IsActive,
                CreatedAtUtc,
                UpdatedAtUtc
            FROM dbo.ReviewQueue
            WHERE UserId = :user_id
              AND IsActive = 1
              AND [Source] = :source
              AND AttemptId = :attempt_id
            ORDER BY ReviewReason, QuestionNumber, RuntimeQuestionId, Id
            """
        ),
        {"user_id": user_id, "source": normalized_source, "attempt_id": attemptId},
    ).mappings().all()
    reason_counts: dict[str, int] = {}
    for row in rows:
        reason = str(row["ReviewReason"] or "unknown")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "source": normalized_source,
        "attemptId": attemptId,
        "total": len(rows),
        "reasonCounts": reason_counts,
        "items": [dict(row) for row in rows],
    }


@router.post("/api/review/item/{review_item_id}/mark-reviewed")
def mark_review_item_route(
    review_item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    ensure_review_schema(db)
    item = mark_review_item_reviewed(db, user_id, review_item_id)
    if item is None:
        return JSONResponse(status_code=404, content={"message": "Review item not found."})
    return item


def _require_user(user_id: int | None) -> None:
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _normalize_filter(value: str) -> str:
    normalized = (value or "all").strip().lower()
    aliases = {
        "note": "noted",
        "notes": "noted",
        "highlight": "highlighted",
        "highlights": "highlighted",
    }
    normalized = aliases.get(normalized, normalized)
    allowed = {"all", "wrong", "correct", "skipped", "bookmarked", "noted", "highlighted", "notebook"}
    return normalized if normalized in allowed else "all"


def _normalize_source_filter(value: str | None) -> str:
    normalized = (value or "all").strip().lower().replace("-", "_")
    aliases = {
        "all": "all",
        "practice": "practice",
        "bai_tap": "practice",
        "full": "fulltest",
        "full_test": "fulltest",
        "fulltest": "fulltest",
        "mock": "fulltest",
        "mock_test": "fulltest",
        "mock-test": "fulltest",
        "mini": "minitest",
        "mini_test": "minitest",
        "minitest": "minitest",
        "weekly": "weeklycheck",
        "weekly_check": "weeklycheck",
        "weeklycheck": "weeklycheck",
        "diagnostic": "diagnostic",
        "placement": "diagnostic",
        "placement_test": "diagnostic",
    }
    return aliases.get(normalized, "all")


def _normalize_persisted_source(value: str | None, fallback: str = "practice") -> str:
    normalized = _normalize_source_filter(value)
    return fallback if normalized == "all" else normalized


def _source_values_for_filter(source_filter: str) -> list[str]:
    if source_filter == "all":
        return []
    aliases = {
        "practice": ["practice"],
        "fulltest": ["fulltest", "full_test", "mock", "mock_test", "mock-test"],
        "minitest": ["minitest", "mini", "mini_test", "mini-test"],
        "weeklycheck": ["weeklycheck", "weekly", "weekly_check", "weekly-check"],
        "diagnostic": ["diagnostic", "placement", "placement_test", "placement-test"],
    }
    return aliases.get(source_filter, [source_filter])


def _effective_attempt_id(source_filter: str, attempt_id: int | None) -> int | None:
    return attempt_id if source_filter != "all" else None


def _normalize_review_identity(
    question_id: int,
    source: str | None,
    runtime_question_id: int | None = None,
    diagnostic_question_id: int | None = None,
) -> tuple[str, int | None, int | None, int]:
    review_source = _normalize_persisted_source(source)
    runtime_id = runtime_question_id or (question_id if review_source in RUNTIME_REVIEW_SOURCES else None)
    diagnostic_id = diagnostic_question_id or (question_id if review_source == "diagnostic" else None)
    canonical_question_id = runtime_id or diagnostic_id or question_id
    return review_source, runtime_id, diagnostic_id, int(canonical_question_id)


def _identity_filter(
    model,
    source: str,
    question_id: int,
    runtime_question_id: int | None,
    diagnostic_question_id: int | None,
) -> list[Any]:
    conditions: list[Any] = [model.source == source]
    if runtime_question_id is not None:
        conditions.append(
            or_(
                model.runtime_question_id == runtime_question_id,
                and_(model.runtime_question_id.is_(None), model.question_id == question_id),
            )
        )
    elif diagnostic_question_id is not None:
        conditions.append(
            or_(
                model.diagnostic_question_id == diagnostic_question_id,
                and_(model.diagnostic_question_id.is_(None), model.question_id == question_id),
            )
        )
    else:
        conditions.append(model.question_id == question_id)
    return conditions


def _attempt_filter(model, attempt_id: int | None) -> list[Any]:
    if not hasattr(model, "attempt_id"):
        return []
    return [model.attempt_id.is_(None) if attempt_id is None else model.attempt_id == attempt_id]


def _queue_identity_key(item: ReviewQueueItem) -> tuple[str, int]:
    source = _canonical_source_type(item.source or item.source_attempt_type)
    if source in RUNTIME_REVIEW_SOURCES and item.runtime_question_id:
        return source, int(item.runtime_question_id)
    if source == "diagnostic" and (item.diagnostic_question_id or item.question_id):
        return source, int(item.diagnostic_question_id or item.question_id)
    return source, int(item.question_id or 0)


def _notebook_identity_key(item: UserQuestionNote | UserQuestionHighlight | UserQuestionBookmark) -> tuple[str, int]:
    source = _normalize_persisted_source(getattr(item, "source", None))
    runtime_question_id = getattr(item, "runtime_question_id", None)
    diagnostic_question_id = getattr(item, "diagnostic_question_id", None)
    if source in RUNTIME_REVIEW_SOURCES and runtime_question_id:
        return source, int(runtime_question_id)
    if source == "diagnostic" and diagnostic_question_id:
        return source, int(diagnostic_question_id)
    return source, int(item.question_id or 0)


def _reason_filter(filter_name: str) -> set[str] | None:
    if filter_name == "wrong":
        return {"wrong", "skipped"}
    if filter_name == "skipped":
        return {"skipped"}
    if filter_name == "bookmarked":
        return {"bookmarked"}
    if filter_name == "noted":
        return {"noted"}
    if filter_name == "highlighted":
        return {"highlighted"}
    if filter_name == "notebook":
        return {"bookmarked", "noted", "highlighted"}
    return None


def _queue_item_is_wrong(item: ReviewQueueItem) -> bool:
    reason = (item.review_reason or "").strip().lower()
    if reason in {"wrong", "skipped"} or item.is_skipped:
        return True
    if reason in {"noted", "highlighted", "bookmarked"}:
        return False
    return item.is_correct is False


def _identity_matches_source(identity: tuple[str, int], source_filter: str) -> bool:
    return source_filter == "all" or identity[0] == source_filter


def _notebook_row_matches_filters(
    item: UserQuestionNote | UserQuestionHighlight | UserQuestionBookmark,
    source_filter: str,
    attempt_id: int | None,
) -> bool:
    effective_attempt_id = _effective_attempt_id(source_filter, attempt_id)
    if effective_attempt_id is not None and getattr(item, "attempt_id", None) != effective_attempt_id:
        return False
    return _identity_matches_source(_notebook_identity_key(item), source_filter)


def _make_notebook_queue_item(
    item: UserQuestionNote | UserQuestionHighlight | UserQuestionBookmark,
    review_reason: str,
) -> ReviewQueueItem:
    source = _normalize_persisted_source(getattr(item, "source", None))
    runtime_question_id = getattr(item, "runtime_question_id", None)
    diagnostic_question_id = getattr(item, "diagnostic_question_id", None)
    question_id = int(runtime_question_id or diagnostic_question_id or getattr(item, "question_id", None) or 0)
    return ReviewQueueItem(
        id=getattr(item, "id", None),
        user_id=getattr(item, "user_id", None),
        question_id=question_id,
        source=source,
        attempt_id=getattr(item, "attempt_id", None),
        runtime_question_id=runtime_question_id,
        diagnostic_question_id=diagnostic_question_id,
        review_reason=review_reason,
        is_correct=False,
        is_skipped=False,
        is_active=True,
        status="notebook" if review_reason in {"noted", "highlighted"} else "pending",
        source_attempt_type=source,
        source_attempt_id=getattr(item, "attempt_id", None),
        added_at_utc=getattr(item, "updated_at", None) or getattr(item, "created_at", None),
        updated_at_utc=getattr(item, "updated_at", None) or getattr(item, "created_at", None),
    )


def _merge_review_item(target: ReviewQueueItem, source: ReviewQueueItem) -> None:
    target.question_id = target.question_id or source.question_id
    target.runtime_question_id = target.runtime_question_id or source.runtime_question_id
    target.diagnostic_question_id = target.diagnostic_question_id or source.diagnostic_question_id
    target.question_number = target.question_number or source.question_number
    target.part = target.part or source.part
    target.section = target.section or source.section
    target.skill = target.skill or source.skill
    target.skill_code = target.skill_code or source.skill_code
    target.selected_option_key = target.selected_option_key or source.selected_option_key
    target.correct_option_key = target.correct_option_key or source.correct_option_key
    target.last_answered_at_utc = target.last_answered_at_utc or source.last_answered_at_utc
    target.updated_at_utc = target.updated_at_utc or source.updated_at_utc
    target.added_at_utc = target.added_at_utc or source.added_at_utc
    target.source_attempt_type = target.source_attempt_type or source.source_attempt_type
    target.source_attempt_id = target.source_attempt_id or source.source_attempt_id
    if source.is_skipped:
        target.is_skipped = True
    if source.is_correct:
        target.is_correct = True
    priority = {"wrong": 50, "skipped": 45, "bookmarked": 30, "noted": 25, "highlighted": 20}
    if priority.get(source.review_reason or "", 0) > priority.get(target.review_reason or "", 0):
        target.review_reason = source.review_reason
        target.id = target.id or source.id


def _review_reasons_for_identity(
    item: ReviewQueueItem,
    notes_by_identity: dict[tuple[str, int], list[UserQuestionNote]],
    highlights_by_identity: dict[tuple[str, int], list[UserQuestionHighlight]],
    bookmarked_identities: set[tuple[str, int]],
) -> list[str]:
    identity = _queue_identity_key(item)
    reasons = {
        row.review_reason
        for row in getattr(item, "_merged_queue_rows", [item])
        if getattr(row, "review_reason", None)
    }
    if any(_queue_item_is_wrong(row) and (row.review_reason or "").strip().lower() != "skipped" for row in getattr(item, "_merged_queue_rows", [item])):
        reasons.add("wrong")
    if item.is_skipped:
        reasons.add("skipped")
    if notes_by_identity.get(identity):
        reasons.add("noted")
    if highlights_by_identity.get(identity):
        reasons.add("highlighted")
    if identity in bookmarked_identities:
        reasons.add("bookmarked")
    order = ["wrong", "skipped", "noted", "highlighted", "bookmarked"]
    return [reason for reason in order if reason in reasons]


def _display_question_numbers_by_identity(queue_items: list[ReviewQueueItem]) -> dict[tuple[str, int], int]:
    result: dict[tuple[str, int], int] = {}
    groups: dict[tuple[str, int], list[ReviewQueueItem]] = {}
    for item in queue_items:
        source_type = _canonical_source_type(item.source or item.source_attempt_type)
        if source_type != "minitest":
            continue
        groups.setdefault((source_type, int(item.attempt_id or item.source_attempt_id or 0)), []).append(item)

    for group_items in groups.values():
        ordered = sorted(
            group_items,
            key=lambda item: (
                int(item.question_number or 0),
                int(item.runtime_question_id or item.question_id or 0),
                int(item.id or 0),
            ),
        )
        for index, item in enumerate(ordered, start=1):
            result.setdefault(_queue_identity_key(item), index)
    return result


def _review_queue_order_key(item: ReviewQueueItem) -> tuple[int, int, int, int, int]:
    source_type = _canonical_source_type(item.source or item.source_attempt_type)
    question_order = item.question_number
    if question_order is None:
        if source_type in RUNTIME_REVIEW_SOURCES:
            question_order = item.runtime_question_id or item.question_id
        elif source_type == "diagnostic":
            question_order = item.question_number or item.diagnostic_question_id or item.question_id
        else:
            question_order = item.question_number or item.question_id
    return (
        REVIEW_SOURCE_ORDER.get(source_type, 99),
        int(item.attempt_id or item.source_attempt_id or 0),
        int(question_order or 0),
        int(item.runtime_question_id or item.diagnostic_question_id or item.question_id or 0),
        int(item.id or 0),
    )


def _review_response_order_key(item: ReviewItemResponse) -> tuple[int, int, int, int, int]:
    source_type = _canonical_source_type(item.source or item.source_type)
    question_order = item.question_number
    if question_order is None:
        question_order = item.runtime_question_id or item.diagnostic_question_id or item.question_id
    return (
        REVIEW_SOURCE_ORDER.get(source_type, 99),
        int(item.attempt_id or item.source_attempt_id or 0),
        int(question_order or 0),
        int(item.runtime_question_id or item.diagnostic_question_id or item.question_id or 0),
        int(item.id or 0),
    )


def _load_review_queue_items(
    db: Session,
    user_id: int,
    filter_name: str,
    source_filter: str,
    attempt_id: int | None,
    limit: int,
) -> list[ReviewQueueItem]:
    queue_query = select(ReviewQueueItem).where(
        ReviewQueueItem.user_id == user_id,
        ReviewQueueItem.is_active == True,
    )
    if source_filter != "all":
        queue_query = queue_query.where(ReviewQueueItem.source.in_(_source_values_for_filter(source_filter)))
    effective_attempt_id = _effective_attempt_id(source_filter, attempt_id)
    if effective_attempt_id is not None:
        queue_query = queue_query.where(ReviewQueueItem.attempt_id == effective_attempt_id)
    reasons = _reason_filter(filter_name)
    if filter_name == "wrong":
        queue_query = queue_query.where(
            or_(
                ReviewQueueItem.review_reason.in_(["wrong", "skipped"]),
                ReviewQueueItem.is_skipped == True,
                and_(
                    ReviewQueueItem.is_correct == False,
                    ~ReviewQueueItem.review_reason.in_(["noted", "highlighted", "bookmarked"]),
                ),
            )
        )
    elif reasons:
        queue_query = queue_query.where(ReviewQueueItem.review_reason.in_(sorted(reasons)))
    elif filter_name == "correct":
        queue_query = queue_query.where(ReviewQueueItem.is_correct == True)
    queue_rows = list(
        db.scalars(
            queue_query.order_by(
                func.coalesce(
                    ReviewQueueItem.question_number,
                    ReviewQueueItem.runtime_question_id,
                    ReviewQueueItem.diagnostic_question_id,
                    ReviewQueueItem.question_id,
                    ReviewQueueItem.id,
                ).asc(),
                ReviewQueueItem.id.asc(),
            ).limit(max(limit * 20, 5000))
        ).all()
    )

    candidates: list[ReviewQueueItem] = queue_rows
    if filter_name in {"all", "noted", "highlighted", "bookmarked", "notebook"}:
        if filter_name in {"all", "noted", "notebook"}:
            note_query = select(UserQuestionNote).where(
                UserQuestionNote.user_id == user_id,
                UserQuestionNote.is_active == True,
                func.len(func.ltrim(func.rtrim(UserQuestionNote.note_text))) > 0,
            )
            for note in db.scalars(note_query.order_by(UserQuestionNote.updated_at.desc()).limit(max(limit * 20, 5000))).all():
                if _notebook_row_matches_filters(note, source_filter, effective_attempt_id):
                    candidates.append(_make_notebook_queue_item(note, "noted"))
        if filter_name in {"all", "highlighted", "notebook"}:
            highlight_query = select(UserQuestionHighlight).where(
                UserQuestionHighlight.user_id == user_id,
                UserQuestionHighlight.is_active == True,
            )
            for highlight in db.scalars(highlight_query.order_by(UserQuestionHighlight.updated_at.desc()).limit(max(limit * 20, 5000))).all():
                if _notebook_row_matches_filters(highlight, source_filter, effective_attempt_id):
                    candidates.append(_make_notebook_queue_item(highlight, "highlighted"))
        if filter_name in {"all", "bookmarked", "notebook"}:
            bookmark_query = select(UserQuestionBookmark).where(
                UserQuestionBookmark.user_id == user_id,
                UserQuestionBookmark.is_active == True,
            )
            for bookmark in db.scalars(bookmark_query.order_by(UserQuestionBookmark.created_at.desc()).limit(max(limit * 20, 5000))).all():
                if _notebook_row_matches_filters(bookmark, source_filter, effective_attempt_id):
                    candidates.append(_make_notebook_queue_item(bookmark, "bookmarked"))

    unique: dict[tuple[str, int], ReviewQueueItem] = {}
    for item in candidates:
        identity = _queue_identity_key(item)
        if identity[1] <= 0 or not _identity_matches_source(identity, source_filter):
            continue
        if identity not in unique:
            setattr(item, "_merged_queue_rows", [item])
            unique[identity] = item
        else:
            getattr(unique[identity], "_merged_queue_rows").append(item)
            _merge_review_item(unique[identity], item)
    return sorted(unique.values(), key=_review_queue_order_key)[:limit]


def _build_review_summary(
    db: Session,
    user_id: int,
    filter_name: str,
    source_filter: str,
    attempt_id: int | None,
) -> dict[str, int]:
    del filter_name
    queue_query = select(ReviewQueueItem).where(
        ReviewQueueItem.user_id == user_id,
        ReviewQueueItem.is_active == True,
    )
    if source_filter != "all":
        queue_query = queue_query.where(ReviewQueueItem.source.in_(_source_values_for_filter(source_filter)))
    effective_attempt_id = _effective_attempt_id(source_filter, attempt_id)
    if effective_attempt_id is not None:
        queue_query = queue_query.where(ReviewQueueItem.attempt_id == effective_attempt_id)

    wrong_identities: set[tuple[str, int]] = set()
    skipped_identities: set[tuple[str, int]] = set()
    total_identities: set[tuple[str, int]] = set()
    for item in db.scalars(queue_query).all():
        identity = _queue_identity_key(item)
        if identity[1] <= 0:
            continue
        total_identities.add(identity)
        reason = (item.review_reason or "").strip().lower()
        if _queue_item_is_wrong(item) and reason != "skipped" and not item.is_skipped:
            wrong_identities.add(identity)
        if reason == "skipped" or item.is_skipped:
            skipped_identities.add(identity)

    noted_identities: set[tuple[str, int]] = set()
    note_query = select(UserQuestionNote).where(
        UserQuestionNote.user_id == user_id,
        UserQuestionNote.is_active == True,
        func.len(func.ltrim(func.rtrim(UserQuestionNote.note_text))) > 0,
    )
    for note in db.scalars(note_query).all():
        if _notebook_row_matches_filters(note, source_filter, effective_attempt_id):
            identity = _notebook_identity_key(note)
            if identity[1] > 0:
                noted_identities.add(identity)
                total_identities.add(identity)

    highlighted_identities: set[tuple[str, int]] = set()
    highlight_query = select(UserQuestionHighlight).where(
        UserQuestionHighlight.user_id == user_id,
        UserQuestionHighlight.is_active == True,
    )
    for highlight in db.scalars(highlight_query).all():
        if _notebook_row_matches_filters(highlight, source_filter, effective_attempt_id):
            identity = _notebook_identity_key(highlight)
            if identity[1] > 0:
                highlighted_identities.add(identity)
                total_identities.add(identity)

    bookmarked_identities: set[tuple[str, int]] = set()
    bookmark_query = select(UserQuestionBookmark).where(
        UserQuestionBookmark.user_id == user_id,
        UserQuestionBookmark.is_active == True,
    )
    for bookmark in db.scalars(bookmark_query).all():
        if _notebook_row_matches_filters(bookmark, source_filter, effective_attempt_id):
            identity = _notebook_identity_key(bookmark)
            if identity[1] > 0:
                bookmarked_identities.add(identity)
                total_identities.add(identity)

    wrong_card_count = len(wrong_identities | skipped_identities)
    stability_percent = 100 if not total_identities else max(0, 100 - wrong_card_count * 5)
    return {
        "wrongCount": len(wrong_identities),
        "skippedCount": len(skipped_identities),
        "wrongCardCount": wrong_card_count,
        "wrongReviewCount": wrong_card_count,
        "noteCount": len(noted_identities),
        "notedCount": len(noted_identities),
        "highlightCount": len(highlighted_identities),
        "highlightedCount": len(highlighted_identities),
        "bookmarkCount": len(bookmarked_identities),
        "bookmarkedCount": len(bookmarked_identities),
        "totalReviewQuestions": len(total_identities),
        "stabilityPercent": stability_percent,
    }


def _load_runtime_question_summary(db: Session, runtime_question_id: int | None) -> dict[str, Any]:
    if not runtime_question_id:
        return {}
    row = db.execute(
        text(
            """
            SELECT TOP 1
                q.QuestionNumber,
                q.Part,
                q.Section,
                q.SkillCode,
                q.CorrectOptionKey
            FROM dbo.ToeicPracticeQuestions q
            WHERE q.Id = :question_id
            """
        ),
        {"question_id": runtime_question_id},
    ).mappings().first()
    return dict(row) if row else {}


def _upsert_review_queue_marker(
    db: Session,
    user_id: int,
    source: str,
    question_id: int,
    runtime_question_id: int | None,
    diagnostic_question_id: int | None,
    attempt_id: int | None,
    review_reason: str,
    at_utc: datetime,
) -> ReviewQueueItem:
    review_source = _normalize_persisted_source(source)
    query = select(ReviewQueueItem).where(
        ReviewQueueItem.user_id == user_id,
        ReviewQueueItem.source == review_source,
        ReviewQueueItem.review_reason == review_reason,
    )
    if attempt_id is None:
        query = query.where(ReviewQueueItem.attempt_id.is_(None))
    else:
        query = query.where(ReviewQueueItem.attempt_id == attempt_id)
    if runtime_question_id is not None:
        query = query.where(ReviewQueueItem.runtime_question_id == runtime_question_id)
    elif diagnostic_question_id is not None:
        query = query.where(ReviewQueueItem.diagnostic_question_id == diagnostic_question_id)
    else:
        query = query.where(ReviewQueueItem.question_id == question_id)
    item = db.scalar(query)
    summary = _load_runtime_question_summary(db, runtime_question_id) if review_source in RUNTIME_REVIEW_SOURCES else {}
    if item is None:
        item = ReviewQueueItem(
            user_id=user_id,
            question_id=question_id,
            source=review_source,
            attempt_id=attempt_id,
            runtime_question_id=runtime_question_id,
            diagnostic_question_id=diagnostic_question_id,
            question_number=summary.get("QuestionNumber"),
            part=summary.get("Part"),
            section=summary.get("Section"),
            skill=summary.get("SkillCode"),
            skill_code=summary.get("SkillCode"),
            is_correct=False,
            is_skipped=False,
            correct_option_key=summary.get("CorrectOptionKey"),
            review_reason=review_reason,
            last_answered_at_utc=at_utc,
            created_at_utc=at_utc,
            updated_at_utc=at_utc,
            is_active=True,
            status="pending",
            source_attempt_type=review_source,
            source_attempt_id=attempt_id,
            added_at_utc=at_utc,
        )
        db.add(item)
    else:
        item.question_id = question_id
        item.source = review_source
        item.attempt_id = attempt_id if attempt_id is not None else item.attempt_id
        item.runtime_question_id = runtime_question_id
        item.diagnostic_question_id = diagnostic_question_id
        item.question_number = item.question_number or summary.get("QuestionNumber")
        item.part = item.part or summary.get("Part")
        item.section = item.section or summary.get("Section")
        item.skill = item.skill or summary.get("SkillCode")
        item.skill_code = item.skill_code or summary.get("SkillCode")
        item.correct_option_key = item.correct_option_key or summary.get("CorrectOptionKey")
        item.last_answered_at_utc = at_utc
        item.updated_at_utc = at_utc
        item.is_active = True
        item.source_attempt_type = review_source
        item.source_attempt_id = attempt_id if attempt_id is not None else item.source_attempt_id
    return item


def _set_review_queue_marker_active(
    db: Session,
    user_id: int,
    source: str,
    question_id: int,
    runtime_question_id: int | None,
    diagnostic_question_id: int | None,
    attempt_id: int | None,
    review_reason: str,
    is_active: bool,
    at_utc: datetime,
) -> None:
    review_source = _normalize_persisted_source(source)
    query = select(ReviewQueueItem).where(
        ReviewQueueItem.user_id == user_id,
        ReviewQueueItem.source == review_source,
        ReviewQueueItem.review_reason == review_reason,
    )
    if attempt_id is None:
        query = query.where(ReviewQueueItem.attempt_id.is_(None))
    else:
        query = query.where(ReviewQueueItem.attempt_id == attempt_id)
    if runtime_question_id is not None:
        query = query.where(ReviewQueueItem.runtime_question_id == runtime_question_id)
    elif diagnostic_question_id is not None:
        query = query.where(ReviewQueueItem.diagnostic_question_id == diagnostic_question_id)
    else:
        query = query.where(ReviewQueueItem.question_id == question_id)
    item = db.scalar(query)
    if item is not None:
        item.is_active = is_active
        item.updated_at_utc = at_utc


def _deactivate_review_queue_marker_if_empty(
    db: Session,
    user_id: int,
    source: str,
    question_id: int,
    runtime_question_id: int | None,
    diagnostic_question_id: int | None,
    attempt_id: int | None,
    review_reason: str,
    model,
    exclude_id: int,
) -> None:
    conditions = [
        model.user_id == user_id,
        model.is_active == True,
        model.id != exclude_id,
        *_identity_filter(model, source, question_id, runtime_question_id, diagnostic_question_id),
    ]
    if hasattr(model, "attempt_id"):
        conditions.append(model.attempt_id.is_(None) if attempt_id is None else model.attempt_id == attempt_id)
    remaining = db.scalar(select(model.id).where(*conditions))
    if remaining is None:
        _set_review_queue_marker_active(
            db,
            user_id=user_id,
            source=source,
            question_id=question_id,
            runtime_question_id=runtime_question_id,
            diagnostic_question_id=diagnostic_question_id,
            attempt_id=attempt_id,
            review_reason=review_reason,
            is_active=False,
            at_utc=datetime.utcnow(),
        )


def _canonical_source_type(value: str | None) -> str:
    return _normalize_source_filter(value)


def _source_label(source_type: str | None) -> str:
    return {
        "practice": "Bài tập",
        "fulltest": "Full Test",
        "minitest": "Mini Test",
        "weeklycheck": "Weekly Check",
    }.get(_canonical_source_type(source_type), "Review")


def _source_type_for_practice_attempt(attempt: PracticeAttempt) -> str:
    mode = (attempt.mode or "").strip().lower().replace("_", "-")
    return "weeklycheck" if mode == "weekly-check" else "practice"


def _source_type_for_mock_attempt(db: Session, attempt: MockTestAttempt) -> str:
    row = db.execute(
        text(
            """
            SELECT TOP 1 LOWER(s.Type) AS SetType, COUNT(*) AS QuestionCount
            FROM dbo.MockTestAttemptAnswers a
            JOIN dbo.ToeicPracticeQuestions q ON q.Id = a.QuestionId
            JOIN dbo.ToeicPracticeSets s ON s.Id = q.SetId
            WHERE a.MockTestAttemptId = :attempt_id
              AND LOWER(s.Type) IN ('fulltest', 'minitest')
            GROUP BY LOWER(s.Type)
            ORDER BY COUNT(*) DESC
            """
        ),
        {"attempt_id": attempt.id},
    ).first()
    if row:
        set_type = (row._mapping["SetType"] or "").strip().lower()
        if set_type in {"fulltest", "minitest"}:
            return set_type

    title = (attempt.title or "").strip().lower()
    if "mini" in title:
        return "minitest"
    if "full" in title or "mock" in title:
        return "fulltest"
    if attempt.total_questions and attempt.total_questions < 120:
        return "minitest"
    return "fulltest"


def _source_matches_filter(source_type: str | None, source_filter: str) -> bool:
    return source_filter == "all" or _canonical_source_type(source_type) == source_filter


def _load_review_debug_set_meta(db: Session, question_ids: list[int | None]) -> dict[int, dict[str, Any]]:
    ids = sorted({int(value) for value in question_ids if value and int(value) > 0})
    if not ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT q.Id AS QuestionId, q.SetId, s.Type AS SetType
            FROM dbo.ToeicPracticeQuestions q
            LEFT JOIN dbo.ToeicPracticeSets s ON s.Id = q.SetId
            WHERE q.Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            """
        ),
        {"ids_csv": ",".join(str(value) for value in ids)},
    ).all()
    return {int(row._mapping["QuestionId"]): dict(row._mapping) for row in rows}


def _get_scoped_review_question_ids(
    db: Session,
    user_id: int,
    source_filter: str,
    attempt_id: int | None,
) -> set[int] | None:
    if source_filter == "all" and not attempt_id:
        return None

    question_ids: set[int] = set()

    if source_filter in {"all", "practice", "weeklycheck"}:
        practice_query = (
            select(PracticeAttemptAnswer, PracticeAttempt)
            .join(PracticeAttempt, PracticeAttempt.id == PracticeAttemptAnswer.practice_attempt_id)
            .where(PracticeAttempt.user_id == user_id)
        )
        if attempt_id:
            practice_query = practice_query.where(PracticeAttempt.id == attempt_id)
        for answer, attempt in db.execute(practice_query).all():
            attempt_source_type = _source_type_for_practice_attempt(attempt)
            if _source_matches_filter(attempt_source_type, source_filter):
                question_ids.add(answer.question_id)

    if source_filter in {"all", "fulltest", "minitest"}:
        mock_query = (
            select(MockTestAttemptAnswer, MockTestAttempt)
            .join(MockTestAttempt, MockTestAttempt.id == MockTestAttemptAnswer.mock_test_attempt_id)
            .where(MockTestAttempt.user_id == user_id)
        )
        if attempt_id:
            mock_query = mock_query.where(MockTestAttempt.id == attempt_id)
        mock_source_cache: dict[int, str] = {}
        for answer, attempt in db.execute(mock_query).all():
            attempt_source_type = mock_source_cache.get(attempt.id)
            if attempt_source_type is None:
                attempt_source_type = _source_type_for_mock_attempt(db, attempt)
                mock_source_cache[attempt.id] = attempt_source_type
            if _source_matches_filter(attempt_source_type, source_filter):
                question_ids.add(answer.question_id)

    return question_ids


def _label_from_index(index: int | None) -> str | None:
    if index is None or index < 0 or index > 25:
        return None
    return chr(ord("A") + index)


@dataclass
class _ReviewSeed:
    raw_question_id: int
    question_id: int | None = None
    part: int | None = None
    question_number: int | None = None
    source_type: str | None = None
    source_attempt_id: int | None = None
    source_queue_id: int | None = None
    user_selected_option_label: str | None = None
    is_correct: bool | None = None
    status: str = "active"
    priority: int = 0

    def with_question_id(self, question_id: int) -> "_ReviewSeed":
        return _ReviewSeed(
            raw_question_id=self.raw_question_id,
            question_id=question_id,
            part=self.part,
            question_number=self.question_number,
            source_type=self.source_type,
            source_attempt_id=self.source_attempt_id,
            source_queue_id=self.source_queue_id,
            user_selected_option_label=self.user_selected_option_label,
            is_correct=self.is_correct,
            status=self.status,
            priority=self.priority,
        )

    def merge(self, other: "_ReviewSeed") -> None:
        if other.priority >= self.priority:
            other_source = _canonical_source_type(other.source_type)
            current_source = _canonical_source_type(self.source_type)
            if other_source != "all" or current_source == "all":
                self.source_type = other.source_type or self.source_type
            self.source_attempt_id = other.source_attempt_id or self.source_attempt_id
            self.source_queue_id = other.source_queue_id or self.source_queue_id
            self.user_selected_option_label = other.user_selected_option_label or self.user_selected_option_label
            self.is_correct = other.is_correct if other.is_correct is not None else self.is_correct
            self.status = other.status or self.status
            self.priority = other.priority


def _collect_review_seeds(
    db: Session,
    user_id: int,
    filter_name: str,
    limit: int,
    source_filter: str = "all",
    attempt_id: int | None = None,
) -> list[_ReviewSeed]:
    seeds: list[_ReviewSeed] = []
    scoped_question_ids = _get_scoped_review_question_ids(db, user_id, source_filter, attempt_id)
    if scoped_question_ids is not None and not scoped_question_ids:
        return []

    def include_attempts() -> bool:
        return filter_name in {"all", "wrong", "correct"}

    if include_attempts():
        practice_query = (
            select(PracticeAttemptAnswer, PracticeAttempt)
            .join(PracticeAttempt, PracticeAttempt.id == PracticeAttemptAnswer.practice_attempt_id)
            .where(PracticeAttempt.user_id == user_id)
            .order_by(func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc).desc())
            .limit(limit * 3)
        )
        if attempt_id and source_filter in {"all", "practice", "weeklycheck"}:
            practice_query = practice_query.where(PracticeAttempt.id == attempt_id)
        elif source_filter in {"fulltest", "minitest"}:
            practice_query = practice_query.where(PracticeAttempt.id == -1)
        mock_query = (
            select(MockTestAttemptAnswer, MockTestAttempt)
            .join(MockTestAttempt, MockTestAttempt.id == MockTestAttemptAnswer.mock_test_attempt_id)
            .where(MockTestAttempt.user_id == user_id)
            .order_by(func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc).desc())
            .limit(limit * 3)
        )
        if attempt_id and source_filter in {"all", "fulltest", "minitest"}:
            mock_query = mock_query.where(MockTestAttempt.id == attempt_id)
        elif source_filter in {"practice", "weeklycheck"}:
            mock_query = mock_query.where(MockTestAttempt.id == -1)
        for answer, attempt in db.execute(practice_query).all():
            attempt_source_type = _source_type_for_practice_attempt(attempt)
            if not _source_matches_filter(attempt_source_type, source_filter):
                continue
            if filter_name == "wrong" and answer.is_correct:
                continue
            if filter_name == "correct" and not answer.is_correct:
                continue
            seeds.append(
                _ReviewSeed(
                    raw_question_id=answer.question_id,
                    part=answer.part,
                    question_number=answer.question_number,
                    source_type=attempt_source_type,
                    source_attempt_id=attempt.id,
                    user_selected_option_label=_label_from_index(answer.selected_answer_index),
                    is_correct=bool(answer.is_correct),
                    status="reviewed" if answer.is_correct else "pending",
                    priority=80,
                )
            )
        for answer, attempt in db.execute(mock_query).all():
            attempt_source_type = _source_type_for_mock_attempt(db, attempt)
            if not _source_matches_filter(attempt_source_type, source_filter):
                continue
            if filter_name == "wrong" and answer.is_correct:
                continue
            if filter_name == "correct" and not answer.is_correct:
                continue
            seeds.append(
                _ReviewSeed(
                    raw_question_id=answer.question_id,
                    part=answer.part,
                    question_number=answer.question_number,
                    source_type=attempt_source_type,
                    source_attempt_id=attempt.id,
                    user_selected_option_label=_label_from_index(answer.selected_answer_index),
                    is_correct=bool(answer.is_correct),
                    status="reviewed" if answer.is_correct else "pending",
                    priority=75,
                )
            )

    if filter_name in {"all", "wrong"}:
        queue_query = (
            select(ReviewQueueItem)
            .where(ReviewQueueItem.user_id == user_id)
            .order_by(ReviewQueueItem.added_at_utc.desc())
            .limit(limit * 2)
        )
        if attempt_id:
            queue_query = queue_query.where(ReviewQueueItem.source_attempt_id == attempt_id)
        if scoped_question_ids is not None:
            queue_query = queue_query.where(ReviewQueueItem.question_id.in_(scoped_question_ids))
        queue_rows = db.scalars(queue_query).all()
        for item in queue_rows:
            item_source = _canonical_source_type(item.source_attempt_type or "review_queue")
            if source_filter != "all" and item_source == "all":
                item_source = source_filter
            if not _source_matches_filter(item_source, source_filter):
                continue
            seeds.append(
                _ReviewSeed(
                    raw_question_id=item.question_id,
                    part=item.part,
                    source_type=item_source,
                    source_attempt_id=item.source_attempt_id,
                    source_queue_id=item.id,
                    is_correct=False if item.status == "pending" else None,
                    status=item.status or "pending",
                    priority=60,
                )
            )

    if filter_name in {"all", "bookmarked", "notebook"}:
        bookmark_query = (
            select(UserQuestionBookmark)
            .where(UserQuestionBookmark.user_id == user_id)
            .order_by(UserQuestionBookmark.created_at.desc())
            .limit(limit * 2)
        )
        if attempt_id:
            bookmark_query = bookmark_query.where(UserQuestionBookmark.attempt_id == attempt_id)
        if scoped_question_ids is not None:
            bookmark_query = bookmark_query.where(UserQuestionBookmark.question_id.in_(scoped_question_ids))
        for item in db.scalars(bookmark_query).all():
            seeds.append(
                _ReviewSeed(
                    raw_question_id=item.question_id,
                    source_type=source_filter if source_filter != "all" else "bookmark",
                    source_attempt_id=item.attempt_id,
                    status="bookmarked",
                    priority=90 if filter_name == "bookmarked" else 55,
                )
            )

    if filter_name in {"all", "notes", "notebook"}:
        note_query = (
            select(UserQuestionNote)
            .where(UserQuestionNote.user_id == user_id)
            .order_by(UserQuestionNote.updated_at.desc(), UserQuestionNote.id.desc())
            .limit(limit * 2)
        )
        if attempt_id:
            note_query = note_query.where(UserQuestionNote.attempt_id == attempt_id)
        if scoped_question_ids is not None:
            note_query = note_query.where(UserQuestionNote.question_id.in_(scoped_question_ids))
        for item in db.scalars(note_query).all():
            seeds.append(
                _ReviewSeed(
                    raw_question_id=item.question_id,
                    source_type=source_filter if source_filter != "all" else "note",
                    source_attempt_id=item.attempt_id,
                    status="notebook",
                    priority=95 if filter_name == "notes" else 58,
                )
            )

    if filter_name in {"all", "highlights", "notebook"}:
        highlight_query = (
            select(UserQuestionHighlight)
            .where(UserQuestionHighlight.user_id == user_id)
            .order_by(UserQuestionHighlight.updated_at.desc(), UserQuestionHighlight.id.desc())
            .limit(limit * 2)
        )
        if attempt_id:
            highlight_query = highlight_query.where(UserQuestionHighlight.attempt_id == attempt_id)
        if scoped_question_ids is not None:
            highlight_query = highlight_query.where(UserQuestionHighlight.question_id.in_(scoped_question_ids))
        for item in db.scalars(highlight_query).all():
            seeds.append(
                _ReviewSeed(
                    raw_question_id=item.question_id,
                    source_type=source_filter if source_filter != "all" else "highlight",
                    source_attempt_id=item.attempt_id,
                    status="notebook",
                    priority=95 if filter_name == "highlights" else 57,
                )
            )

    return seeds[: limit * 4]


def _resolve_seed_question_ids(db: Session, seeds: list[_ReviewSeed]) -> dict[int, int]:
    raw_ids = sorted({seed.raw_question_id for seed in seeds if seed.raw_question_id > 0})
    if not raw_ids:
        return {}

    practice_meta = _load_practice_question_meta(db, raw_ids)
    direct_meta = _load_docx_question_meta(db, raw_ids)
    internal_rows = {
        row.id: row
        for row in db.scalars(select(ToeicQuestion).where(ToeicQuestion.id.in_(raw_ids))).all()
    }
    internal_docx_cache: dict[int, int | None] = {}
    resolved: dict[int, int] = {}

    for seed in seeds:
        raw_id = seed.raw_question_id
        practice = practice_meta.get(raw_id)
        if practice and _matches_practice_seed_meta(seed, practice) and _should_load_seed_from_practice(seed):
            resolved[raw_id] = raw_id
            continue
        direct = direct_meta.get(raw_id)
        if direct and _matches_seed_meta(seed, direct):
            resolved[raw_id] = raw_id
            continue
        if practice and _matches_practice_seed_meta(seed, practice) and not _should_load_seed_from_legacy(seed):
            resolved[raw_id] = raw_id
            continue
        internal = internal_rows.get(raw_id)
        if internal is not None:
            if raw_id not in internal_docx_cache:
                internal_docx_cache[raw_id] = _find_docx_id_for_internal_question(db, internal)
            docx_id = internal_docx_cache[raw_id]
            if docx_id:
                resolved[raw_id] = docx_id
                continue
        if direct:
            resolved[raw_id] = raw_id

    return resolved


def _should_load_seed_from_practice(seed: _ReviewSeed) -> bool:
    source_type = (seed.source_type or "").strip().lower().replace("_", "-")
    return source_type in {"practice", "mock-test", "weekly", "weekly-check", "review-focus"}


def _should_load_seed_from_legacy(seed: _ReviewSeed) -> bool:
    source_type = (seed.source_type or "").strip().lower().replace("_", "-")
    return source_type in {"diagnostic", "placement", "placement-test"}


def _matches_seed_meta(seed: _ReviewSeed, meta: dict[str, Any]) -> bool:
    if seed.part and meta.get("PartNumber") and int(meta["PartNumber"]) != int(seed.part):
        return False
    if seed.question_number and meta.get("QuestionNumber") and int(meta["QuestionNumber"]) != int(seed.question_number):
        return False
    return True


def _matches_practice_seed_meta(seed: _ReviewSeed, meta: dict[str, Any]) -> bool:
    if seed.part and meta.get("PartNumber") and int(meta["PartNumber"]) != int(seed.part):
        return False
    return True


def _load_practice_question_meta(db: Session, ids: list[int]) -> dict[int, dict[str, Any]]:
    if not ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT Id, Part AS PartNumber, QuestionNumber
            FROM dbo.ToeicPracticeQuestions
            WHERE Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            """
        ),
        {"ids_csv": ",".join(str(value) for value in ids)},
    ).all()
    return {int(row._mapping["Id"]): dict(row._mapping) for row in rows}


def _load_docx_question_meta(db: Session, ids: list[int]) -> dict[int, dict[str, Any]]:
    if not ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT Id, PartNumber, QuestionNumber
            FROM dbo.ToeicDocxQuestions
            WHERE Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            """
        ),
        {"ids_csv": ",".join(str(value) for value in ids)},
    ).all()
    return {int(row._mapping["Id"]): dict(row._mapping) for row in rows}


def _find_docx_id_for_internal_question(db: Session, question: ToeicQuestion) -> int | None:
    row = db.execute(
        text(
            """
            SELECT TOP 1 Id
            FROM dbo.ToeicDocxQuestions
            WHERE QuestionNumber = :question_number
              AND PartNumber = :part
              AND (:test_number IS NULL OR TestNumber = :test_number)
              AND QuestionTextEn = :question_text
            ORDER BY Id
            """
        ),
        {
            "question_number": question.question_number,
            "part": question.part,
            "test_number": question.test_number,
            "question_text": question.question_text,
        },
    ).first()
    return int(row._mapping["Id"]) if row else None


def _load_practice_questions(db: Session, question_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not question_ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT
                q.Id,
                q.Id AS RuntimeQuestionId,
                q.QuestionNumber,
                q.Part AS PartNumber,
                q.Section,
                CONCAT('Part ', q.Part) AS PartLabel,
                CONCAT('part', q.Part) AS QuestionType,
                q.SkillCode,
                NULL AS SubskillCode,
                NULL AS Topic,
                q.Difficulty,
                q.TestNumber,
                q.QuestionText AS QuestionTextEn,
                q.PassageId,
                p.GroupCode AS PassageGroupCode,
                NULL AS PassageTitle,
                p.PassageText,
                p.AudioPath AS PassageAudioPath,
                p.ImagePath AS PassageImagePath,
                q.CorrectOptionKey AS CorrectOptionLabel,
                correct.OptionText AS CorrectAnswerText,
                q.Explanation AS ExplanationDetail,
                NULL AS OptionAnalysis,
                NULL AS VocabularyNotes,
                NULL AS TranslationVi,
                NULL AS FinalTranslationVi,
                NULL AS RawBlock
            FROM dbo.ToeicPracticeQuestions q
            LEFT JOIN dbo.ToeicPracticePassages p ON p.Id = q.PassageId
            OUTER APPLY (
                SELECT TOP 1 o.OptionText
                FROM dbo.ToeicPracticeQuestionOptions o
                WHERE o.QuestionId = q.Id
                  AND (o.IsCorrect = 1 OR o.OptionKey = q.CorrectOptionKey)
                ORDER BY CASE WHEN o.IsCorrect = 1 THEN 0 ELSE 1 END, o.SortOrder
            ) correct
            WHERE q.Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            """
        ),
        {"ids_csv": ",".join(str(value) for value in question_ids)},
    ).all()
    return {int(row._mapping["Id"]): dict(row._mapping) for row in rows}


def _load_docx_questions(db: Session, question_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not question_ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT Id, QuestionNumber, PartNumber, QuestionTextEn, PassageText,
                   CorrectOptionLabel, CorrectAnswerText, ExplanationDetail,
                   OptionAnalysis, VocabularyNotes, TranslationVi, FinalTranslationVi, RawBlock
            FROM dbo.ToeicDocxQuestions
            WHERE Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            """
        ),
        {"ids_csv": ",".join(str(value) for value in question_ids)},
    ).all()
    return {int(row._mapping["Id"]): dict(row._mapping) for row in rows}


def _load_practice_options(db: Session, question_ids: list[int]) -> dict[int, list[ReviewOptionResponse]]:
    if not question_ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT
                o.QuestionId,
                q.Part,
                q.SetId,
                o.OptionKey,
                o.OptionText,
                o.IsCorrect,
                o.SortOrder
            FROM dbo.ToeicPracticeQuestionOptions o
            JOIN dbo.ToeicPracticeQuestions q ON q.Id = o.QuestionId
            WHERE o.QuestionId IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            ORDER BY o.QuestionId, o.SortOrder
            """
        ),
        {"ids_csv": ",".join(str(value) for value in question_ids)},
    ).all()
    result: dict[int, list[ReviewOptionResponse]] = {}
    for row in rows:
        data = row._mapping
        question_id = int(data["QuestionId"])
        option_key = str(data["OptionKey"] or "")
        option_text = str(data["OptionText"] or "")
        if not option_text.strip():
            option_text = option_key
        warning_key = (question_id, option_key)
        if not option_text.strip() and warning_key not in _OPTION_WARNING_KEYS:
            _OPTION_WARNING_KEYS.add(warning_key)
            logger.warning(
                "Review option text missing for runtime question id=%s part=%s set_id=%s source=ToeicPracticeQuestionOptions option=%s",
                question_id,
                data.get("Part"),
                data.get("SetId"),
                option_key,
            )
        result.setdefault(question_id, []).append(
            ReviewOptionResponse(
                option_label=option_key,
                option_text_en=option_text,
                is_correct=bool(data["IsCorrect"]),
                sort_order=int(data["SortOrder"] or 0),
                option_key=option_key,
                option_text=option_text,
                key=option_key,
                text=option_text,
            )
        )
    missing_question_ids = [question_id for question_id in question_ids if question_id not in result]
    if missing_question_ids:
        fallback_rows = db.execute(
            text(
                """
                SELECT Id, Part, CorrectOptionKey
                FROM dbo.ToeicPracticeQuestions
                WHERE Id IN (
                    SELECT TRY_CAST(value AS INT)
                    FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                    WHERE TRY_CAST(value AS INT) IS NOT NULL
                )
                  AND Part IN (1, 2)
                """
            ),
            {"ids_csv": ",".join(str(value) for value in missing_question_ids)},
        ).mappings().all()
        for row in fallback_rows:
            question_id = int(row["Id"])
            correct_key = str(row["CorrectOptionKey"] or "").strip().upper()
            result[question_id] = [
                ReviewOptionResponse(
                    option_label=option_key,
                    option_text_en=option_key,
                    is_correct=option_key == correct_key,
                    sort_order=index,
                    option_key=option_key,
                    option_text=option_key,
                    key=option_key,
                    text=option_key,
                )
                for index, option_key in enumerate(["A", "B", "C", "D"], start=1)
            ]
    return result


def _load_practice_assets(db: Session, question_ids: list[int]) -> dict[int, dict[str, str]]:
    if not question_ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT
                q.Id AS QuestionId,
                a.QuestionId AS AssetQuestionId,
                a.PassageId AS AssetPassageId,
                a.AssetType,
                a.RelativePath
            FROM dbo.ToeicPracticeQuestions q
            JOIN dbo.ToeicPracticeQuestionAssets a
              ON a.QuestionId = q.Id
              OR (q.PassageId IS NOT NULL AND a.PassageId = q.PassageId)
            WHERE q.Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            ORDER BY q.Id,
                     CASE WHEN a.QuestionId = q.Id THEN 0 ELSE 1 END,
                     a.Id
            """
        ),
        {"ids_csv": ",".join(str(value) for value in question_ids)},
    ).mappings().all()
    result: dict[int, dict[str, str]] = {}
    for row in rows:
        question_id = int(row["QuestionId"])
        asset_type = str(row["AssetType"] or "").strip().lower()
        relative_path = str(row["RelativePath"] or "").strip()
        if not asset_type or not relative_path:
            continue
        data = result.setdefault(question_id, {})
        is_question_asset = row["AssetQuestionId"] is not None
        prefix = "" if is_question_asset else "passage_"
        if asset_type == "audio":
            data.setdefault(f"{prefix}audio_path", relative_path)
        elif asset_type in {"image", "graphic"}:
            data.setdefault(f"{prefix}image_path", relative_path)
    return result


def _load_practice_explanations(db: Session, question_ids: list[int]) -> dict[int, dict[str, str]]:
    if not question_ids:
        return {}
    table_exists = db.execute(
        text("SELECT OBJECT_ID(N'dbo.ToeicQuestionExplanations', N'U')")
    ).scalar()
    if not table_exists:
        return {}
    rows = db.execute(
        text(
            """
            SELECT
                RuntimeQuestionId,
                PassageText,
                ExplanationText,
                RawBlock
            FROM dbo.ToeicQuestionExplanations
            WHERE RuntimeQuestionId IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            ORDER BY Id
            """
        ),
        {"ids_csv": ",".join(str(value) for value in question_ids)},
    ).mappings().all()
    result: dict[int, dict[str, str]] = {}
    for row in rows:
        question_id = row["RuntimeQuestionId"]
        if question_id is None:
            continue
        result.setdefault(int(question_id), dict(row))
    return result


def _load_diagnostic_questions(db: Session, question_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not question_ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT
                q.Id,
                q.QuestionNumber,
                q.Part AS PartNumber,
                q.Section,
                COALESCE(q.PartLabel, CONCAT('Part ', q.Part)) AS PartLabel,
                q.QuestionType,
                q.SkillCode,
                q.SubskillCode,
                q.Topic,
                q.Difficulty,
                q.TestNumber,
                q.QuestionText AS QuestionTextEn,
                q.PassageId,
                p.GroupCode AS PassageGroupCode,
                p.Title AS PassageTitle,
                p.PassageText,
                p.AudioPath AS PassageAudioPath,
                p.ImagePath AS PassageImagePath,
                q.CorrectOptionKey AS CorrectOptionLabel,
                correct.OptionText AS CorrectAnswerText,
                q.Explanation AS ExplanationDetail,
                NULL AS OptionAnalysis,
                NULL AS VocabularyNotes,
                NULL AS TranslationVi,
                NULL AS FinalTranslationVi,
                NULL AS RawBlock
            FROM dbo.ToeicQuestions q
            LEFT JOIN dbo.ToeicPassages p ON p.Id = q.PassageId
            OUTER APPLY (
                SELECT TOP 1 o.OptionText
                FROM dbo.ToeicQuestionOptions o
                WHERE o.QuestionId = q.Id
                  AND o.OptionKey = q.CorrectOptionKey
                ORDER BY o.SortOrder
            ) correct
            WHERE q.Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            """
        ),
        {"ids_csv": ",".join(str(value) for value in question_ids)},
    ).all()
    return {int(row._mapping["Id"]): dict(row._mapping) for row in rows}


def _load_diagnostic_options(db: Session, question_ids: list[int]) -> dict[int, list[ReviewOptionResponse]]:
    if not question_ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT QuestionId, OptionKey, OptionText, SortOrder
            FROM dbo.ToeicQuestionOptions
            WHERE QuestionId IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            ORDER BY QuestionId, SortOrder
            """
        ),
        {"ids_csv": ",".join(str(value) for value in question_ids)},
    ).all()
    result: dict[int, list[ReviewOptionResponse]] = {}
    correct_by_question = {
        int(row._mapping["Id"]): str(row._mapping["CorrectOptionKey"] or "")
        for row in db.execute(
            text(
                """
                SELECT Id, CorrectOptionKey
                FROM dbo.ToeicQuestions
                WHERE Id IN (
                    SELECT TRY_CAST(value AS INT)
                    FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                    WHERE TRY_CAST(value AS INT) IS NOT NULL
                )
                """
            ),
            {"ids_csv": ",".join(str(value) for value in question_ids)},
        ).all()
    }
    for row in rows:
        data = row._mapping
        question_id = int(data["QuestionId"])
        option_key = str(data["OptionKey"] or "")
        option_text = str(data["OptionText"] or "")
        result.setdefault(question_id, []).append(
            ReviewOptionResponse(
                option_label=option_key,
                option_text_en=option_text,
                is_correct=option_key == correct_by_question.get(question_id),
                sort_order=int(data["SortOrder"] or 0),
                option_key=option_key,
                option_text=option_text,
                key=option_key,
                text=option_text,
            )
        )
    return result


def _queue_identity_sets(queue_items: list[ReviewQueueItem]) -> tuple[set[int], set[int], set[int]]:
    runtime_ids = {
        int(item.runtime_question_id)
        for item in queue_items
        if item.runtime_question_id is not None
    }
    diagnostic_ids = {
        int(item.diagnostic_question_id)
        for item in queue_items
        if item.diagnostic_question_id is not None
    }
    question_ids = {
        int(item.question_id)
        for item in queue_items
        if item.question_id is not None
    }
    return runtime_ids, diagnostic_ids, question_ids


def _load_notes_by_identity(
    db: Session,
    user_id: int,
    queue_items: list[ReviewQueueItem],
) -> dict[tuple[str, int], list[UserQuestionNote]]:
    runtime_ids, diagnostic_ids, question_ids = _queue_identity_sets(queue_items)
    if not (runtime_ids or diagnostic_ids or question_ids):
        return {}
    rows = db.scalars(
        select(UserQuestionNote)
        .where(
            UserQuestionNote.user_id == user_id,
            UserQuestionNote.is_active == True,
            or_(
                UserQuestionNote.runtime_question_id.in_(runtime_ids or {-1}),
                UserQuestionNote.diagnostic_question_id.in_(diagnostic_ids or {-1}),
                UserQuestionNote.question_id.in_(question_ids or {-1}),
            ),
        )
        .order_by(UserQuestionNote.updated_at.desc(), UserQuestionNote.id.desc())
    ).all()
    result: dict[tuple[str, int], list[UserQuestionNote]] = {}
    valid_keys = {_queue_identity_key(item) for item in queue_items}
    for item in rows:
        key = _notebook_identity_key(item)
        if key in valid_keys and key not in result:
            result[key] = [item]
    return result


def _load_highlights_by_identity(
    db: Session,
    user_id: int,
    queue_items: list[ReviewQueueItem],
) -> dict[tuple[str, int], list[UserQuestionHighlight]]:
    runtime_ids, diagnostic_ids, question_ids = _queue_identity_sets(queue_items)
    if not (runtime_ids or diagnostic_ids or question_ids):
        return {}
    rows = db.scalars(
        select(UserQuestionHighlight)
        .where(
            UserQuestionHighlight.user_id == user_id,
            UserQuestionHighlight.is_active == True,
            or_(
                UserQuestionHighlight.runtime_question_id.in_(runtime_ids or {-1}),
                UserQuestionHighlight.diagnostic_question_id.in_(diagnostic_ids or {-1}),
                UserQuestionHighlight.question_id.in_(question_ids or {-1}),
            ),
        )
        .order_by(UserQuestionHighlight.updated_at.desc(), UserQuestionHighlight.id.desc())
    ).all()
    result: dict[tuple[str, int], list[UserQuestionHighlight]] = {}
    valid_keys = {_queue_identity_key(item) for item in queue_items}
    for item in rows:
        key = _notebook_identity_key(item)
        if key in valid_keys:
            result.setdefault(key, []).append(item)
    return result


def _load_bookmarked_identities(
    db: Session,
    user_id: int,
    queue_items: list[ReviewQueueItem],
) -> set[tuple[str, int]]:
    runtime_ids, diagnostic_ids, question_ids = _queue_identity_sets(queue_items)
    if not (runtime_ids or diagnostic_ids or question_ids):
        return set()
    rows = db.scalars(
        select(UserQuestionBookmark).where(
            UserQuestionBookmark.user_id == user_id,
            UserQuestionBookmark.is_active == True,
            or_(
                UserQuestionBookmark.runtime_question_id.in_(runtime_ids or {-1}),
                UserQuestionBookmark.diagnostic_question_id.in_(diagnostic_ids or {-1}),
                UserQuestionBookmark.question_id.in_(question_ids or {-1}),
            ),
        )
    ).all()
    valid_keys = {_queue_identity_key(item) for item in queue_items}
    return {key for item in rows if (key := _notebook_identity_key(item)) in valid_keys}


def _review_asset(path: str | None) -> ReviewAssetResponse | None:
    return ReviewAssetResponse(path=path) if path else None


def _normalize_review_asset_path(path: str | None, asset_type: str) -> str | None:
    value = str(path or "").strip().replace("\\", "/")
    if not value:
        return None
    if value.lower().startswith(("http://", "https://", "data:")):
        return value
    if value.startswith("/toeic/"):
        return value
    if value.startswith("toeic/"):
        return f"/{value}"

    normalized = value.lstrip("/")
    lower_value = normalized.lower()
    if lower_value.startswith(("audio/", "images/", "image/")):
        return f"/toeic/{normalized}"
    if asset_type.lower() == "audio":
        return f"/toeic/audio/{normalized}"
    return f"/toeic/images/{normalized}"


def _load_docx_options(db: Session, question_ids: list[int]) -> dict[int, list[ReviewOptionResponse]]:
    if not question_ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT QuestionId, OptionLabel, OptionTextEn, IsCorrect, SortOrder
            FROM dbo.ToeicDocxOptions
            WHERE QuestionId IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(CAST(:ids_csv AS NVARCHAR(MAX)), ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            ORDER BY QuestionId, SortOrder
            """
        ),
        {"ids_csv": ",".join(str(value) for value in question_ids)},
    ).all()
    result: dict[int, list[ReviewOptionResponse]] = {}
    for row in rows:
        data = row._mapping
        question_id = int(data["QuestionId"])
        result.setdefault(question_id, []).append(
            ReviewOptionResponse(
                option_label=str(data["OptionLabel"] or ""),
                option_text_en=str(data["OptionTextEn"] or ""),
                is_correct=bool(data["IsCorrect"]),
                sort_order=int(data["SortOrder"] or 0),
                option_key=str(data["OptionLabel"] or ""),
                option_text=str(data["OptionTextEn"] or ""),
                key=str(data["OptionLabel"] or ""),
                text=str(data["OptionTextEn"] or ""),
            )
        )
    return result


def _load_notes_by_question(db: Session, user_id: int, question_ids: list[int]) -> dict[int, list[UserQuestionNote]]:
    rows = db.scalars(
        select(UserQuestionNote)
        .where(UserQuestionNote.user_id == user_id, UserQuestionNote.question_id.in_(question_ids))
        .order_by(UserQuestionNote.updated_at.desc(), UserQuestionNote.id.desc())
    ).all()
    result: dict[int, list[UserQuestionNote]] = {}
    for item in rows:
        result.setdefault(item.question_id, []).append(item)
    return result


def _load_highlights_by_question(db: Session, user_id: int, question_ids: list[int]) -> dict[int, list[UserQuestionHighlight]]:
    rows = db.scalars(
        select(UserQuestionHighlight)
        .where(UserQuestionHighlight.user_id == user_id, UserQuestionHighlight.question_id.in_(question_ids))
        .order_by(UserQuestionHighlight.updated_at.desc(), UserQuestionHighlight.id.desc())
    ).all()
    result: dict[int, list[UserQuestionHighlight]] = {}
    for item in rows:
        result.setdefault(item.question_id, []).append(item)
    return result


def _load_bookmarked_ids(db: Session, user_id: int, question_ids: list[int]) -> set[int]:
    rows = db.scalars(
        select(UserQuestionBookmark.question_id).where(
            UserQuestionBookmark.user_id == user_id,
            UserQuestionBookmark.question_id.in_(question_ids),
        )
    ).all()
    return {int(value) for value in rows}
