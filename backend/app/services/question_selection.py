from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.toeic import ToeicRunnerQuestionDto


@dataclass(frozen=True)
class CompletedQuestion:
    question_id: int
    last_answered_at_utc: datetime | None


def select_questions_for_attempt(
    db: Session,
    *,
    user_id: int | None,
    source_type: str,
    pool: Iterable[ToeicRunnerQuestionDto],
    question_count: int,
    part: int | None = None,
    skill: str | None = None,
    subskill: str | None = None,
    difficulty: str | None = None,
    exclude_completed: bool = True,
    seed_context: str = "",
) -> list[ToeicRunnerQuestionDto]:
    requested_count = max(0, int(question_count or 0))
    if requested_count <= 0:
        return []

    eligible = [clone_question(item) for item in pool]
    if not eligible:
        return []

    completed = (
        get_completed_question_history(db, user_id)
        if exclude_completed and user_id and user_id > 0
        else {}
    )
    completed_ids = set(completed)
    seed = _selection_seed(
        user_id=user_id,
        source_type=source_type,
        part=part,
        skill=skill,
        subskill=subskill,
        difficulty=difficulty,
        question_count=requested_count,
        seed_context=seed_context,
        completed_ids=completed_ids,
    )

    unseen = [item for item in eligible if _question_id(item) not in completed_ids]
    seen = [item for item in eligible if _question_id(item) in completed_ids]

    selected = _stable_shuffle(unseen, seed)[:requested_count]
    shortage = requested_count - len(selected)
    if shortage > 0:
        repeated = sorted(
            _stable_shuffle(seen, f"{seed}:repeat"),
            key=lambda item: (
                completed.get(_question_id(item), CompletedQuestion(_question_id(item), None)).last_answered_at_utc
                or datetime.min,
                _stable_hash(f"{seed}:repeat-order:{_question_id(item)}"),
            ),
        )[:shortage]
        for item in repeated:
            item.repeated = True
            item.repeatReason = "not_enough_unseen_questions"
        selected.extend(repeated)

    for index, question in enumerate(selected, start=1):
        question.questionNumber = index
    return selected


def get_completed_question_history(
    db: Session,
    user_id: int | None,
) -> dict[int, CompletedQuestion]:
    if not user_id or user_id <= 0:
        return {}

    rows = db.execute(
        text(
            """
            SELECT QuestionId, MAX(AnsweredAtUtc) AS LastAnsweredAtUtc
            FROM (
                SELECT paa.QuestionId,
                       COALESCE(pa.SubmittedAtUtc, pa.CreatedAtUtc) AS AnsweredAtUtc
                FROM dbo.PracticeAttemptAnswers paa
                INNER JOIN dbo.PracticeAttempts pa ON pa.Id = paa.PracticeAttemptId
                WHERE pa.UserId = :user_id
                  AND paa.QuestionId IS NOT NULL
                  AND pa.SubmittedAtUtc IS NOT NULL

                UNION ALL

                SELECT mta.QuestionId,
                       COALESCE(mt.SubmittedAtUtc, mt.CreatedAtUtc) AS AnsweredAtUtc
                FROM dbo.MockTestAttemptAnswers mta
                INNER JOIN dbo.MockTestAttempts mt ON mt.Id = mta.MockTestAttemptId
                WHERE mt.UserId = :user_id
                  AND mta.QuestionId IS NOT NULL
                  AND mt.SubmittedAtUtc IS NOT NULL
            ) completed
            GROUP BY QuestionId
            """
        ),
        {"user_id": user_id},
    ).mappings().all()

    result: dict[int, CompletedQuestion] = {}
    for row in rows:
        try:
            question_id = int(row.get("QuestionId") or 0)
        except (TypeError, ValueError):
            continue
        if question_id <= 0:
            continue
        result[question_id] = CompletedQuestion(
            question_id=question_id,
            last_answered_at_utc=row.get("LastAnsweredAtUtc"),
        )
    return result


def clone_question(question: ToeicRunnerQuestionDto) -> ToeicRunnerQuestionDto:
    return ToeicRunnerQuestionDto.model_validate(question.model_dump())


def _selection_seed(
    *,
    user_id: int | None,
    source_type: str,
    part: int | None,
    skill: str | None,
    subskill: str | None,
    difficulty: str | None,
    question_count: int,
    seed_context: str,
    completed_ids: set[int],
) -> str:
    completed_fingerprint = ",".join(str(value) for value in sorted(completed_ids))
    return "|".join(
        [
            str(user_id or 0),
            source_type.strip().lower(),
            str(part or ""),
            (skill or "").strip().lower(),
            (subskill or "").strip().lower(),
            (difficulty or "").strip().lower(),
            str(question_count),
            seed_context.strip().lower(),
            sha256(completed_fingerprint.encode("utf-8")).hexdigest(),
        ]
    )


def _stable_shuffle(
    questions: Iterable[ToeicRunnerQuestionDto],
    seed: str,
) -> list[ToeicRunnerQuestionDto]:
    return sorted(
        (clone_question(item) for item in questions),
        key=lambda item: (
            _stable_hash(f"{seed}:{_question_id(item)}:{item.part}:{item.test}:{item.questionNumber}"),
            item.part,
            item.id,
        ),
    )


def _stable_hash(value: str) -> int:
    return int.from_bytes(sha256(value.encode("utf-8")).digest()[:8], "little")


def _question_id(question: ToeicRunnerQuestionDto) -> int:
    return int(question.sourceQuestionId or question.docxQuestionId or question.dbId or question.questionId or question.id)
