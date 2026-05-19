from __future__ import annotations

import json
import logging
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.attempts import AttemptQuestionStartRequest, AttemptQuestionStartResponse
from app.schemas.toeic import ToeicRunnerQuestionDto
from app.services import toeic as toeic_service


logger = logging.getLogger(__name__)
_schema_ready = False

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "20260519_attempt_question_snapshots.sql"
)


def ensure_attempt_snapshot_schema(db: Session) -> None:
    global _schema_ready
    if _schema_ready:
        return
    script = MIGRATION_PATH.read_text(encoding="utf-8")
    for batch in _split_sql_batches(script):
        db.execute(text(batch))
        db.commit()
    _schema_ready = True


def start_attempt_snapshot(
    db: Session,
    user_id: int,
    request: AttemptQuestionStartRequest,
) -> AttemptQuestionStartResponse:
    ensure_attempt_snapshot_schema(db)
    source_type = _normalize_source_type(request.sourceType)
    source_key = _source_key(request, source_type)
    existing_id = _find_open_session(db, user_id, source_type, source_key)
    if existing_id:
        resumed = resume_attempt_snapshot(db, user_id, existing_id)
        if resumed is not None:
            return resumed

    questions = _select_questions(db, user_id, source_type, request)
    attempt_id = create_attempt_snapshot(
        db,
        user_id=user_id,
        source_type=source_type,
        source_key=source_key,
        questions=questions,
    )
    return _response_for_questions(attempt_id, source_type, questions)


def create_attempt_snapshot_for_questions(
    db: Session,
    *,
    user_id: int,
    source_type: str,
    source_key: str,
    questions: Iterable[ToeicRunnerQuestionDto],
) -> AttemptQuestionStartResponse:
    ensure_attempt_snapshot_schema(db)
    normalized_source = _normalize_source_type(source_type)
    question_list = list(questions)
    existing_id = _find_open_session(db, user_id, normalized_source, source_key)
    if existing_id:
        resumed = resume_attempt_snapshot(db, user_id, existing_id)
        if resumed is not None:
            return resumed
    attempt_id = create_attempt_snapshot(
        db,
        user_id=user_id,
        source_type=normalized_source,
        source_key=source_key,
        questions=question_list,
    )
    return _response_for_questions(attempt_id, normalized_source, question_list)


def create_attempt_snapshot(
    db: Session,
    *,
    user_id: int,
    source_type: str,
    source_key: str,
    questions: Iterable[ToeicRunnerQuestionDto],
) -> int:
    normalized_source = _normalize_source_type(source_type)
    attempt_id = int(
        db.execute(
            text(
                """
                INSERT INTO dbo.AttemptQuestionSessions (UserId, SourceType, SourceKey, Status, CreatedAtUtc)
                OUTPUT INSERTED.Id
                VALUES (:user_id, :source_type, :source_key, N'started', SYSUTCDATETIME())
                """
            ),
            {
                "user_id": user_id,
                "source_type": normalized_source,
                "source_key": source_key,
            },
        ).scalar_one()
    )
    for index, question in enumerate(questions, start=1):
        question_id = _question_id(question)
        if question_id <= 0:
            continue
        db.execute(
            text(
                """
                INSERT INTO dbo.AttemptQuestionItems
                    (AttemptId, SourceType, UserId, QuestionId, OrderIndex, Repeated, RepeatReason, CreatedAtUtc)
                VALUES
                    (:attempt_id, :source_type, :user_id, :question_id, :order_index, :repeated, :repeat_reason, SYSUTCDATETIME())
                """
            ),
            {
                "attempt_id": attempt_id,
                "source_type": normalized_source,
                "user_id": user_id,
                "question_id": question_id,
                "order_index": index,
                "repeated": bool(question.repeated),
                "repeat_reason": question.repeatReason,
            },
        )
    db.commit()
    return attempt_id


def resume_attempt_snapshot(
    db: Session,
    user_id: int,
    attempt_id: int,
) -> AttemptQuestionStartResponse | None:
    ensure_attempt_snapshot_schema(db)
    session = db.execute(
        text(
            """
            SELECT Id, SourceType
            FROM dbo.AttemptQuestionSessions
            WHERE Id = :attempt_id AND UserId = :user_id
            """
        ),
        {"attempt_id": attempt_id, "user_id": user_id},
    ).mappings().first()
    if session is None:
        return None

    item_rows = db.execute(
        text(
            """
            SELECT QuestionId, OrderIndex, Repeated, RepeatReason
            FROM dbo.AttemptQuestionItems
            WHERE AttemptId = :attempt_id AND UserId = :user_id
            ORDER BY OrderIndex ASC
            """
        ),
        {"attempt_id": attempt_id, "user_id": user_id},
    ).mappings().all()
    question_ids = [int(row["QuestionId"]) for row in item_rows]
    questions = toeic_service.get_runner_questions_by_ids(db, question_ids)
    metadata = {int(row["QuestionId"]): row for row in item_rows}
    for index, question in enumerate(questions, start=1):
        meta = metadata.get(_question_id(question))
        question.attemptId = attempt_id
        question.questionNumber = index
        if meta is not None:
            question.repeated = bool(meta.get("Repeated"))
            question.repeatReason = meta.get("RepeatReason")
    return _response_for_questions(attempt_id, str(session["SourceType"]), questions)


def mark_attempt_snapshot_submitted(
    db: Session,
    *,
    user_id: int,
    snapshot_attempt_id: int | None,
    submitted_attempt_id: int,
) -> None:
    if not snapshot_attempt_id or snapshot_attempt_id <= 0:
        return
    ensure_attempt_snapshot_schema(db)
    db.execute(
        text(
            """
            UPDATE dbo.AttemptQuestionSessions
            SET Status = N'submitted',
                SubmittedAttemptId = :submitted_attempt_id,
                SubmittedAtUtc = SYSUTCDATETIME(),
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE Id = :snapshot_attempt_id
              AND UserId = :user_id
              AND Status = N'started'
            """
        ),
        {
            "snapshot_attempt_id": snapshot_attempt_id,
            "submitted_attempt_id": submitted_attempt_id,
            "user_id": user_id,
        },
    )
    db.commit()


def _select_questions(
    db: Session,
    user_id: int,
    source_type: str,
    request: AttemptQuestionStartRequest,
) -> list[ToeicRunnerQuestionDto]:
    count = max(1, min(int(request.count or 10), 200))
    parts = _selected_parts(request)
    if source_type == "mini_test":
        return _select_mini_questions(db, user_id, request, parts, count)
    if source_type == "weekly_check":
        from app.services.weekly_check import get_current_weekly_check

        return get_current_weekly_check(db, user_id).questions
    if source_type == "roadmap":
        if not request.roadmapWeekId or not request.roadmapSetId:
            return []
        from app.services.roadmap import get_set_questions

        payload = get_set_questions(db, request.roadmapWeekId, request.roadmapSetId, user_id)
        return payload.questions if payload else []
    return _select_practice_questions(db, user_id, request, parts, count)


def _select_practice_questions(
    db: Session,
    user_id: int,
    request: AttemptQuestionStartRequest,
    parts: list[int],
    count: int,
) -> list[ToeicRunnerQuestionDto]:
    if len(parts) <= 1:
        return toeic_service.get_part_runner_questions(
            db,
            parts[0],
            count,
            request.difficulty,
            None,
            user_id,
        )

    quotas = _quotas_by_part(parts, count)
    selected: list[ToeicRunnerQuestionDto] = []
    for part in parts:
        quota = quotas.get(part, 0)
        if quota <= 0:
            continue
        selected.extend(
            toeic_service.get_part_runner_questions(
                db,
                part,
                quota,
                request.difficulty,
                None,
                user_id,
            )
        )
    return _final_order(selected, user_id, "practice", request)


def _select_mini_questions(
    db: Session,
    user_id: int,
    request: AttemptQuestionStartRequest,
    parts: list[int],
    count: int,
) -> list[ToeicRunnerQuestionDto]:
    if len(parts) <= 1:
        return toeic_service.get_minitest_runner_questions(
            db,
            request.test or 1,
            parts,
            count,
            user_id,
        )
    quotas = _quotas_by_part(parts, count)
    selected: list[ToeicRunnerQuestionDto] = []
    for part in parts:
        quota = quotas.get(part, 0)
        if quota <= 0:
            continue
        selected.extend(
            toeic_service.get_minitest_runner_questions(
                db,
                request.test or 1,
                [part],
                quota,
                user_id,
            )
        )
    return _final_order(selected, user_id, "mini_test", request)


def _response_for_questions(
    attempt_id: int,
    source_type: str,
    questions: list[ToeicRunnerQuestionDto],
) -> AttemptQuestionStartResponse:
    shortage_parts = sorted({question.part for question in questions if question.repeated})
    for index, question in enumerate(questions, start=1):
        question.attemptId = attempt_id
        question.questionNumber = index
    repeated = bool(shortage_parts)
    return AttemptQuestionStartResponse(
        attemptId=attempt_id,
        sourceType=_normalize_source_type(source_type),
        questions=questions,
        shortage=repeated,
        shortageParts=shortage_parts,
        repeated=repeated,
        repeatReason="not_enough_unseen_questions" if repeated else None,
        message=(
            "Not enough new questions available for the selected part."
            if repeated
            else None
        ),
    )


def _find_open_session(
    db: Session,
    user_id: int,
    source_type: str,
    source_key: str,
) -> int | None:
    row = db.execute(
        text(
            """
            SELECT TOP (1) Id
            FROM dbo.AttemptQuestionSessions
            WHERE UserId = :user_id
              AND SourceType = :source_type
              AND SourceKey = :source_key
              AND Status = N'started'
            ORDER BY CreatedAtUtc DESC, Id DESC
            """
        ),
        {
            "user_id": user_id,
            "source_type": source_type,
            "source_key": source_key,
        },
    ).mappings().first()
    return int(row["Id"]) if row else None


def _source_key(request: AttemptQuestionStartRequest, source_type: str) -> str:
    payload = {
        "sourceType": source_type,
        "parts": _selected_parts(request),
        "skill": (request.skill or "").strip().lower(),
        "subskill": (request.subskill or "").strip().lower(),
        "difficulty": (request.difficulty or "mixed").strip().lower(),
        "count": max(1, min(int(request.count or 10), 200)),
        "test": request.test or 1,
        "roadmapWeekId": request.roadmapWeekId,
        "roadmapSetId": request.roadmapSetId,
        "seedContext": request.seedContext or "",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _selected_parts(request: AttemptQuestionStartRequest) -> list[int]:
    values = list(request.parts or [])
    if request.part is not None:
        values.append(request.part)
    selected = sorted({int(part) for part in values if 1 <= int(part) <= 7})
    return selected or [1]


def _quotas_by_part(parts: list[int], count: int) -> dict[int, int]:
    normalized = sorted({part for part in parts if 1 <= part <= 7})
    if not normalized:
        return {}
    base = count // len(normalized)
    remainder = count % len(normalized)
    return {
        part: base + (1 if index < remainder else 0)
        for index, part in enumerate(normalized)
    }


def _final_order(
    questions: list[ToeicRunnerQuestionDto],
    user_id: int,
    source_type: str,
    request: AttemptQuestionStartRequest,
) -> list[ToeicRunnerQuestionDto]:
    seed = _source_key(request, source_type)
    ordered = sorted(
        questions,
        key=lambda item: (
            int.from_bytes(
                sha256(f"{user_id}:{seed}:{_question_id(item)}".encode("utf-8")).digest()[:8],
                "little",
            ),
            item.part,
            _question_id(item),
        ),
    )
    for index, question in enumerate(ordered, start=1):
        question.questionNumber = index
    return ordered


def _normalize_source_type(value: str | None) -> str:
    normalized = (value or "practice").strip().lower().replace("-", "_")
    if normalized in {"mini", "minitest"}:
        return "mini_test"
    if normalized in {"weekly", "weeklycheck"}:
        return "weekly_check"
    if normalized in {"roadmap_set", "roadmap_practice"}:
        return "roadmap"
    return normalized or "practice"


def _question_id(question: ToeicRunnerQuestionDto) -> int:
    return int(question.sourceQuestionId or question.docxQuestionId or question.dbId or question.questionId or question.id)


def _split_sql_batches(script: str) -> list[str]:
    batches: list[str] = []
    current: list[str] = []
    for line in script.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(current).strip()
            if batch:
                batches.append(batch)
            current = []
            continue
        current.append(line)
    batch = "\n".join(current).strip()
    if batch:
        batches.append(batch)
    return batches
