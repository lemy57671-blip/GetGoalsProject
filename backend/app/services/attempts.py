from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
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
    UserPartStat,
    UserSkillProfile,
)
from app.schemas.attempts import (
    AttemptPartBreakdownDto,
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


def save_practice_attempt(db: Session, user_id: int, request: SavePracticeAttemptRequest) -> SaveAttemptResponse:
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

    incorrect_answers = [item for item in attempt.answers if not item.is_correct]
    review_queued_count = _enqueue_review_items(
        db,
        user_id,
        [
            _ReviewSeed(
                questionId=item.question_id,
                part=item.part,
                skill=item.skill,
                sourceAttemptType="practice",
                sourceAttemptId=attempt.id,
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

    return SaveAttemptResponse(
        attemptId=attempt.id,
        reviewQueuedCount=review_queued_count,
        skillStatsUpdated=stat_result.skillStatsUpdated,
        partStatsUpdated=stat_result.partStatsUpdated,
        result=_build_practice_result(attempt.id, request),
    )


def save_mock_test_attempt(db: Session, user_id: int, request: SaveMockTestAttemptRequest) -> SaveAttemptResponse:
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

    review_queued_count = _enqueue_review_items(
        db,
        user_id,
        [
            _ReviewSeed(
                questionId=item.question_id,
                part=item.part,
                skill=item.skill,
                sourceAttemptType="mock-test",
                sourceAttemptId=attempt.id,
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

    return SaveAttemptResponse(
        attemptId=attempt.id,
        reviewQueuedCount=review_queued_count,
        skillStatsUpdated=stat_result.skillStatsUpdated,
        partStatsUpdated=stat_result.partStatsUpdated,
        result=_build_mock_test_result(attempt.id, request),
    )


def save_diagnostic_attempt(db: Session, user_id: int, request: SaveDiagnosticAttemptRequest) -> SaveAttemptResponse:
    """
    Lưu kết quả bài test đầu vào vào 2 bảng:
    - dbo.DiagnosticAttempts
    - dbo.DiagnosticAttemptAnswers

    Đồng thời:
    - Tính Rasch theta từ dữ liệu đúng/sai.
    - Lưu Theta vào DiagnosticAttempts.Theta.
    - Lưu EstimatedScore theo Rasch vào DiagnosticAttempts.EstimatedScore.
    - Lưu ScoreRule là điểm rule-based cũ theo accuracy để đối chiếu.
    - Giữ logic cũ: update profile, review queue, skill stats, part stats.
    """

    now = datetime.utcnow()
    user = db.get(User, user_id)
    answers = list(request.answers or [])

    question_meta_by_id: dict[int, dict] = {}

    if answers:
        question_ids_csv = ",".join(
            str(item.questionId)
            for item in answers
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

    answered_count = sum(
        1
        for item in answers
        if item.selectedAnswerIndex is not None and item.selectedAnswerIndex >= 0
    )

    total_questions = request.totalQuestions or len(answers)

    correct_count = request.correctCount
    if correct_count is None:
        correct_count = sum(1 for item in answers if item.isCorrect)

    accuracy_pct = request.accuracyPct
    if accuracy_pct is None:
        accuracy_pct = round(correct_count * 100 / total_questions, 2) if total_questions else 0

    score_rule = int(round(5 + (float(accuracy_pct) / 100.0) * 985))
    score_rule = max(5, min(score_rule, 990))

    rasch_items: list[dict] = []

    for item in answers:
        meta = question_meta_by_id.get(item.questionId, {})
        legacy_id = meta.get("legacy_id")

        if legacy_id is not None:
            rasch_items.append(
                {
                    "item_id": int(legacy_id),
                    "is_correct": bool(item.isCorrect),
                }
            )

    rasch_result = score_diagnostic_with_rasch(rasch_items)

    theta = rasch_result.get("theta")
    estimated_score = int(rasch_result.get("estimated_score") or request.score or score_rule)

    level_name = rasch_result.get("level_name") or request.levelName
    level_range = rasch_result.get("level_range") or request.levelRange

    if user is not None:
        user.current_score = estimated_score

        if request.targetScore is not None:
            user.target_score = request.targetScore

        if request.minutesPerDay is not None:
            user.study_minutes_per_day = request.minutesPerDay

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
        [_diagnostic_answer_to_dict(item) for item in answers],
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
                NULL,
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
            "level_name": level_name,
            "level_range": level_range,
            "answers_json": answers_json,
            "weak_subskills_json": request.weakSubskillsJson,
            "top_errors_json": request.topErrorsJson,
        },
    ).scalar_one()

    for item in answers:
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
                note=(
                    item.subskill
                    or question_meta_by_id.get(item.questionId, {}).get("subskill")
                ),
            )
            for item in answers
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
            for item in answers
        ],
    )

    _sync_user_profile(db, user_id, request.weakSubskillsJson)

    return SaveAttemptResponse(
        attemptId=attempt_id,
        reviewQueuedCount=review_queued_count,
        skillStatsUpdated=stat_result.skillStatsUpdated,
        partStatsUpdated=stat_result.partStatsUpdated,
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
    question_lookup = get_question_lookup_by_ids(db, [item.question_id for item in answers])
    questions = [_build_saved_result_question(item, question_lookup) for item in answers]
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
    question_lookup = get_question_lookup_by_ids(db, [item.question_id for item in answers])
    questions = [_build_saved_result_question(item, question_lookup) for item in answers]
    total_questions = attempt.total_questions or len(questions)
    unanswered_count = max(total_questions - attempt.answered_count, 0)
    wrong_count = max(attempt.answered_count - attempt.correct_count, 0)

    return AttemptResultDto(
        attemptId=attempt.id,
        attemptType="mock-test",
        title=attempt.title or "Mock Test Result",
        totalQuestions=total_questions,
        correctCount=attempt.correct_count,
        wrongCount=wrong_count,
        unansweredCount=unanswered_count,
        accuracyPct=float(attempt.accuracy_pct or 0),
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

    queued = 0

    for seed in seeds:
        exists = db.scalar(
            select(ReviewQueueItem.id).where(
                ReviewQueueItem.user_id == user_id,
                ReviewQueueItem.question_id == seed.questionId,
                ReviewQueueItem.source_attempt_type == seed.sourceAttemptType,
                ReviewQueueItem.source_attempt_id == seed.sourceAttemptId,
            )
        )

        if exists:
            continue

        db.add(
            ReviewQueueItem(
                user_id=user_id,
                question_id=seed.questionId,
                part=seed.part,
                skill=seed.skill,
                status="pending",
                source_attempt_type=seed.sourceAttemptType,
                source_attempt_id=seed.sourceAttemptId,
                note=seed.note,
                added_at_utc=datetime.utcnow(),
            )
        )
        queued += 1

    if queued:
        db.commit()

    return queued


def _update_stats(db: Session, user_id: int, seeds: list["_StatSeed"]) -> "_StatUpdateResult":
    skill_stats_updated = 0
    part_stats_updated = 0

    skill_groups: dict[str, list[_StatSeed]] = {}

    for seed in seeds:
        if seed.skill and seed.skill.strip():
            skill_groups.setdefault(seed.skill.strip().lower(), []).append(seed)

    for skill_code_lower, group in skill_groups.items():
        actual_skill_code = group[0].skill.strip()

        profile = db.scalar(
            select(UserSkillProfile).where(
                UserSkillProfile.user_id == user_id,
                UserSkillProfile.skill_code == actual_skill_code,
            )
        )

        if profile is None:
            profile = UserSkillProfile(
                user_id=user_id,
                skill_code=actual_skill_code,
                skill_name=actual_skill_code,
                correct_count=0,
                attempt_count=0,
                updated_at_utc=datetime.utcnow(),
            )
            db.add(profile)

        profile.correct_count += sum(1 for item in group if item.isCorrect)
        profile.attempt_count += len(group)
        profile.accuracy_pct = (
            round(profile.correct_count * 100 / profile.attempt_count, 2)
            if profile.attempt_count
            else 0
        )
        profile.last_practiced_at_utc = datetime.utcnow()
        profile.updated_at_utc = datetime.utcnow()
        skill_stats_updated += 1

    part_groups: dict[int, list[_StatSeed]] = {}

    for seed in seeds:
        if seed.part and seed.part > 0:
            part_groups.setdefault(seed.part, []).append(seed)

    for part, group in part_groups.items():
        stat = db.scalar(
            select(UserPartStat).where(
                UserPartStat.user_id == user_id,
                UserPartStat.part == part,
            )
        )

        if stat is None:
            stat = UserPartStat(
                user_id=user_id,
                part=part,
                correct_count=0,
                attempt_count=0,
                updated_at_utc=datetime.utcnow(),
                average_time_seconds=0,
            )
            db.add(stat)

        stat.correct_count += sum(1 for item in group if item.isCorrect)
        stat.attempt_count += len(group)
        stat.accuracy_pct = (
            round(stat.correct_count * 100 / stat.attempt_count, 2)
            if stat.attempt_count
            else 0
        )
        stat.updated_at_utc = datetime.utcnow()
        part_stats_updated += 1

    if skill_stats_updated or part_stats_updated:
        db.commit()

    return _StatUpdateResult(
        skillStatsUpdated=skill_stats_updated,
        partStatsUpdated=part_stats_updated,
    )


def _sync_user_profile(db: Session, user_id: int, latest_weak_skills_json: str | None = None) -> None:
    user = db.get(User, user_id)

    if user is None:
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

    user.weak_skills_json = json.dumps(
        list(
            dict.fromkeys(
                item.strip()
                for item in weak_skills
                if item and item.strip()
            )
        )
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

    return AttemptResultDto(
        attemptId=attempt_id,
        attemptType="weekly_check" if (request.mode or "").lower() == "weekly-check" else "practice",
        title=request.title or ("Weekly Check" if (request.mode or "").lower() == "weekly-check" else "Practice Result"),
        totalQuestions=total_questions,
        correctCount=request.correctCount,
        wrongCount=wrong_count,
        unansweredCount=unanswered_count,
        accuracyPct=request.accuracyPct,
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

    return AttemptResultDto(
        attemptId=attempt_id,
        attemptType=(request.attemptType or "mock-test").strip().lower(),
        title=request.title or "Mock Test Result",
        totalQuestions=total_questions,
        correctCount=request.correctCount,
        wrongCount=wrong_count,
        unansweredCount=unanswered_count,
        accuracyPct=request.accuracyPct,
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


def _build_saved_result_question(answer, question_lookup: dict[str, ToeicRunnerQuestionDto]) -> AttemptResultQuestionDto:
    part = answer.part or 0
    source_question = question_lookup.get(build_question_lookup_key(part, answer.question_id)) if part > 0 else None
    options = list(source_question.options) if source_question else []

    selected_answer_text = _resolve_answer_text(answer.selected_answer_index, None, options)
    correct_answer_text = _resolve_correct_answer_text(None, answer.correct_answer_index, None, options)

    return AttemptResultQuestionDto(
        questionId=answer.question_id,
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
        options=options,
        userAnswer=selected_answer_text,
        userAnswerIndex=answer.selected_answer_index,
        correctAnswer=correct_answer_text,
        correctAnswerIndex=answer.correct_answer_index,
        isCorrect=answer.is_correct,
        explanation=_build_explanation(
            answer.explanation,
            answer.selected_answer_index,
            answer.correct_answer_index,
            None,
            None,
            options,
        ),
        audio=source_question.audio if source_question else None,
        graphic=source_question.graphic if source_question else None,
        image=source_question.image if source_question else None,
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
                suggestion=f"Ưu tiên luyện lại nhóm kỹ năng {weakest_skill.label} trước ở các câu tương tự.",
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
                suggestion=f"Ôn lại subskill {weakest_subskill.label} và xem kỹ dấu hiệu nhận biết đáp án đúng.",
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
                suggestion=f"Dành thêm thời gian luyện theo part {weakest_part.label.replace('Part ', '')} để cải thiện độ ổn định.",
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
        return "Bạn đã bỏ qua câu này." if correct is None else f"Bạn đã bỏ qua câu này. Đáp án đúng là {correct}."

    if correct_answer_index is None:
        return (
            "Chưa có giải thích chi tiết cho câu này."
            if selected is None
            else f"Bạn đã chọn {selected}. Chưa có giải thích chi tiết cho câu này."
        )

    if selected_answer_index == correct_answer_index:
        return f"Bạn đã chọn đúng đáp án {correct}."

    return (
        "Chưa có giải thích chi tiết cho câu này."
        if selected is None or correct is None
        else f"Bạn đã chọn {selected}. Đáp án đúng là {correct}."
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
    part: int | None
    skill: str | None
    sourceAttemptType: str
    sourceAttemptId: int
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