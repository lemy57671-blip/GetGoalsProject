from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models import (
    MockTestAttempt,
    MockTestAttemptAnswer,
    PracticeAttempt,
    PracticeAttemptAnswer,
    ReviewQueueItem,
    User,
    UserSkillProfile,
)
from app.schemas.attempts import (
    AttemptAssetDto,
    AttemptPartBreakdownDto,
    AttemptResultOptionDto,
    AttemptResultPassageDto,
    AttemptResultDto,
    AttemptResultQuestionDto,
    AttemptSkillBreakdownDto,
    AttemptWeakAreaDto,
    SaveAttemptResponse,
    SaveDiagnosticAttemptRequest,
    SaveMockTestAttemptAnswerRequest,
    SaveMockTestAttemptRequest,
    SavePracticeAttemptAnswerRequest,
    SavePracticeAttemptRequest,
)
from app.schemas.toeic import ToeicRunnerQuestionDto
from app.services.skill_analytics import infer_part, normalize_skill_code
from app.services.toeic import build_question_lookup_key, get_question_lookup_by_ids
from app.services.irt_scoring import score_diagnostic_with_rasch
from app.services.weighted_score import compute_weight_score_fields
from app.services.review_schema import ensure_review_schema
from app.services.attempt_snapshots import mark_attempt_snapshot_submitted


logger = logging.getLogger(__name__)


RUNTIME_REVIEW_SOURCES = {"practice", "fulltest", "minitest", "weeklycheck"}


def _normalize_mock_attempt_type(
    attempt_type: str | None,
    title: str | None,
    total_questions: int | None = None,
) -> str:
    raw = (attempt_type or "").strip().lower().replace("_", "-")
    title_lower = (title or "").strip().lower()
    if raw in {"mini", "mini-test", "minitest"} or "mini" in title_lower:
        return "minitest"
    if raw in {"full", "full-test", "fulltest", "mock", "mock-test"}:
        return "fulltest"
    if "full" in title_lower or "mock" in title_lower:
        return "fulltest"
    if total_questions and total_questions < 120:
        return "minitest"
    return "fulltest"


def _normalize_review_source(value: str | None) -> str:
    normalized = (value or "").strip().lower().replace("-", "_")
    if normalized in {"practice", "bai_tap"}:
        return "practice"
    if normalized in {"full", "full_test", "fulltest", "mock", "mock_test"}:
        return "fulltest"
    if normalized in {"mini", "mini_test", "minitest"}:
        return "minitest"
    if normalized in {"weekly", "weekly_check", "weeklycheck"}:
        return "weeklycheck"
    if normalized in {"diagnostic", "placement", "placement_test"}:
        return "diagnostic"
    return "practice"


def _label_from_index(index: int | None) -> str | None:
    if index is None or index < 0 or index > 25:
        return None
    return chr(ord("A") + index)


def _review_reason_for_answer(selected_answer_index: int | None, is_correct: bool) -> str | None:
    if is_correct:
        return None
    return "skipped" if selected_answer_index is None else "wrong"


def _answer_value(answer, snake_name: str, camel_name: str | None = None, default=None):
    if isinstance(answer, dict):
        if snake_name in answer:
            return answer[snake_name]
        if camel_name and camel_name in answer:
            return answer[camel_name]
        return default
    if hasattr(answer, snake_name):
        return getattr(answer, snake_name)
    if camel_name and hasattr(answer, camel_name):
        return getattr(answer, camel_name)
    return default


def _source_question_id(source_question: ToeicRunnerQuestionDto | None) -> int | None:
    if source_question is None:
        return None
    for value in (
        source_question.sourceQuestionId,
        source_question.docxQuestionId,
        source_question.dbId,
        source_question.questionId,
        source_question.id,
    ):
        if value:
            return int(value)
    return None


def _compute_attempt_weight_score_fields(
    answers,
    question_lookup: dict[str, ToeicRunnerQuestionDto] | None = None,
) -> dict[str, int | float]:
    weight_items: list[dict] = []

    for answer in answers or []:
        question_id = _answer_value(answer, "question_id", "questionId")
        part = _answer_value(answer, "part", "part")
        source_question = None
        if question_lookup is not None and question_id is not None:
            lookup_answer = type(
                "_WeightLookupAnswer",
                (),
                {"question_id": question_id, "part": part or 0},
            )()
            source_question = _find_source_question(lookup_answer, question_lookup)

        resolved_item_id = _source_question_id(source_question) or question_id
        weight_items.append(
            {
                "item_id": resolved_item_id,
                "question_id": question_id,
                "is_correct": _answer_value(answer, "is_correct", "isCorrect", False),
                "selected_answer_index": _answer_value(
                    answer,
                    "selected_answer_index",
                    "selectedAnswerIndex",
                ),
                "difficulty": _answer_value(
                    answer,
                    "difficulty",
                    "difficulty",
                    source_question.difficulty if source_question else None,
                ),
                "itemDifficulty": _answer_value(answer, "itemDifficulty", "itemDifficulty"),
            }
        )

    return compute_weight_score_fields(weight_items)


def save_practice_attempt(db: Session, user_id: int, request: SavePracticeAttemptRequest) -> SaveAttemptResponse:
    ensure_review_schema(db)
    source_attempt_type = (
        _normalize_review_source(request.source)
        if request.source
        else "weeklycheck" if (request.mode or "").strip().lower().replace("_", "-") == "weekly-check" else "practice"
    )
    attempt = PracticeAttempt(
        user_id=user_id,
        title=request.title,
        subtitle=request.subtitle,
        mode=request.mode,
        parts=request.parts,
        difficulty=request.difficulty,
        total_questions=request.totalQuestions,
        answered_count=request.answeredCount,
        correct_count=request.correctCount,
        accuracy_pct=request.accuracyPct,
        score=request.score,
        time_spent_seconds=request.timeSpentSeconds,
        started_at_utc=request.startedAtUtc or datetime.utcnow(),
        submitted_at_utc=request.submittedAtUtc or datetime.utcnow(),
        created_at_utc=datetime.utcnow(),
        answers=[
            PracticeAttemptAnswer(
                question_id=item.questionId,
                question_number=item.questionNumber,
                part=item.part,
                skill=item.skill,
                selected_answer_index=item.selectedAnswerIndex,
                correct_answer_index=item.correctAnswerIndex,
                is_correct=item.isCorrect,
                is_flagged=item.isFlagged,
                explanation=item.explanation,
                created_at_utc=datetime.utcnow(),
            )
            for item in request.answers
        ],
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    mark_attempt_snapshot_submitted(
        db,
        user_id=user_id,
        snapshot_attempt_id=request.attemptId,
        submitted_attempt_id=attempt.id,
    )

    incorrect_answers = [item for item in attempt.answers if not item.is_correct]
    review_queued_count = _enqueue_review_items(
        db,
        user_id,
        [
            _ReviewSeed(
                questionId=item.question_id,
                questionNumber=item.question_number,
                part=item.part,
                skill=item.skill,
                sourceAttemptType=source_attempt_type,
                sourceAttemptId=attempt.id,
                selectedOptionKey=_label_from_index(item.selected_answer_index),
                correctOptionKey=_label_from_index(item.correct_answer_index),
                isCorrect=bool(item.is_correct),
                isSkipped=item.selected_answer_index is None,
                reviewReason=_review_reason_for_answer(item.selected_answer_index, item.is_correct) or "wrong",
                lastAnsweredAtUtc=attempt.submitted_at_utc or attempt.created_at_utc,
                note=item.explanation,
            )
            for item in incorrect_answers
        ],
    )

    stat_result = _update_stats(
        db,
        user_id,
        [_StatSeed(part=item.part, skill=item.skill, isCorrect=item.is_correct) for item in attempt.answers],
    )
    _sync_user_profile(db, user_id)
    logger.info(
        "Practice submit persisted user_id=%s source=%s attempt_id=%s answers=%s review_queued=%s wrong=%s skipped=%s skill_profiles_upserted=%s part_stats_upserted=%s",
        user_id,
        source_attempt_type,
        attempt.id,
        len(attempt.answers),
        review_queued_count,
        sum(1 for item in incorrect_answers if item.selected_answer_index is not None),
        sum(1 for item in incorrect_answers if item.selected_answer_index is None),
        stat_result.skillStatsUpdated,
        stat_result.partStatsUpdated,
    )

    try:
        result = get_practice_attempt_result(db, user_id, attempt.id)
    except Exception:
        logger.exception("Could not hydrate practice attempt result after submit; returning fallback result.")
        result = None

    return SaveAttemptResponse(
        attemptId=attempt.id,
        reviewQueuedCount=review_queued_count,
        skillStatsUpdated=stat_result.skillStatsUpdated,
        partStatsUpdated=stat_result.partStatsUpdated,
        result=result or _build_practice_result(attempt.id, request),
    )


def save_mock_test_attempt(db: Session, user_id: int, request: SaveMockTestAttemptRequest) -> SaveAttemptResponse:
    ensure_review_schema(db)
    source_attempt_type = (
        _normalize_review_source(request.source)
        if request.source
        else _normalize_mock_attempt_type(request.attemptType, request.title, request.totalQuestions)
    )
    attempt = MockTestAttempt(
        user_id=user_id,
        title=request.title,
        total_questions=request.totalQuestions,
        answered_count=request.answeredCount,
        correct_count=request.correctCount,
        listening_score=request.listeningScore,
        reading_score=request.readingScore,
        total_score=request.totalScore,
        accuracy_pct=request.accuracyPct,
        time_spent_seconds=request.timeSpentSeconds,
        status=request.status,
        started_at_utc=request.startedAtUtc or datetime.utcnow(),
        submitted_at_utc=request.submittedAtUtc or datetime.utcnow(),
        created_at_utc=datetime.utcnow(),
        answers=[
            MockTestAttemptAnswer(
                question_id=item.questionId,
                question_number=item.questionNumber,
                part=item.part,
                skill=item.skill,
                selected_answer_index=item.selectedAnswerIndex,
                correct_answer_index=item.correctAnswerIndex,
                is_correct=item.isCorrect,
                is_flagged=item.isFlagged,
                explanation=item.explanation,
            )
            for item in request.answers
        ],
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    mark_attempt_snapshot_submitted(
        db,
        user_id=user_id,
        snapshot_attempt_id=request.attemptId,
        submitted_attempt_id=attempt.id,
    )

    review_queued_count = _enqueue_review_items(
        db,
        user_id,
        [
            _ReviewSeed(
                questionId=item.question_id,
                questionNumber=item.question_number,
                part=item.part,
                skill=item.skill,
                sourceAttemptType=source_attempt_type,
                sourceAttemptId=attempt.id,
                selectedOptionKey=_label_from_index(item.selected_answer_index),
                correctOptionKey=_label_from_index(item.correct_answer_index),
                isCorrect=bool(item.is_correct),
                isSkipped=item.selected_answer_index is None,
                reviewReason=_review_reason_for_answer(item.selected_answer_index, item.is_correct) or "wrong",
                lastAnsweredAtUtc=attempt.submitted_at_utc or attempt.created_at_utc,
                note=item.explanation,
            )
            for item in attempt.answers
            if not item.is_correct
        ],
    )

    stat_result = _update_stats(
        db,
        user_id,
        [_StatSeed(part=item.part, skill=item.skill, isCorrect=item.is_correct) for item in attempt.answers],
    )
    _sync_user_profile(db, user_id)
    incorrect_answers = [item for item in attempt.answers if not item.is_correct]
    logger.info(
        "Mock submit persisted user_id=%s source=%s attempt_id=%s answers=%s review_queued=%s wrong=%s skipped=%s skill_profiles_upserted=%s part_stats_upserted=%s",
        user_id,
        source_attempt_type,
        attempt.id,
        len(attempt.answers),
        review_queued_count,
        sum(1 for item in incorrect_answers if item.selected_answer_index is not None),
        sum(1 for item in incorrect_answers if item.selected_answer_index is None),
        stat_result.skillStatsUpdated,
        stat_result.partStatsUpdated,
    )

    try:
        result = get_mock_test_attempt_result(db, user_id, attempt.id)
    except Exception:
        logger.exception("Could not hydrate mock-test attempt result after submit; returning fallback result.")
        result = None

    return SaveAttemptResponse(
        attemptId=attempt.id,
        reviewQueuedCount=review_queued_count,
        skillStatsUpdated=stat_result.skillStatsUpdated,
        partStatsUpdated=stat_result.partStatsUpdated,
        result=result or _build_mock_test_result(attempt.id, request),
    )


def save_diagnostic_attempt(db: Session, user_id: int, request: SaveDiagnosticAttemptRequest) -> SaveAttemptResponse:
    """
    LÆ°u káº¿t quáº£ bÃ i test Ä‘áº§u vÃ o vÃ o 2 báº£ng:
    - dbo.DiagnosticAttempts
    - dbo.DiagnosticAttemptAnswers

    Äá»“ng thá»i:
    - TÃ­nh Rasch theta tá»« dá»¯ liá»‡u Ä‘Ãºng/sai.
    - LÆ°u Theta vÃ o DiagnosticAttempts.Theta.
    - LÆ°u EstimatedScore theo hybrid Rasch/weighted vÃ o DiagnosticAttempts.EstimatedScore.
    - LÆ°u ScoreRule lÃ  Ä‘iá»ƒm rule-based cÅ© theo accuracy Ä‘á»ƒ Ä‘á»‘i chiáº¿u.
    - Giá»¯ logic cÅ©: update profile, review queue, skill stats, part stats.
    """

    now = datetime.utcnow()
    user = db.get(User, user_id)
    answers = list(request.answers or [])
    answered_answers = [
        item
        for item in answers
        if item.selectedAnswerIndex is not None and item.selectedAnswerIndex >= 0
    ]

    question_meta_by_id: dict[int, dict] = {}

    if answered_answers:
        question_ids_csv = ",".join(
            str(item.questionId)
            for item in answered_answers
            if item.questionId is not None
        )

        if question_ids_csv:
            rows = db.execute(
                text(
                    """
                    SELECT
                        Id,
                        LegacyQuestionId,
                        Part,
                        SkillCode,
                        SubskillCode
                    FROM dbo.ToeicQuestions
                    WHERE Id IN (
                        SELECT TRY_CAST(value AS INT)
                        FROM STRING_SPLIT(:question_ids_csv, ',')
                    )
                    """
                ),
                {"question_ids_csv": question_ids_csv},
            ).mappings().all()

            question_meta_by_id = {
                int(row["Id"]): {
                    "legacy_id": row["LegacyQuestionId"],
                    "part": row["Part"],
                    "skill": row["SkillCode"],
                    "subskill": row["SubskillCode"],
                }
                for row in rows
            }

    answered_count = len(answered_answers)

    total_questions = request.totalQuestions or len(answers)

    correct_count = request.correctCount
    if correct_count is None:
        correct_count = sum(1 for item in answered_answers if item.isCorrect)

    accuracy_pct = request.accuracyPct
    if accuracy_pct is None:
        accuracy_pct = round(correct_count * 100 / answered_count, 2) if answered_count else 0

    score_rule = int(round(5 + (float(accuracy_pct) / 100.0) * 985))
    score_rule = max(5, min(score_rule, 990))

    rasch_items: list[dict] = []
    weight_items: list[dict] = []

    for item in answered_answers:
        meta = question_meta_by_id.get(item.questionId, {})
        legacy_id = meta.get("legacy_id")
        weight_items.append(
            {
                "item_id": int(legacy_id or item.questionId),
                "question_id": item.questionId,
                "is_correct": bool(item.isCorrect),
                "selected_answer_index": item.selectedAnswerIndex,
            }
        )

        if legacy_id is not None:
            rasch_items.append(
                {
                    "item_id": int(legacy_id),
                    "is_correct": bool(item.isCorrect),
                }
            )

    rasch_result = score_diagnostic_with_rasch(rasch_items)
    weight_score_fields = compute_weight_score_fields(weight_items)

    theta = rasch_result.get("theta")
    rasch_score = rasch_result.get("rasch_score")
    weighted_score = rasch_result.get("weighted_score")
    if weighted_score is not None:
        weighted_score = int(weighted_score)
        weight_score_fields = {
            **weight_score_fields,
            "weighted_score": weighted_score,
            "weight_score": weighted_score,
        }
    estimated_score = int(rasch_result.get("estimated_score") or request.score or score_rule)

    level_name = rasch_result.get("level_name") or request.levelName
    level_range = rasch_result.get("level_range") or request.levelRange
    true_toeic = request.currentScore if request.currentScore is not None and 0 <= request.currentScore <= 990 else None

    if user is not None:
        user.current_score = true_toeic if true_toeic is not None else estimated_score

        if request.targetScore is not None:
            user.target_score = request.targetScore

        if request.minutesPerDay is not None:
            user.study_minutes_per_day = request.minutesPerDay

        if request.weeks is not None and request.weeks > 0:
            user.exam_date = (now + timedelta(weeks=min(request.weeks, 104))).date()

        db.commit()

    attempt_code = f"diagnostic-{user_id}-{now.strftime('%Y%m%d%H%M%S')}"

    user_email = getattr(user, "email", None) if user is not None else None

    if user is not None:
        user_name = (
            getattr(user, "full_name", None)
            or getattr(user, "name", None)
            or getattr(user, "username", None)
        )
    else:
        user_name = None

    answers_json = json.dumps(
        [_diagnostic_answer_to_dict(item) for item in answered_answers],
        ensure_ascii=False,
        default=str,
    )

    attempt_id = db.execute(
        text(
            """
            INSERT INTO dbo.DiagnosticAttempts
            (
                UserId,
                AttemptId,
                Email,
                Name,
                TargetScore,
                Weeks,
                MinutesPerDay,
                DurationSec,
                CorrectCount,
                AnsweredCount,
                TotalQuestions,
                AccuracyPct,
                ScoreRule,
                Theta,
                EstimatedScore,
                TrueToeic,
                LevelName,
                LevelRange,
                AnswersJson,
                WeakSubskillsJson,
                TopErrorsJson,
                CreatedAtUtc,
                SubmittedAtUtc
            )
            OUTPUT INSERTED.Id
            VALUES
            (
                :user_id,
                :attempt_code,
                :email,
                :name,
                :target_score,
                :weeks,
                :minutes_per_day,
                :duration_sec,
                :correct_count,
                :answered_count,
                :total_questions,
                :accuracy_pct,
                :score_rule,
                :theta,
                :estimated_score,
                :true_toeic,
                :level_name,
                :level_range,
                :answers_json,
                :weak_subskills_json,
                :top_errors_json,
                SYSUTCDATETIME(),
                SYSUTCDATETIME()
            )
            """
        ),
        {
            "user_id": user_id,
            "attempt_code": attempt_code,
            "email": user_email,
            "name": user_name,
            "target_score": request.targetScore,
            "weeks": request.weeks,
            "minutes_per_day": request.minutesPerDay,
            "duration_sec": getattr(request, "durationSec", None)
            or getattr(request, "timeSpentSeconds", None),
            "correct_count": correct_count,
            "answered_count": answered_count,
            "total_questions": total_questions,
            "accuracy_pct": accuracy_pct,
            "score_rule": score_rule,
            "theta": theta,
            "estimated_score": estimated_score,
            "true_toeic": true_toeic,
            "level_name": level_name,
            "level_range": level_range,
            "answers_json": answers_json,
            "weak_subskills_json": request.weakSubskillsJson,
            "top_errors_json": request.topErrorsJson,
        },
    ).scalar_one()

    for item in answered_answers:
        meta = question_meta_by_id.get(item.questionId, {})

        part = item.part or meta.get("part") or infer_part(item.skill, item.subskill)
        skill_raw = item.skill or meta.get("skill")
        subskill = item.subskill or meta.get("subskill") or skill_raw
        skill = normalize_skill_code(skill_raw, subskill)

        db.execute(
            text(
                """
                INSERT INTO dbo.DiagnosticAttemptAnswers
                (
                    DiagnosticAttemptId,
                    QuestionId,
                    QuestionNumber,
                    Part,
                    Skill,
                    Subskill,
                    SelectedAnswerIndex,
                    CorrectAnswerIndex,
                    IsCorrect,
                    CreatedAtUtc
                )
                VALUES
                (
                    :diagnostic_attempt_id,
                    :question_id,
                    :question_number,
                    :part,
                    :skill,
                    :subskill,
                    :selected_answer_index,
                    :correct_answer_index,
                    :is_correct,
                    SYSUTCDATETIME()
                )
                """
            ),
            {
                "diagnostic_attempt_id": attempt_id,
                "question_id": item.questionId,
                "question_number": item.questionNumber,
                "part": part,
                "skill": skill,
                "subskill": subskill,
                "selected_answer_index": item.selectedAnswerIndex,
                "correct_answer_index": item.correctAnswerIndex,
                "is_correct": 1 if item.isCorrect else 0,
            },
        )

    db.commit()

    review_queued_count = _enqueue_review_items(
        db,
        user_id,
        [
            _ReviewSeed(
                questionId=item.questionId,
                questionNumber=item.questionNumber,
                part=(
                    item.part
                    or question_meta_by_id.get(item.questionId, {}).get("part")
                    or infer_part(item.skill, item.subskill)
                ),
                skill=(
                    item.skill
                    or question_meta_by_id.get(item.questionId, {}).get("skill")
                    or item.subskill
                ),
                sourceAttemptType="diagnostic",
                sourceAttemptId=attempt_id,
                selectedOptionKey=_label_from_index(item.selectedAnswerIndex),
                correctOptionKey=_label_from_index(item.correctAnswerIndex),
                isCorrect=bool(item.isCorrect),
                isSkipped=item.selectedAnswerIndex is None,
                reviewReason=_review_reason_for_answer(item.selectedAnswerIndex, item.isCorrect) or "wrong",
                lastAnsweredAtUtc=now,
                note=(
                    item.subskill
                    or question_meta_by_id.get(item.questionId, {}).get("subskill")
                ),
            )
            for item in answered_answers
            if not item.isCorrect
        ],
    )

    stat_result = _update_stats(
        db,
        user_id,
        [
            _StatSeed(
                part=(
                    item.part
                    or question_meta_by_id.get(item.questionId, {}).get("part")
                    or infer_part(item.skill, item.subskill)
                ),
                skill=normalize_skill_code(
                    item.skill or question_meta_by_id.get(item.questionId, {}).get("skill"),
                    item.subskill or question_meta_by_id.get(item.questionId, {}).get("subskill"),
                ),
                isCorrect=item.isCorrect,
            )
            for item in answered_answers
        ],
    )

    _sync_user_profile(db, user_id, request.weakSubskillsJson)

    return SaveAttemptResponse(
        attemptId=attempt_id,
        reviewQueuedCount=review_queued_count,
        skillStatsUpdated=stat_result.skillStatsUpdated,
        partStatsUpdated=stat_result.partStatsUpdated,
        result=AttemptResultDto(
            attemptId=attempt_id,
            attemptType="diagnostic",
            title="Diagnostic Result",
            totalQuestions=total_questions,
            correctCount=correct_count,
            wrongCount=max(answered_count - correct_count, 0),
            unansweredCount=max(total_questions - answered_count, 0),
            accuracyPct=float(accuracy_pct or 0),
            rasch_score=int(rasch_score) if rasch_score is not None else None,
            theta=float(theta) if theta is not None else None,
            model_used=str(rasch_result.get("model_used") or ""),
            **weight_score_fields,
            startedAt=None,
            submittedAt=now,
            durationSeconds=int(
                getattr(request, "durationSec", None)
                or getattr(request, "timeSpentSeconds", None)
                or 0
            ),
            scaledScore=estimated_score,
            skillBreakdown=[],
            partBreakdown=[],
            weakAreas=[],
            questions=[],
        ),
    )


def get_practice_attempt_result(db: Session, user_id: int, attempt_id: int) -> AttemptResultDto | None:
    attempt = db.scalar(
        select(PracticeAttempt)
        .options(selectinload(PracticeAttempt.answers))
        .where(PracticeAttempt.id == attempt_id, PracticeAttempt.user_id == user_id)
    )
    if attempt is None:
        return None

    answers = sorted(attempt.answers, key=lambda item: (item.question_number or 0, item.question_id))
    question_ids = [item.question_id for item in answers]
    question_lookup = get_question_lookup_by_ids(db, question_ids)
    explanation_lookup = _load_runtime_explanations(db, question_ids)
    questions = [_build_saved_result_question(item, question_lookup, explanation_lookup) for item in answers]
    weight_score_fields = _compute_attempt_weight_score_fields(answers, question_lookup)
    total_questions = attempt.total_questions or len(questions)
    unanswered_count = max(total_questions - attempt.answered_count, 0)
    wrong_count = max(attempt.answered_count - attempt.correct_count, 0)
    mode = (attempt.mode or "").strip().lower()

    return AttemptResultDto(
        attemptId=attempt.id,
        attemptType="weekly_check" if mode == "weekly-check" else "practice",
        title=attempt.title or ("Weekly Check" if mode == "weekly-check" else "Practice Result"),
        totalQuestions=total_questions,
        correctCount=attempt.correct_count,
        wrongCount=wrong_count,
        unansweredCount=unanswered_count,
        accuracyPct=float(attempt.accuracy_pct or 0),
        **weight_score_fields,
        startedAt=attempt.started_at_utc,
        submittedAt=attempt.submitted_at_utc or attempt.created_at_utc,
        durationSeconds=attempt.time_spent_seconds,
        durationMinutes=int(ceil(attempt.time_spent_seconds / 60)) if attempt.time_spent_seconds > 0 else None,
        scaledScore=attempt.score,
        skillBreakdown=_build_skill_breakdown(questions),
        partBreakdown=_build_part_breakdown(questions),
        weakAreas=_build_weak_areas(questions),
        questions=questions,
    )


def get_mock_test_attempt_result(db: Session, user_id: int, attempt_id: int) -> AttemptResultDto | None:
    attempt = db.scalar(
        select(MockTestAttempt)
        .options(selectinload(MockTestAttempt.answers))
        .where(MockTestAttempt.id == attempt_id, MockTestAttempt.user_id == user_id)
    )
    if attempt is None:
        return None

    answers = sorted(attempt.answers, key=lambda item: (item.question_number or 0, item.question_id))
    question_ids = [item.question_id for item in answers]
    question_lookup = get_question_lookup_by_ids(db, question_ids)
    explanation_lookup = _load_runtime_explanations(db, question_ids)
    questions = [_build_saved_result_question(item, question_lookup, explanation_lookup) for item in answers]
    weight_score_fields = _compute_attempt_weight_score_fields(answers, question_lookup)
    total_questions = attempt.total_questions or len(questions)
    unanswered_count = max(total_questions - attempt.answered_count, 0)
    wrong_count = max(attempt.answered_count - attempt.correct_count, 0)

    return AttemptResultDto(
        attemptId=attempt.id,
        attemptType=_normalize_mock_attempt_type(None, attempt.title, total_questions),
        title=attempt.title or "Mock Test Result",
        totalQuestions=total_questions,
        correctCount=attempt.correct_count,
        wrongCount=wrong_count,
        unansweredCount=unanswered_count,
        accuracyPct=float(attempt.accuracy_pct or 0),
        **weight_score_fields,
        startedAt=attempt.started_at_utc,
        submittedAt=attempt.submitted_at_utc or attempt.created_at_utc,
        durationSeconds=attempt.time_spent_seconds,
        durationMinutes=int(ceil(attempt.time_spent_seconds / 60)) if attempt.time_spent_seconds > 0 else None,
        scaledScore=attempt.total_score,
        listeningScore=attempt.listening_score,
        readingScore=attempt.reading_score,
        skillBreakdown=_build_skill_breakdown(questions),
        partBreakdown=_build_part_breakdown(questions),
        weakAreas=_build_weak_areas(questions),
        questions=questions,
    )


def _enqueue_review_items(db: Session, user_id: int, seeds: list["_ReviewSeed"]) -> int:
    if not seeds:
        return 0

    ensure_review_schema(db)
    touched = 0
    runtime_question_ids = [
        seed.questionId
        for seed in seeds
        if _normalize_review_source(seed.sourceAttemptType) in RUNTIME_REVIEW_SOURCES and seed.questionId
    ]
    runtime_summary_by_id = _load_runtime_review_summaries(db, runtime_question_ids)

    for seed in seeds:
        source = _normalize_review_source(seed.sourceAttemptType)
        review_reason = seed.reviewReason or "wrong"
        runtime_question_id = seed.questionId if source in RUNTIME_REVIEW_SOURCES else None
        diagnostic_question_id = seed.questionId if source == "diagnostic" else None
        runtime_summary = runtime_summary_by_id.get(int(runtime_question_id or 0), {})
        question_number = runtime_summary.get("QuestionNumber") or seed.questionNumber
        part = runtime_summary.get("Part") or seed.part
        section = runtime_summary.get("Section")
        skill = runtime_summary.get("SkillCode") or seed.skill
        correct_option_key = runtime_summary.get("CorrectOptionKey") or seed.correctOptionKey

        if source in RUNTIME_REVIEW_SOURCES and not runtime_question_id:
            logger.warning(
                "Skipping ReviewQueue upsert: missing RuntimeQuestionId userId=%s source=%s attemptId=%s reason=%s",
                user_id,
                source,
                seed.sourceAttemptId,
                review_reason,
            )
            continue

        query = select(ReviewQueueItem).where(
            ReviewQueueItem.user_id == user_id,
            ReviewQueueItem.source == source,
            ReviewQueueItem.review_reason == review_reason,
            ReviewQueueItem.is_active == True,
        )
        if seed.sourceAttemptId is None:
            query = query.where(ReviewQueueItem.attempt_id.is_(None))
        else:
            query = query.where(ReviewQueueItem.attempt_id == seed.sourceAttemptId)
        if runtime_question_id is not None:
            query = query.where(ReviewQueueItem.runtime_question_id == runtime_question_id)
        elif diagnostic_question_id is not None:
            query = query.where(ReviewQueueItem.diagnostic_question_id == diagnostic_question_id)
        else:
            query = query.where(ReviewQueueItem.question_id == seed.questionId)

        item = db.scalar(query)
        now = datetime.utcnow()
        last_answered_at = seed.lastAnsweredAtUtc or now

        if item is None:
            item = ReviewQueueItem(
                user_id=user_id,
                question_id=seed.questionId,
                source=source,
                attempt_id=seed.sourceAttemptId,
                runtime_question_id=runtime_question_id,
                diagnostic_question_id=diagnostic_question_id,
                question_number=question_number,
                part=part,
                section=section,
                skill=skill,
                skill_code=skill,
                is_correct=seed.isCorrect,
                is_skipped=seed.isSkipped,
                selected_option_key=seed.selectedOptionKey,
                correct_option_key=correct_option_key,
                review_reason=review_reason,
                last_answered_at_utc=last_answered_at,
                created_at_utc=now,
                updated_at_utc=now,
                is_active=True,
                status="pending",
                source_attempt_type=source,
                source_attempt_id=seed.sourceAttemptId,
                note=seed.note,
                added_at_utc=now,
            )
            db.add(item)
        else:
            item.question_id = seed.questionId
            item.attempt_id = seed.sourceAttemptId
            item.source_attempt_type = source
            item.source_attempt_id = seed.sourceAttemptId
            item.runtime_question_id = runtime_question_id
            item.diagnostic_question_id = diagnostic_question_id
            item.question_number = question_number or item.question_number
            item.part = part or item.part
            item.section = section or item.section
            item.skill = skill or item.skill
            item.skill_code = skill or item.skill_code
            item.is_correct = seed.isCorrect
            item.is_skipped = seed.isSkipped
            item.selected_option_key = seed.selectedOptionKey
            item.correct_option_key = correct_option_key or item.correct_option_key
            item.last_answered_at_utc = last_answered_at
            item.updated_at_utc = now
            item.status = "pending"
            item.note = seed.note or item.note
        touched += 1

    if touched:
        db.commit()

    return touched


def _load_runtime_review_summaries(db: Session, question_ids: list[int | None]) -> dict[int, dict[str, object]]:
    ids = sorted({int(value) for value in question_ids if value and int(value) > 0})
    if not ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT
                q.Id,
                q.QuestionNumber,
                q.Part,
                q.Section,
                q.SkillCode,
                q.CorrectOptionKey
            FROM dbo.ToeicPracticeQuestions q
            WHERE q.Id IN (
                SELECT TRY_CAST(value AS INT)
                FROM STRING_SPLIT(:ids_csv, ',')
                WHERE TRY_CAST(value AS INT) IS NOT NULL
            )
            """
        ),
        {"ids_csv": ",".join(str(value) for value in ids)},
    ).mappings().all()
    return {int(row["Id"]): dict(row) for row in rows}


def _update_stats(db: Session, user_id: int, seeds: list["_StatSeed"]) -> "_StatUpdateResult":
    skill_stats_updated = 0
    part_stats_updated = 0

    skill_groups: dict[str, list[_StatSeed]] = {}

    for seed in seeds:
        if seed.skill and seed.skill.strip():
            skill_groups.setdefault(seed.skill.strip().lower(), []).append(seed)

    for skill_code_lower, group in skill_groups.items():
        actual_skill_code = group[0].skill.strip()
        correct_delta = sum(1 for item in group if item.isCorrect)
        attempt_delta = len(group)
        db.execute(
            text(
                """
                SET NOCOUNT ON;

                IF EXISTS (
                    SELECT 1
                    FROM dbo.UserSkillProfiles WITH (UPDLOCK, HOLDLOCK)
                    WHERE UserId = :user_id AND SkillCode = :skill_code
                )
                BEGIN
                    UPDATE dbo.UserSkillProfiles
                    SET
                        SkillName = COALESCE(NULLIF(SkillName, N''), :skill_name),
                        CorrectCount = COALESCE(CorrectCount, 0) + :correct_delta,
                        AttemptCount = COALESCE(AttemptCount, 0) + :attempt_delta,
                        AccuracyPct = CAST(
                            CASE
                                WHEN COALESCE(AttemptCount, 0) + :attempt_delta > 0 THEN
                                    ((COALESCE(CorrectCount, 0) + :correct_delta) * 100.0)
                                    / (COALESCE(AttemptCount, 0) + :attempt_delta)
                                ELSE 0
                            END AS DECIMAL(7, 2)
                        ),
                        LastPracticedAtUtc = SYSUTCDATETIME(),
                        UpdatedAtUtc = SYSUTCDATETIME()
                    WHERE UserId = :user_id AND SkillCode = :skill_code;
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.UserSkillProfiles
                    (
                        UserId,
                        SkillCode,
                        SkillName,
                        AccuracyPct,
                        CorrectCount,
                        AttemptCount,
                        LastPracticedAtUtc,
                        UpdatedAtUtc
                    )
                    VALUES
                    (
                        :user_id,
                        :skill_code,
                        :skill_name,
                        CAST(
                            CASE
                                WHEN :attempt_delta > 0 THEN (:correct_delta * 100.0) / :attempt_delta
                                ELSE 0
                            END AS DECIMAL(7, 2)
                        ),
                        :correct_delta,
                        :attempt_delta,
                        SYSUTCDATETIME(),
                        SYSUTCDATETIME()
                    );
                END
                """
            ),
            {
                "user_id": user_id,
                "skill_code": actual_skill_code,
                "skill_name": actual_skill_code,
                "correct_delta": correct_delta,
                "attempt_delta": attempt_delta,
            },
        )
        skill_stats_updated += 1

    part_groups: dict[int, list[_StatSeed]] = {}

    for seed in seeds:
        if seed.part and seed.part > 0:
            part_groups.setdefault(seed.part, []).append(seed)

    for part, group in part_groups.items():
        correct_delta = sum(1 for item in group if item.isCorrect)
        attempt_delta = len(group)
        db.execute(
            text(
                """
                SET NOCOUNT ON;

                IF EXISTS (
                    SELECT 1
                    FROM dbo.UserPartStats WITH (UPDLOCK, HOLDLOCK)
                    WHERE UserId = :user_id AND Part = :part
                )
                BEGIN
                    UPDATE dbo.UserPartStats
                    SET
                        CorrectCount = COALESCE(CorrectCount, 0) + :correct_delta,
                        AttemptCount = COALESCE(AttemptCount, 0) + :attempt_delta,
                        AccuracyPct = CAST(
                            CASE
                                WHEN COALESCE(AttemptCount, 0) + :attempt_delta > 0 THEN
                                    ((COALESCE(CorrectCount, 0) + :correct_delta) * 100.0)
                                    / (COALESCE(AttemptCount, 0) + :attempt_delta)
                                ELSE 0
                            END AS DECIMAL(7, 2)
                        ),
                        UpdatedAtUtc = SYSUTCDATETIME()
                    WHERE UserId = :user_id AND Part = :part;
                END
                ELSE
                BEGIN
                    INSERT INTO dbo.UserPartStats
                    (
                        UserId,
                        Part,
                        AccuracyPct,
                        CorrectCount,
                        AttemptCount,
                        AverageTimeSeconds,
                        UpdatedAtUtc
                    )
                    VALUES
                    (
                        :user_id,
                        :part,
                        CAST(
                            CASE
                                WHEN :attempt_delta > 0 THEN (:correct_delta * 100.0) / :attempt_delta
                                ELSE 0
                            END AS DECIMAL(7, 2)
                        ),
                        :correct_delta,
                        :attempt_delta,
                        0,
                        SYSUTCDATETIME()
                    );
                END
                """
            ),
            {
                "user_id": user_id,
                "part": part,
                "correct_delta": correct_delta,
                "attempt_delta": attempt_delta,
            },
        )
        part_stats_updated += 1

    if skill_stats_updated or part_stats_updated:
        db.commit()

    return _StatUpdateResult(
        skillStatsUpdated=skill_stats_updated,
        partStatsUpdated=part_stats_updated,
    )


def _sync_user_profile(db: Session, user_id: int, latest_weak_skills_json: str | None = None) -> None:
    user_exists = db.scalar(select(User.id).where(User.id == user_id))
    if user_exists is None:
        return

    if latest_weak_skills_json and latest_weak_skills_json.strip():
        weak_skills = _parse_weak_skills(latest_weak_skills_json)
    else:
        weak_skills = db.execute(
            select(UserSkillProfile.skill_name, UserSkillProfile.skill_code)
            .where(UserSkillProfile.user_id == user_id, UserSkillProfile.attempt_count > 0)
            .order_by(UserSkillProfile.accuracy_pct, UserSkillProfile.attempt_count.desc())
            .limit(5)
        ).all()
        weak_skills = [row[0] or row[1] for row in weak_skills]

    weak_skills_json = json.dumps(
        list(
            dict.fromkeys(
                item.strip()
                for item in weak_skills
                if item and item.strip()
            )
        )
    )
    db.execute(
        text("UPDATE dbo.Users SET WeakSkillsJson = :weak_skills_json WHERE Id = :user_id"),
        {"weak_skills_json": weak_skills_json, "user_id": user_id},
    )
    db.commit()


def _build_practice_result(attempt_id: int, request: SavePracticeAttemptRequest) -> AttemptResultDto:
    questions = [
        _build_practice_result_question(item)
        for item in sorted(request.answers, key=lambda x: (x.questionNumber, x.questionId))
    ]

    total_questions = request.totalQuestions or len(questions)
    unanswered_count = max(total_questions - request.answeredCount, 0)
    wrong_count = max(request.answeredCount - request.correctCount, 0)
    weight_score_fields = _compute_attempt_weight_score_fields(request.answers)

    return AttemptResultDto(
        attemptId=attempt_id,
        attemptType="weekly_check" if (request.mode or "").lower() == "weekly-check" else "practice",
        title=request.title or ("Weekly Check" if (request.mode or "").lower() == "weekly-check" else "Practice Result"),
        totalQuestions=total_questions,
        correctCount=request.correctCount,
        wrongCount=wrong_count,
        unansweredCount=unanswered_count,
        accuracyPct=request.accuracyPct,
        **weight_score_fields,
        startedAt=request.startedAtUtc,
        submittedAt=request.submittedAtUtc or datetime.utcnow(),
        durationSeconds=request.timeSpentSeconds,
        durationMinutes=int(ceil(request.timeSpentSeconds / 60)) if request.timeSpentSeconds > 0 else None,
        scaledScore=request.score,
        skillBreakdown=_build_skill_breakdown(questions),
        partBreakdown=_build_part_breakdown(questions),
        weakAreas=_build_weak_areas(questions),
        questions=questions,
    )


def _build_mock_test_result(attempt_id: int, request: SaveMockTestAttemptRequest) -> AttemptResultDto:
    questions = [
        _build_mock_result_question(item)
        for item in sorted(request.answers, key=lambda x: (x.questionNumber, x.questionId))
    ]

    total_questions = request.totalQuestions or len(questions)
    unanswered_count = max(total_questions - request.answeredCount, 0)
    wrong_count = max(request.answeredCount - request.correctCount, 0)
    weight_score_fields = _compute_attempt_weight_score_fields(request.answers)

    return AttemptResultDto(
        attemptId=attempt_id,
        attemptType=(request.attemptType or "mock-test").strip().lower(),
        title=request.title or "Mock Test Result",
        totalQuestions=total_questions,
        correctCount=request.correctCount,
        wrongCount=wrong_count,
        unansweredCount=unanswered_count,
        accuracyPct=request.accuracyPct,
        **weight_score_fields,
        startedAt=request.startedAtUtc,
        submittedAt=request.submittedAtUtc or datetime.utcnow(),
        durationSeconds=request.timeSpentSeconds,
        durationMinutes=int(ceil(request.timeSpentSeconds / 60)) if request.timeSpentSeconds > 0 else None,
        scaledScore=request.totalScore,
        listeningScore=request.listeningScore,
        readingScore=request.readingScore,
        skillBreakdown=_build_skill_breakdown(questions),
        partBreakdown=_build_part_breakdown(questions),
        weakAreas=_build_weak_areas(questions),
        questions=questions,
    )


def _build_practice_result_question(answer: SavePracticeAttemptAnswerRequest) -> AttemptResultQuestionDto:
    return AttemptResultQuestionDto(
        questionId=answer.questionId,
        questionNumber=answer.questionNumber,
        test=answer.test,
        part=answer.part,
        section=answer.section.strip() if answer.section and answer.section.strip() else _infer_section(answer.part),
        partLabel=answer.partLabel,
        type=answer.type,
        groupId=answer.groupId,
        skill=answer.skill.strip() if answer.skill and answer.skill.strip() else "general",
        subskill=answer.subskill.strip() if answer.subskill and answer.subskill.strip() else None,
        question=answer.question or "",
        options=answer.options or [],
        userAnswer=_resolve_answer_text(answer.selectedAnswerIndex, answer.selectedAnswerText, answer.options),
        userAnswerIndex=answer.selectedAnswerIndex,
        correctAnswer=_resolve_correct_answer_text(answer.correctAnswer, answer.correctAnswerIndex, answer.correctAnswerText, answer.options),
        correctAnswerIndex=answer.correctAnswerIndex,
        isCorrect=answer.isCorrect,
        explanation=_build_explanation(
            answer.explanation,
            answer.selectedAnswerIndex,
            answer.correctAnswerIndex,
            answer.selectedAnswerText,
            answer.correctAnswerText,
            answer.options,
        ),
        audio=answer.audio,
        graphic=answer.graphic,
        image=answer.image,
    )


def _build_mock_result_question(answer: SaveMockTestAttemptAnswerRequest) -> AttemptResultQuestionDto:
    return AttemptResultQuestionDto(
        questionId=answer.questionId,
        questionNumber=answer.questionNumber,
        test=answer.test,
        part=answer.part,
        section=answer.section.strip() if answer.section and answer.section.strip() else _infer_section(answer.part),
        partLabel=answer.partLabel,
        type=answer.type,
        groupId=answer.groupId,
        skill=answer.skill.strip() if answer.skill and answer.skill.strip() else "general",
        subskill=answer.subskill.strip() if answer.subskill and answer.subskill.strip() else None,
        question=answer.question or "",
        options=answer.options or [],
        userAnswer=_resolve_answer_text(answer.selectedAnswerIndex, answer.selectedAnswerText, answer.options),
        userAnswerIndex=answer.selectedAnswerIndex,
        correctAnswer=_resolve_correct_answer_text(answer.correctAnswer, answer.correctAnswerIndex, answer.correctAnswerText, answer.options),
        correctAnswerIndex=answer.correctAnswerIndex,
        isCorrect=answer.isCorrect,
        explanation=_build_explanation(
            answer.explanation,
            answer.selectedAnswerIndex,
            answer.correctAnswerIndex,
            answer.selectedAnswerText,
            answer.correctAnswerText,
            answer.options,
        ),
        audio=answer.audio,
        graphic=answer.graphic,
        image=answer.image,
    )


def _load_runtime_explanations(db: Session, question_ids: list[int]) -> dict[int, dict]:
    ids = sorted({int(value) for value in question_ids if value and int(value) > 0})
    if not ids:
        return {}
    try:
        table_exists = db.execute(text("SELECT OBJECT_ID(N'dbo.ToeicQuestionExplanations', N'U')")).scalar()
        if not table_exists:
            return {}
        rows = db.execute(
            text(
                """
                SELECT
                    e.RuntimeQuestionId,
                    e.ExplanationText,
                    e.RawBlock,
                    CAST(NULL AS NVARCHAR(MAX)) AS RawText
                FROM dbo.ToeicQuestionExplanations e
                WHERE e.RuntimeQuestionId IN (
                    SELECT TRY_CAST(value AS INT)
                    FROM STRING_SPLIT(:ids_csv, ',')
                    WHERE TRY_CAST(value AS INT) IS NOT NULL
                )
                ORDER BY e.Id
                """
            ),
            {"ids_csv": ",".join(str(value) for value in ids)},
        ).mappings().all()
    except Exception:
        logger.info("Could not load runtime TOEIC explanations for attempt result.", exc_info=True)
        return {}

    result: dict[int, dict] = {}
    for row in rows:
        runtime_question_id = row.get("RuntimeQuestionId")
        if runtime_question_id is None:
            continue
        result.setdefault(int(runtime_question_id), dict(row))
    return result


def _find_source_question(
    answer,
    question_lookup: dict[str, ToeicRunnerQuestionDto],
) -> ToeicRunnerQuestionDto | None:
    part = answer.part or 0
    if part > 0:
        direct = question_lookup.get(build_question_lookup_key(part, answer.question_id))
        if direct is not None:
            return direct
    for candidate in question_lookup.values():
        if candidate.id == answer.question_id or candidate.questionId == answer.question_id or candidate.sourceQuestionId == answer.question_id:
            return candidate
    return None


def _build_saved_result_question(
    answer,
    question_lookup: dict[str, ToeicRunnerQuestionDto],
    explanation_lookup: dict[int, dict] | None = None,
) -> AttemptResultQuestionDto:
    source_question = _find_source_question(answer, question_lookup)
    if source_question is None:
        logger.warning(
            "Practice summary hydrate failed: runtime question not found attemptAnswerId=%s questionId=%s",
            getattr(answer, "id", None),
            answer.question_id,
        )
    part = answer.part or (source_question.part if source_question else 0)
    options = list(source_question.options) if source_question else []
    option_rows = _build_attempt_option_rows(source_question)
    raw_explanation = (explanation_lookup or {}).get(answer.question_id, {})
    explanation_text = _first_non_empty(
        raw_explanation.get("ExplanationText"),
        source_question.explanation if source_question else None,
        None if _is_placeholder_explanation(getattr(answer, "explanation", None)) else getattr(answer, "explanation", None),
    )
    raw_block = raw_explanation.get("RawBlock")
    raw_text = raw_explanation.get("RawText")

    selected_answer_text = _resolve_answer_text(answer.selected_answer_index, None, options)
    correct_answer_text = _resolve_correct_answer_text(None, answer.correct_answer_index, None, options)
    selected_option_key = _option_label(answer.selected_answer_index) if answer.selected_answer_index is not None else None
    correct_option_key = _option_label(answer.correct_answer_index) if answer.correct_answer_index is not None else (
        source_question.correctAnswer if source_question else None
    )
    selected_option_text = _option_text(answer.selected_answer_index, options)
    correct_option_text = _option_text(answer.correct_answer_index, options)
    passage = _build_attempt_passage(source_question)
    audio_path = _asset_path(source_question.audio if source_question else None) or (passage.audioPath if passage else None)
    image_path = (
        _asset_path(source_question.image if source_question else None)
        or _asset_path(source_question.graphic if source_question else None)
        or (passage.imagePath if passage else None)
    )

    return AttemptResultQuestionDto(
        questionId=answer.question_id,
        runtimeQuestionId=source_question.id if source_question else None,
        missingReason=None if source_question else f"Runtime question not found for questionId={answer.question_id}",
        questionNumber=answer.question_number or 0,
        test=source_question.test if source_question else 0,
        part=part,
        section=source_question.section if source_question else _infer_section(part),
        partLabel=source_question.partLabel if source_question else (f"Part {part}" if part > 0 else None),
        type=source_question.type if source_question else None,
        groupId=source_question.groupId if source_question else None,
        skill=source_question.skill if source_question and source_question.skill else (answer.skill or "general"),
        subskill=source_question.subskill if source_question else None,
        question=source_question.question if source_question else f"Question {answer.question_number or answer.question_id}",
        questionText=source_question.question if source_question else "",
        options=options,
        optionRows=option_rows,
        userAnswer=selected_answer_text,
        userAnswerIndex=answer.selected_answer_index,
        selectedOptionKey=selected_option_key,
        selectedOptionText=selected_option_text,
        correctAnswer=correct_answer_text,
        correctAnswerIndex=answer.correct_answer_index,
        correctOptionKey=correct_option_key,
        correctOptionText=correct_option_text,
        isCorrect=answer.is_correct,
        explanation=explanation_text or _build_explanation(
            None,
            answer.selected_answer_index,
            answer.correct_answer_index,
            None,
            None,
            options,
        ),
        explanationText=explanation_text,
        rawBlock=raw_block,
        rawText=raw_text,
        passage=passage,
        audio=_build_attempt_asset(source_question.audio if source_question else None),
        audioPath=audio_path,
        graphic=_build_attempt_asset(source_question.graphic if source_question else None),
        image=_build_attempt_asset(source_question.image if source_question else None),
        imagePath=image_path,
    )


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return None


def _is_placeholder_explanation(value: str | None) -> bool:
    normalized = " ".join(str(value or "").strip().lower().split())
    return normalized in {
        "",
        "no explanation is available for this question yet.",
        "no explanation available.",
    }


def _asset_path(asset: AttemptAssetDto | None) -> str | None:
    path = getattr(asset, "path", None)
    return path if path and str(path).strip() else None


def _build_attempt_asset(asset) -> AttemptAssetDto | None:
    path = _asset_path(asset)
    return AttemptAssetDto(path=path) if path else None


def _option_label(index: int | None) -> str | None:
    if index is None or index < 0:
        return None
    return chr(ord("A") + index) if index < 26 else str(index + 1)

def _option_text(index: int | None, options: list[str]) -> str | None:
    if index is None or index < 0 or index >= len(options):
        return None
    return options[index]


def _build_attempt_option_rows(source_question: ToeicRunnerQuestionDto | None) -> list[AttemptResultOptionDto]:
    if source_question is None:
        return []
    correct_index = source_question.correctAnswerIndex
    rows: list[AttemptResultOptionDto] = []
    for index, option_text in enumerate(source_question.options):
        key = _option_label(index)
        text_value = str(option_text or "")
        if not text_value.strip() or text_value.strip().upper() == key:
            logger.warning(
                "Practice summary hydrate warning: option text missing questionId=%s option=%s",
                source_question.id,
                key,
            )
        rows.append(
            AttemptResultOptionDto(
                key=key,
                text=text_value,
                isCorrect=correct_index == index,
                sortOrder=index,
            )
        )
    return rows


def _build_attempt_passage(source_question: ToeicRunnerQuestionDto | None) -> AttemptResultPassageDto | None:
    passage = source_question.passage if source_question else None
    if passage is None:
        return None
    audio_path = _asset_path(passage.audio)
    image_path = _asset_path(passage.image)
    if not (passage.id or passage.groupCode or passage.title or passage.text or audio_path or image_path):
        return None
    return AttemptResultPassageDto(
        id=passage.id,
        groupCode=passage.groupCode,
        title=passage.title,
        text=passage.text,
        audioPath=audio_path,
        imagePath=image_path,
        audio=_build_attempt_asset(passage.audio),
        image=_build_attempt_asset(passage.image),
    )


def _build_skill_breakdown(questions: list[AttemptResultQuestionDto]) -> list[AttemptSkillBreakdownDto]:
    grouped: dict[str, list[AttemptResultQuestionDto]] = {}

    for question in questions:
        key = question.skill.strip() if question.skill.strip() else "general"
        grouped.setdefault(key, []).append(question)

    result = []

    for key, group in grouped.items():
        total = len(group)
        correct = sum(1 for item in group if item.isCorrect)
        result.append(
            AttemptSkillBreakdownDto(
                skill=key,
                total=total,
                correct=correct,
                accuracyPct=round(correct * 100 / total, 2) if total else 0,
            )
        )

    return sorted(result, key=lambda item: (item.accuracyPct, -item.total))


def _build_part_breakdown(questions: list[AttemptResultQuestionDto]) -> list[AttemptPartBreakdownDto]:
    grouped: dict[int, list[AttemptResultQuestionDto]] = {}

    for question in questions:
        if question.part > 0:
            grouped.setdefault(question.part, []).append(question)

    result = []

    for part, group in grouped.items():
        total = len(group)
        correct = sum(1 for item in group if item.isCorrect)
        result.append(
            AttemptPartBreakdownDto(
                part=part,
                total=total,
                correct=correct,
                accuracyPct=round(correct * 100 / total, 2) if total else 0,
            )
        )

    return sorted(result, key=lambda item: item.part)


def _build_weak_areas(questions: list[AttemptResultQuestionDto]) -> list[AttemptWeakAreaDto]:
    result: list[AttemptWeakAreaDto] = []

    weakest_skill = _build_weak_area_seed(
        {key: value for key, value in _group_by_skill(questions).items()}
    )

    if weakest_skill:
        result.append(
            AttemptWeakAreaDto(
                type="skill",
                label=weakest_skill.label,
                accuracyPct=weakest_skill.accuracyPct,
                total=weakest_skill.total,
                correct=weakest_skill.correct,
                suggestion=f"Æ¯u tiÃªn luyá»‡n láº¡i nhÃ³m ká»¹ nÄƒng {weakest_skill.label} trÆ°á»›c á»Ÿ cÃ¡c cÃ¢u tÆ°Æ¡ng tá»±.",
            )
        )

    subskill_groups = {
        key: value
        for key, value in _group_by_subskill(questions).items()
        if key
    }

    weakest_subskill = _build_weak_area_seed(subskill_groups)

    if weakest_subskill:
        result.append(
            AttemptWeakAreaDto(
                type="subskill",
                label=weakest_subskill.label,
                accuracyPct=weakest_subskill.accuracyPct,
                total=weakest_subskill.total,
                correct=weakest_subskill.correct,
                suggestion=f"Ã”n láº¡i subskill {weakest_subskill.label} vÃ  xem ká»¹ dáº¥u hiá»‡u nháº­n biáº¿t Ä‘Ã¡p Ã¡n Ä‘Ãºng.",
            )
        )

    part_groups = {
        f"Part {part}": value
        for part, value in _group_by_part(questions).items()
    }

    weakest_part = _build_weak_area_seed(part_groups)

    if weakest_part:
        result.append(
            AttemptWeakAreaDto(
                type="part",
                label=weakest_part.label,
                accuracyPct=weakest_part.accuracyPct,
                total=weakest_part.total,
                correct=weakest_part.correct,
                suggestion=f"DÃ nh thÃªm thá»i gian luyá»‡n theo part {weakest_part.label.replace('Part ', '')} Ä‘á»ƒ cáº£i thiá»‡n Ä‘á»™ á»•n Ä‘á»‹nh.",
            )
        )

    return result


def _group_by_skill(questions: list[AttemptResultQuestionDto]) -> dict[str, list[AttemptResultQuestionDto]]:
    grouped: dict[str, list[AttemptResultQuestionDto]] = {}

    for question in questions:
        key = question.skill.strip() if question.skill.strip() else "general"
        grouped.setdefault(key, []).append(question)

    return grouped


def _group_by_subskill(questions: list[AttemptResultQuestionDto]) -> dict[str, list[AttemptResultQuestionDto]]:
    grouped: dict[str, list[AttemptResultQuestionDto]] = {}

    for question in questions:
        if question.subskill and question.subskill.strip():
            grouped.setdefault(question.subskill.strip(), []).append(question)

    return grouped


def _group_by_part(questions: list[AttemptResultQuestionDto]) -> dict[int, list[AttemptResultQuestionDto]]:
    grouped: dict[int, list[AttemptResultQuestionDto]] = {}

    for question in questions:
        if question.part > 0:
            grouped.setdefault(question.part, []).append(question)

    return grouped


def _build_weak_area_seed(groups: dict[str, list[AttemptResultQuestionDto]]) -> "_WeakAreaSeed | None":
    if not groups:
        return None

    items = []

    for label, group in groups.items():
        total = len(group)
        correct = sum(1 for item in group if item.isCorrect)

        items.append(
            _WeakAreaSeed(
                label=label,
                total=total,
                correct=correct,
                accuracyPct=round(correct * 100 / total, 2) if total else 0,
            )
        )

    return sorted(items, key=lambda item: (item.accuracyPct, -item.total))[0]


def _infer_section(part: int) -> str:
    return "Listening" if part <= 4 else "Reading"


def _resolve_answer_text(answer_index: int | None, answer_text: str | None, options: list[str] | None) -> str | None:
    if answer_text and answer_text.strip():
        return _with_choice_prefix(answer_index, answer_text.strip())

    if answer_index is not None and answer_index >= 0 and options and answer_index < len(options):
        return _with_choice_prefix(answer_index, options[answer_index])

    return None


def _resolve_correct_answer_text(
    correct_answer: str | None,
    correct_answer_index: int | None,
    correct_answer_text: str | None,
    options: list[str] | None,
) -> str | None:
    if correct_answer_text and correct_answer_text.strip():
        return _with_choice_prefix(correct_answer_index, correct_answer_text.strip())

    if correct_answer_index is not None and correct_answer_index >= 0 and options and correct_answer_index < len(options):
        return _with_choice_prefix(correct_answer_index, options[correct_answer_index])

    if correct_answer and correct_answer.strip():
        return correct_answer.strip()

    return None


def _with_choice_prefix(answer_index: int | None, answer_text: str) -> str:
    if answer_index is None or answer_index < 0:
        return answer_text

    return f"{chr(ord('A') + answer_index)}. {answer_text}"


def _build_explanation(
    explanation: str | None,
    selected_answer_index: int | None,
    correct_answer_index: int | None,
    selected_answer_text: str | None,
    correct_answer_text: str | None,
    options: list[str] | None,
) -> str:
    if explanation and explanation.strip():
        return explanation.strip()

    selected = _resolve_answer_text(selected_answer_index, selected_answer_text, options)
    correct = _resolve_correct_answer_text(None, correct_answer_index, correct_answer_text, options)

    if selected_answer_index is None:
        return "Báº¡n Ä‘Ã£ bá» qua cÃ¢u nÃ y." if correct is None else f"Báº¡n Ä‘Ã£ bá» qua cÃ¢u nÃ y. ÄÃ¡p Ã¡n Ä‘Ãºng lÃ  {correct}."

    if correct_answer_index is None:
        return (
            "ChÆ°a cÃ³ giáº£i thÃ­ch chi tiáº¿t cho cÃ¢u nÃ y."
            if selected is None
            else f"Báº¡n Ä‘Ã£ chá»n {selected}. ChÆ°a cÃ³ giáº£i thÃ­ch chi tiáº¿t cho cÃ¢u nÃ y."
        )

    if selected_answer_index == correct_answer_index:
        return f"Báº¡n Ä‘Ã£ chá»n Ä‘Ãºng Ä‘Ã¡p Ã¡n {correct}."

    return (
        "ChÆ°a cÃ³ giáº£i thÃ­ch chi tiáº¿t cho cÃ¢u nÃ y."
        if selected is None or correct is None
        else f"Báº¡n Ä‘Ã£ chá»n {selected}. ÄÃ¡p Ã¡n Ä‘Ãºng lÃ  {correct}."
    )


def _diagnostic_answer_to_dict(item) -> dict:
    return {
        "questionId": item.questionId,
        "questionNumber": item.questionNumber,
        "part": item.part,
        "skill": item.skill,
        "subskill": item.subskill,
        "selectedAnswerIndex": item.selectedAnswerIndex,
        "correctAnswerIndex": item.correctAnswerIndex,
        "isCorrect": item.isCorrect,
    }


def _parse_weak_skills(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return []

    try:
        parsed = json.loads(raw)

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass

    return [
        item.strip()
        for item in raw.replace("\r", "\n").replace(";", ",").replace("|", ",").split(",")
        if item.strip()
    ]


@dataclass
class _ReviewSeed:
    questionId: int
    questionNumber: int | None
    part: int | None
    skill: str | None
    sourceAttemptType: str
    sourceAttemptId: int
    selectedOptionKey: str | None
    correctOptionKey: str | None
    isCorrect: bool | None
    isSkipped: bool
    reviewReason: str
    lastAnsweredAtUtc: datetime | None
    note: str | None


@dataclass
class _StatSeed:
    part: int | None
    skill: str | None
    isCorrect: bool


@dataclass
class _StatUpdateResult:
    skillStatsUpdated: int
    partStatsUpdated: int


@dataclass
class _WeakAreaSeed:
    label: str
    total: int
    correct: int
    accuracyPct: float

