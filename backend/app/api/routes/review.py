from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
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
    BookmarkResponse,
    BookmarkToggleRequest,
    HighlightCreate,
    HighlightResponse,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    ReviewItemResponse,
    ReviewOptionResponse,
)
from app.services.learning_analytics import get_review_item_detail, get_review_summary, mark_review_item_reviewed


router = APIRouter()


@router.get("/api/review/notes", response_model=list[NoteResponse])
def get_notes_route(
    question_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    return db.scalars(
        select(UserQuestionNote)
        .where(UserQuestionNote.user_id == user_id, UserQuestionNote.question_id == question_id)
        .order_by(UserQuestionNote.updated_at.desc(), UserQuestionNote.id.desc())
    ).all()


@router.post("/api/review/notes", response_model=NoteResponse)
def save_note_route(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    note_text = payload.note_text.strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required.")

    note = db.scalar(
        select(UserQuestionNote).where(
            UserQuestionNote.user_id == user_id,
            UserQuestionNote.question_id == payload.question_id,
        )
    )
    now = datetime.utcnow()
    if note is None:
        note = UserQuestionNote(
            user_id=user_id,
            question_id=payload.question_id,
            attempt_id=payload.attempt_id,
            note_text=note_text,
            created_at=now,
            updated_at=now,
        )
        db.add(note)
    else:
        note.note_text = note_text
        note.attempt_id = payload.attempt_id or note.attempt_id
        note.updated_at = now
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
    note = db.scalar(select(UserQuestionNote).where(UserQuestionNote.id == note_id, UserQuestionNote.user_id == user_id))
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    note_text = payload.note_text.strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="note_text is required.")
    note.note_text = note_text
    note.updated_at = datetime.utcnow()
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
    note = db.scalar(select(UserQuestionNote).where(UserQuestionNote.id == note_id, UserQuestionNote.user_id == user_id))
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    db.delete(note)
    db.commit()
    return {"deleted": True, "id": note_id}


@router.get("/api/review/highlights", response_model=list[HighlightResponse])
def get_highlights_route(
    question_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    return db.scalars(
        select(UserQuestionHighlight)
        .where(UserQuestionHighlight.user_id == user_id, UserQuestionHighlight.question_id == question_id)
        .order_by(UserQuestionHighlight.updated_at.desc(), UserQuestionHighlight.id.desc())
    ).all()


@router.post("/api/review/highlights", response_model=HighlightResponse)
def create_highlight_route(
    payload: HighlightCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    selected_text = payload.selected_text.strip()
    if not selected_text:
        raise HTTPException(status_code=400, detail="selected_text is required.")
    now = datetime.utcnow()
    highlight = UserQuestionHighlight(
        user_id=user_id,
        question_id=payload.question_id,
        attempt_id=payload.attempt_id,
        target_type=(payload.target_type or "question_text").strip()[:50],
        target_key=(payload.target_key or "").strip()[:20] or None,
        selected_text=selected_text,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        color=(payload.color or "yellow").strip()[:30],
        note_text=payload.note_text.strip() if payload.note_text and payload.note_text.strip() else None,
        created_at=now,
        updated_at=now,
    )
    db.add(highlight)
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
    highlight = db.scalar(
        select(UserQuestionHighlight).where(
            UserQuestionHighlight.id == highlight_id,
            UserQuestionHighlight.user_id == user_id,
        )
    )
    if highlight is None:
        raise HTTPException(status_code=404, detail="Highlight not found.")
    db.delete(highlight)
    db.commit()
    return {"deleted": True, "id": highlight_id}


@router.get("/api/review/bookmarks", response_model=BookmarkResponse)
def get_bookmark_route(
    question_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    bookmarked = db.scalar(
        select(UserQuestionBookmark.id).where(
            UserQuestionBookmark.user_id == user_id,
            UserQuestionBookmark.question_id == question_id,
        )
    )
    return BookmarkResponse(question_id=question_id, bookmarked=bookmarked is not None)


@router.post("/api/review/bookmarks/toggle", response_model=BookmarkResponse)
def toggle_bookmark_route(
    payload: BookmarkToggleRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    existing = db.scalar(
        select(UserQuestionBookmark).where(
            UserQuestionBookmark.user_id == user_id,
            UserQuestionBookmark.question_id == payload.question_id,
        )
    )
    if existing is not None:
        db.delete(existing)
        db.commit()
        return BookmarkResponse(question_id=payload.question_id, bookmarked=False)

    bookmark = UserQuestionBookmark(
        user_id=user_id,
        question_id=payload.question_id,
        attempt_id=payload.attempt_id,
        created_at=datetime.utcnow(),
    )
    db.add(bookmark)
    db.commit()
    return BookmarkResponse(question_id=payload.question_id, bookmarked=True)


@router.get("/api/review/items", response_model=list[ReviewItemResponse])
def get_review_items_route(
    filter: str = Query("all"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    _require_user(user_id)
    normalized_filter = _normalize_filter(filter)
    seeds = _collect_review_seeds(db, user_id, normalized_filter, limit)
    if not seeds:
        return []

    resolved_ids = _resolve_seed_question_ids(db, seeds)
    items_by_question: dict[int, _ReviewSeed] = {}
    for seed in seeds:
        docx_id = resolved_ids.get(seed.raw_question_id)
        if not docx_id:
            continue
        existing = items_by_question.get(docx_id)
        if existing is None:
            items_by_question[docx_id] = seed.with_question_id(docx_id)
            continue
        existing.merge(seed.with_question_id(docx_id))

    question_ids = list(items_by_question.keys())[:limit]
    if not question_ids:
        return []

    question_rows = _load_docx_questions(db, question_ids)
    option_rows = _load_docx_options(db, question_ids)
    notes_by_question = _load_notes_by_question(db, user_id, question_ids)
    highlights_by_question = _load_highlights_by_question(db, user_id, question_ids)
    bookmarked_ids = _load_bookmarked_ids(db, user_id, question_ids)

    result: list[ReviewItemResponse] = []
    for question_id in question_ids:
        question = question_rows.get(question_id)
        if not question:
            continue
        seed = items_by_question[question_id]
        result.append(
            ReviewItemResponse(
                question_id=question_id,
                question_number=question.get("QuestionNumber"),
                part_number=question.get("PartNumber"),
                question_text_en=question.get("QuestionTextEn") or "",
                passage_text=question.get("PassageText"),
                options=option_rows.get(question_id, []),
                correct_option_label=question.get("CorrectOptionLabel"),
                correct_answer_text=question.get("CorrectAnswerText"),
                explanation_detail=question.get("ExplanationDetail"),
                option_analysis=question.get("OptionAnalysis"),
                vocabulary_notes=question.get("VocabularyNotes"),
                translation_vi=question.get("TranslationVi"),
                final_translation_vi=question.get("FinalTranslationVi"),
                user_selected_option_label=seed.user_selected_option_label,
                is_correct=seed.is_correct,
                bookmarked=question_id in bookmarked_ids,
                notes=notes_by_question.get(question_id, []),
                highlights=highlights_by_question.get(question_id, []),
                source_attempt_id=seed.source_attempt_id,
                source_type=seed.source_type,
                source_queue_id=seed.source_queue_id,
                status=seed.status or "active",
            )
        )
    return result


@router.get("/api/review/summary")
def get_review_summary_route(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if not user_id:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    return get_review_summary(db, user_id)


@router.get("/api/review/item/{review_item_id}")
def get_review_item_route(
    review_item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    item = get_review_item_detail(db, user_id, review_item_id)
    if item is None:
        return JSONResponse(status_code=404, content={"message": "Review item not found."})
    return item


@router.post("/api/review/item/{review_item_id}/mark-reviewed")
def mark_review_item_route(
    review_item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    item = mark_review_item_reviewed(db, user_id, review_item_id)
    if item is None:
        return JSONResponse(status_code=404, content={"message": "Review item not found."})
    return item


def _require_user(user_id: int | None) -> None:
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _normalize_filter(value: str) -> str:
    normalized = (value or "all").strip().lower()
    allowed = {"all", "wrong", "correct", "bookmarked", "notes", "highlights", "notebook"}
    return normalized if normalized in allowed else "all"


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
            self.source_type = other.source_type or self.source_type
            self.source_attempt_id = other.source_attempt_id or self.source_attempt_id
            self.source_queue_id = other.source_queue_id or self.source_queue_id
            self.user_selected_option_label = other.user_selected_option_label or self.user_selected_option_label
            self.is_correct = other.is_correct if other.is_correct is not None else self.is_correct
            self.status = other.status or self.status
            self.priority = other.priority


def _collect_review_seeds(db: Session, user_id: int, filter_name: str, limit: int) -> list[_ReviewSeed]:
    seeds: list[_ReviewSeed] = []

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
        mock_query = (
            select(MockTestAttemptAnswer, MockTestAttempt)
            .join(MockTestAttempt, MockTestAttempt.id == MockTestAttemptAnswer.mock_test_attempt_id)
            .where(MockTestAttempt.user_id == user_id)
            .order_by(func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc).desc())
            .limit(limit * 3)
        )
        for answer, attempt in db.execute(practice_query).all():
            if filter_name == "wrong" and answer.is_correct:
                continue
            if filter_name == "correct" and not answer.is_correct:
                continue
            seeds.append(
                _ReviewSeed(
                    raw_question_id=answer.question_id,
                    part=answer.part,
                    question_number=answer.question_number,
                    source_type="practice",
                    source_attempt_id=attempt.id,
                    user_selected_option_label=_label_from_index(answer.selected_answer_index),
                    is_correct=bool(answer.is_correct),
                    status="reviewed" if answer.is_correct else "pending",
                    priority=80,
                )
            )
        for answer, attempt in db.execute(mock_query).all():
            if filter_name == "wrong" and answer.is_correct:
                continue
            if filter_name == "correct" and not answer.is_correct:
                continue
            seeds.append(
                _ReviewSeed(
                    raw_question_id=answer.question_id,
                    part=answer.part,
                    question_number=answer.question_number,
                    source_type="mock-test",
                    source_attempt_id=attempt.id,
                    user_selected_option_label=_label_from_index(answer.selected_answer_index),
                    is_correct=bool(answer.is_correct),
                    status="reviewed" if answer.is_correct else "pending",
                    priority=75,
                )
            )

    if filter_name in {"all", "wrong"}:
        queue_rows = db.scalars(
            select(ReviewQueueItem)
            .where(ReviewQueueItem.user_id == user_id)
            .order_by(ReviewQueueItem.added_at_utc.desc())
            .limit(limit * 2)
        ).all()
        for item in queue_rows:
            seeds.append(
                _ReviewSeed(
                    raw_question_id=item.question_id,
                    part=item.part,
                    source_type=item.source_attempt_type or "review_queue",
                    source_attempt_id=item.source_attempt_id,
                    source_queue_id=item.id,
                    is_correct=False if item.status == "pending" else None,
                    status=item.status or "pending",
                    priority=60,
                )
            )

    if filter_name in {"all", "bookmarked", "notebook"}:
        for item in db.scalars(
            select(UserQuestionBookmark)
            .where(UserQuestionBookmark.user_id == user_id)
            .order_by(UserQuestionBookmark.created_at.desc())
            .limit(limit * 2)
        ).all():
            seeds.append(
                _ReviewSeed(
                    raw_question_id=item.question_id,
                    source_type="bookmark",
                    source_attempt_id=item.attempt_id,
                    status="bookmarked",
                    priority=90 if filter_name == "bookmarked" else 55,
                )
            )

    if filter_name in {"all", "notes", "notebook"}:
        for item in db.scalars(
            select(UserQuestionNote)
            .where(UserQuestionNote.user_id == user_id)
            .order_by(UserQuestionNote.updated_at.desc(), UserQuestionNote.id.desc())
            .limit(limit * 2)
        ).all():
            seeds.append(
                _ReviewSeed(
                    raw_question_id=item.question_id,
                    source_type="note",
                    source_attempt_id=item.attempt_id,
                    status="notebook",
                    priority=95 if filter_name == "notes" else 58,
                )
            )

    if filter_name in {"all", "highlights", "notebook"}:
        for item in db.scalars(
            select(UserQuestionHighlight)
            .where(UserQuestionHighlight.user_id == user_id)
            .order_by(UserQuestionHighlight.updated_at.desc(), UserQuestionHighlight.id.desc())
            .limit(limit * 2)
        ).all():
            seeds.append(
                _ReviewSeed(
                    raw_question_id=item.question_id,
                    source_type="highlight",
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

    direct_meta = _load_docx_question_meta(db, raw_ids)
    internal_rows = {
        row.id: row
        for row in db.scalars(select(ToeicQuestion).where(ToeicQuestion.id.in_(raw_ids))).all()
    }
    internal_docx_cache: dict[int, int | None] = {}
    resolved: dict[int, int] = {}

    for seed in seeds:
        raw_id = seed.raw_question_id
        direct = direct_meta.get(raw_id)
        if direct and _matches_seed_meta(seed, direct):
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


def _matches_seed_meta(seed: _ReviewSeed, meta: dict[str, Any]) -> bool:
    if seed.part and meta.get("PartNumber") and int(meta["PartNumber"]) != int(seed.part):
        return False
    if seed.question_number and meta.get("QuestionNumber") and int(meta["QuestionNumber"]) != int(seed.question_number):
        return False
    return True


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
                FROM STRING_SPLIT(:ids_csv, ',')
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


def _load_docx_questions(db: Session, question_ids: list[int]) -> dict[int, dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT Id, QuestionNumber, PartNumber, QuestionTextEn, PassageText,
                   CorrectOptionLabel, CorrectAnswerText, ExplanationDetail,
                   OptionAnalysis, VocabularyNotes, TranslationVi, FinalTranslationVi, RawBlock
            FROM dbo.ToeicDocxQuestions
            WHERE Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(:ids_csv, ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            """
        ),
        {"ids_csv": ",".join(str(value) for value in question_ids)},
    ).all()
    return {int(row._mapping["Id"]): dict(row._mapping) for row in rows}


def _load_docx_options(db: Session, question_ids: list[int]) -> dict[int, list[ReviewOptionResponse]]:
    rows = db.execute(
        text(
            """
            SELECT QuestionId, OptionLabel, OptionTextEn, IsCorrect, SortOrder
            FROM dbo.ToeicDocxOptions
            WHERE QuestionId IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(:ids_csv, ',')
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
