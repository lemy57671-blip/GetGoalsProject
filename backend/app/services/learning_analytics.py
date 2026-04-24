from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    MockTestAttempt,
    MockTestAttemptAnswer,
    PracticeAttempt,
    PracticeAttemptAnswer,
    ProgressLog,
    ReviewQueueItem,
    ToeicPassage,
    ToeicQuestion,
    User,
    UserPartStat,
    UserSkillAnalytics,
    UserSkillProfile,
)
from app.schemas.analytics import (
    DashboardOverviewDto,
    HistoryPointDto,
    LatestDiagnosticDto,
    LatestMockTestDto,
    PartStatDto,
    ProfileSummaryDto,
    ProgressSummaryDto,
    RecentMockTestDto,
    RecentPracticeAttemptDto,
    ReviewQuestionDetailDto,
    ReviewQueueItemDto,
    ReviewSummaryDto,
    SkillProfileDto,
    WeakMetricDto,
    WeakPartDto,
)
from app.services.skill_analytics import to_dto, to_title
from app.utils.json_helpers import parse_string_list


def get_dashboard_overview(db: Session, user_id: int) -> DashboardOverviewDto:
    practice_attempts = db.scalars(select(PracticeAttempt).where(PracticeAttempt.user_id == user_id)).all()
    mock_attempts = db.scalars(select(MockTestAttempt).where(MockTestAttempt.user_id == user_id)).all()

    recent_attempt_window = sorted(
        [{"accuracy": float(item.accuracy_pct), "submitted": item.submitted_at_utc or item.created_at_utc} for item in practice_attempts]
        + [{"accuracy": float(item.accuracy_pct), "submitted": item.submitted_at_utc or item.created_at_utc} for item in mock_attempts],
        key=lambda row: row["submitted"],
        reverse=True,
    )[:10]
    recent_accuracy = round(sum(item["accuracy"] for item in recent_attempt_window) / len(recent_attempt_window), 2) if recent_attempt_window else 0

    history = get_progress_history(db, user_id, 30)
    user = db.get(User, user_id)
    analytics = db.scalar(select(UserSkillAnalytics).where(UserSkillAnalytics.user_id == user_id))

    latest_mock = db.scalar(
        select(MockTestAttempt)
        .where(MockTestAttempt.user_id == user_id)
        .order_by(func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc).desc())
        .limit(1)
    )

    return DashboardOverviewDto(
        totalPracticeAttempts=len(practice_attempts),
        recentAccuracy=recent_accuracy,
        totalStudyMinutes=_get_total_study_minutes(db, user_id),
        pendingReviewCount=db.scalar(select(func.count()).select_from(ReviewQueueItem).where(ReviewQueueItem.user_id == user_id, ReviewQueueItem.status == "pending")) or 0,
        weakestSkill=_get_weakest_skill(db, user_id),
        weakestPart=_get_weakest_part(db, user_id),
        latestMockTest=LatestMockTestDto(
            title=latest_mock.title or "",
            totalScaledScore=latest_mock.total_score or 0,
            listeningScaledScore=latest_mock.listening_score or 0,
            readingScaledScore=latest_mock.reading_score or 0,
            accuracy=float(latest_mock.accuracy_pct),
            submittedAtUtc=latest_mock.submitted_at_utc or latest_mock.created_at_utc,
        )
        if latest_mock
        else None,
        latestDiagnostic=_build_latest_assessment_snapshot(db, user_id, user, analytics),
        recentActiveDays=sum(1 for item in history if item.studyMinutes > 0 or item.attemptsCount > 0),
        streakDays=_calculate_streak_days(history),
    )


def get_progress_summary(db: Session, user_id: int) -> ProgressSummaryDto:
    practice_attempts = db.scalars(select(PracticeAttempt).where(PracticeAttempt.user_id == user_id)).all()
    mock_attempts = db.scalars(select(MockTestAttempt).where(MockTestAttempt.user_id == user_id)).all()

    total_correct_answers = (
        sum(item.correct_count for item in practice_attempts)
        + sum(item.correct_count for item in mock_attempts)
    )
    total_wrong_answers = (
        sum(max(0, item.total_questions - item.correct_count) for item in practice_attempts)
        + sum(max(0, item.total_questions - item.correct_count) for item in mock_attempts)
    )
    total_answers = total_correct_answers + total_wrong_answers

    return ProgressSummaryDto(
        weeklyStudyMinutes=get_progress_history(db, user_id, 7),
        totalAttempts=len(practice_attempts) + len(mock_attempts),
        totalCorrectAnswers=total_correct_answers,
        totalWrongAnswers=total_wrong_answers,
        averageAccuracy=round(total_correct_answers * 100 / total_answers, 2) if total_answers else 0,
        skillProfiles=[
            SkillProfileDto(
                skillCode=item.skill_code,
                skillName=item.skill_name,
                accuracy=float(item.accuracy_pct),
                correctCount=item.correct_count,
                attemptCount=item.attempt_count,
                lastPracticedAtUtc=item.last_practiced_at_utc,
            )
            for item in db.scalars(
                select(UserSkillProfile)
                .where(UserSkillProfile.user_id == user_id)
                .order_by(UserSkillProfile.accuracy_pct, UserSkillProfile.attempt_count.desc())
            ).all()
        ],
        partStats=[
            PartStatDto(
                part=item.part,
                accuracy=float(item.accuracy_pct),
                correctCount=item.correct_count,
                attemptCount=item.attempt_count,
                averageTimeSeconds=item.average_time_seconds,
                updatedAtUtc=item.updated_at_utc,
            )
            for item in db.scalars(select(UserPartStat).where(UserPartStat.user_id == user_id).order_by(UserPartStat.part)).all()
        ],
        recentPracticeAttempts=[
            RecentPracticeAttemptDto(
                id=item.id,
                title=item.title or "",
                subtitle=item.subtitle,
                mode=item.mode or "",
                parts=item.parts or "",
                correctCount=item.correct_count,
                totalQuestions=item.total_questions,
                accuracy=float(item.accuracy_pct),
                timeSpentSeconds=item.time_spent_seconds,
                submittedAtUtc=item.submitted_at_utc or item.created_at_utc,
            )
            for item in db.scalars(
                select(PracticeAttempt)
                .where(PracticeAttempt.user_id == user_id)
                .order_by(func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc).desc())
                .limit(5)
            ).all()
        ],
        recentMockTests=[
            RecentMockTestDto(
                id=item.id,
                title=item.title or "",
                totalScaledScore=item.total_score or 0,
                listeningScaledScore=item.listening_score or 0,
                readingScaledScore=item.reading_score or 0,
                accuracy=float(item.accuracy_pct),
                timeSpentSeconds=item.time_spent_seconds,
                submittedAtUtc=item.submitted_at_utc or item.created_at_utc,
            )
            for item in db.scalars(
                select(MockTestAttempt)
                .where(MockTestAttempt.user_id == user_id)
                .order_by(func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc).desc())
                .limit(5)
            ).all()
        ],
        pendingReviewCount=db.scalar(select(func.count()).select_from(ReviewQueueItem).where(ReviewQueueItem.user_id == user_id, ReviewQueueItem.status == "pending")) or 0,
    )


def get_progress_history(db: Session, user_id: int, days: int = 30) -> list[HistoryPointDto]:
    normalized_days = max(1, min(days, 90))
    from_date = datetime.utcnow().date() - timedelta(days=normalized_days - 1)

    progress_logs = db.scalars(
        select(ProgressLog).where(ProgressLog.user_id == user_id, ProgressLog.created_at_utc >= from_date)
    ).all()

    practice_rows = db.scalars(
        select(PracticeAttempt).where(PracticeAttempt.user_id == user_id, func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc) >= from_date)
    ).all()
    mock_rows = db.scalars(
        select(MockTestAttempt).where(MockTestAttempt.user_id == user_id, func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc) >= from_date)
    ).all()

    log_minutes_by_date: dict[datetime.date, int] = {}
    for row in progress_logs:
        date_key = row.created_at_utc.date()
        log_minutes_by_date[date_key] = log_minutes_by_date.get(date_key, 0) + row.minutes_learned

    attempts_by_date: dict[datetime.date, dict[str, int]] = {}
    for attempt in list(practice_rows) + list(mock_rows):
        date_key = (attempt.submitted_at_utc or attempt.created_at_utc).date()
        bucket = attempts_by_date.setdefault(date_key, {"studyMinutes": 0, "attemptsCount": 0, "correctAnswers": 0, "wrongAnswers": 0})
        bucket["studyMinutes"] += int((attempt.time_spent_seconds + 59) // 60)
        bucket["attemptsCount"] += 1
        bucket["correctAnswers"] += attempt.correct_count
        bucket["wrongAnswers"] += max(0, attempt.total_questions - attempt.correct_count)

    result: list[HistoryPointDto] = []
    for index in range(normalized_days):
        date_key = from_date + timedelta(days=index)
        attempt_data = attempts_by_date.get(date_key, {"studyMinutes": 0, "attemptsCount": 0, "correctAnswers": 0, "wrongAnswers": 0})
        study_minutes = log_minutes_by_date.get(date_key) or attempt_data["studyMinutes"]
        answers_count = attempt_data["correctAnswers"] + attempt_data["wrongAnswers"]
        result.append(
            HistoryPointDto(
                date=date_key.strftime("%Y-%m-%d"),
                studyMinutes=study_minutes,
                attemptsCount=attempt_data["attemptsCount"],
                correctAnswers=attempt_data["correctAnswers"],
                wrongAnswers=attempt_data["wrongAnswers"],
                accuracy=round(attempt_data["correctAnswers"] * 100 / answers_count, 2) if answers_count else 0,
            )
        )
    return result


def get_review_summary(db: Session, user_id: int) -> ReviewSummaryDto:
    review_items = db.scalars(select(ReviewQueueItem).where(ReviewQueueItem.user_id == user_id).order_by(ReviewQueueItem.added_at_utc.desc())).all()
    top_weak_groups: dict[str, int] = {}
    for item in review_items:
        if item.status == "pending" and item.skill and item.skill.strip():
            key = item.skill.strip()
            top_weak_groups[key] = top_weak_groups.get(key, 0) + 1
    top_weak_skills = [
        WeakMetricDto(skill=skill, accuracy=0, attemptCount=count)
        for skill, count in sorted(top_weak_groups.items(), key=lambda pair: pair[1], reverse=True)[:5]
    ]
    return ReviewSummaryDto(
        pendingCount=sum(1 for item in review_items if item.status == "pending"),
        reviewedCount=sum(1 for item in review_items if item.status != "pending"),
        topWeakSkills=top_weak_skills,
        recentReviewItems=[
            ReviewQueueItemDto(
                id=item.id,
                questionId=item.question_id,
                part=item.part,
                skill=item.skill,
                status=item.status,
                sourceAttemptType=item.source_attempt_type,
                sourceAttemptId=item.source_attempt_id,
                note=item.note,
                addedAtUtc=item.added_at_utc,
                reviewedAtUtc=item.reviewed_at_utc,
            )
            for item in review_items[:8]
        ],
      )


def get_review_item_detail(db: Session, user_id: int, review_item_id: int) -> ReviewQuestionDetailDto | None:
    item = db.scalar(select(ReviewQueueItem).where(ReviewQueueItem.id == review_item_id, ReviewQueueItem.user_id == user_id))
    if item is None:
        return None

    question = db.scalar(
        select(ToeicQuestion)
        .options(
            joinedload(ToeicQuestion.passage).selectinload(ToeicPassage.assets),
            selectinload(ToeicQuestion.options),
            selectinload(ToeicQuestion.assets),
        )
        .where(ToeicQuestion.id == item.question_id)
    )
    source_answer = _get_review_source_answer(db, item)
    option_texts = _get_question_option_texts(question)
    correct_index = _resolve_question_correct_index(question)
    correct_answer = _resolve_answer_text(correct_index, option_texts)
    user_answer_index = source_answer.selected_answer_index if source_answer else None
    user_answer = _resolve_answer_text(user_answer_index, option_texts)

    return ReviewQuestionDetailDto(
        id=item.id,
        queueId=item.id,
        questionId=item.question_id,
        question=question.question_text if question else f"Question #{item.question_id}",
        options=option_texts,
        userAnswer=user_answer,
        userAnswerIndex=user_answer_index,
        correctAnswer=correct_answer or (question.correct_option_key if question else None),
        correctAnswerIndex=correct_index,
        isCorrect=bool(source_answer.is_correct) if source_answer else False,
        explanation=(source_answer.explanation if source_answer and source_answer.explanation else None) or (question.explanation if question else None) or item.note,
        skill=(source_answer.skill if source_answer and source_answer.skill else None) or item.skill or (question.topic if question else None) or (question.skill_code if question else None) or "TOEIC review",
        subskill=question.subskill_code if question else None,
        part=item.part or (question.part if question else 0),
        difficulty=question.difficulty or "mixed" if question else "mixed",
        status=item.status,
        sourceAttemptType=item.source_attempt_type,
        sourceAttemptId=item.source_attempt_id,
        note=item.note,
        addedAtUtc=item.added_at_utc,
        reviewedAtUtc=item.reviewed_at_utc,
        passageTitle=question.passage.title if question and question.passage else None,
        passageText=question.passage.passage_text if question and question.passage else None,
        audioUrl=_resolve_question_asset_path(question, "audio") if question else None,
        imageUrl=_resolve_question_asset_path(question, "image") if question else None,
        graphicUrl=_resolve_question_asset_path(question, "graphic") if question else None,
    )


def mark_review_item_reviewed(db: Session, user_id: int, review_item_id: int) -> ReviewQuestionDetailDto | None:
    item = db.scalar(select(ReviewQueueItem).where(ReviewQueueItem.id == review_item_id, ReviewQueueItem.user_id == user_id))
    if item is None:
        return None
    if item.status != "reviewed":
        item.status = "reviewed"
        item.reviewed_at_utc = datetime.utcnow()
        db.commit()
    return get_review_item_detail(db, user_id, review_item_id)


def _get_review_source_answer(db: Session, item: ReviewQueueItem) -> PracticeAttemptAnswer | MockTestAttemptAnswer | None:
    if not item.source_attempt_id:
        return None
    source_type = (item.source_attempt_type or "").strip().lower()
    if source_type == "practice":
        return db.scalar(
            select(PracticeAttemptAnswer)
            .join(PracticeAttempt, PracticeAttempt.id == PracticeAttemptAnswer.practice_attempt_id)
            .where(
                PracticeAttempt.user_id == item.user_id,
                PracticeAttempt.id == item.source_attempt_id,
                PracticeAttemptAnswer.question_id == item.question_id,
            )
        )
    if source_type == "mock-test":
        return db.scalar(
            select(MockTestAttemptAnswer)
            .join(MockTestAttempt, MockTestAttempt.id == MockTestAttemptAnswer.mock_test_attempt_id)
            .where(
                MockTestAttempt.user_id == item.user_id,
                MockTestAttempt.id == item.source_attempt_id,
                MockTestAttemptAnswer.question_id == item.question_id,
            )
        )
    return None


def _get_question_option_texts(question: ToeicQuestion | None) -> list[str]:
    if question is None:
        return []
    return [
        item.option_text
        for item in sorted(question.options, key=lambda value: (value.sort_order, value.option_key))
    ]


def _resolve_question_correct_index(question: ToeicQuestion | None) -> int | None:
    if question is None or not question.correct_option_key:
        return None
    key = question.correct_option_key.strip().upper()
    if not key:
        return None
    return ord(key[0]) - ord("A")


def _resolve_answer_text(answer_index: int | None, options: list[str]) -> str | None:
    if answer_index is None or answer_index < 0 or answer_index >= len(options):
        return None
    return options[answer_index]


def _resolve_question_asset_path(question: ToeicQuestion, asset_type: str) -> str | None:
    question_asset = next(
        (
            item.relative_path
            for item in sorted(question.assets, key=lambda value: value.sort_order)
            if item.asset_type.lower() == asset_type.lower() and item.relative_path
        ),
        None,
    )
    if question_asset:
        return question_asset
    if question.passage:
        passage_asset = next(
            (
                item.relative_path
                for item in sorted(question.passage.assets, key=lambda value: value.sort_order)
                if item.asset_type.lower() == asset_type.lower() and item.relative_path
            ),
            None,
        )
        if passage_asset:
            return passage_asset
        if asset_type == "audio":
            return question.passage.audio_path or question.audio_url
        if asset_type in {"graphic", "image"}:
            return question.passage.image_path
    return question.audio_url if asset_type == "audio" else None


def get_profile_summary(db: Session, user_id: int) -> ProfileSummaryDto | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    analytics = db.scalar(select(UserSkillAnalytics).where(UserSkillAnalytics.user_id == user_id))
    weak_skills = parse_string_list(user.weak_skills_json)
    if not weak_skills:
        weak_skills = [item.skill_name or item.skill_code for item in db.scalars(select(UserSkillProfile).where(UserSkillProfile.user_id == user_id).order_by(UserSkillProfile.accuracy_pct, UserSkillProfile.attempt_count.desc()).limit(5)).all()]
    latest_assessment = _build_latest_assessment_snapshot(db, user_id, user, analytics)
    return ProfileSummaryDto(
        currentScore=latest_assessment.estimatedScore if latest_assessment else user.current_score,
        targetScore=user.target_score,
        weakSkills=weak_skills,
        latestDiagnostic=latest_assessment,
        pendingReviewCount=db.scalar(select(func.count()).select_from(ReviewQueueItem).where(ReviewQueueItem.user_id == user_id, ReviewQueueItem.status == "pending")) or 0,
    )


def _get_total_study_minutes(db: Session, user_id: int) -> int:
    progress_minutes = db.scalar(select(func.sum(ProgressLog.minutes_learned)).where(ProgressLog.user_id == user_id)) or 0
    if progress_minutes > 0:
        return int(progress_minutes)
    practice_seconds = db.scalar(select(func.sum(PracticeAttempt.time_spent_seconds)).where(PracticeAttempt.user_id == user_id)) or 0
    mock_seconds = db.scalar(select(func.sum(MockTestAttempt.time_spent_seconds)).where(MockTestAttempt.user_id == user_id)) or 0
    return int((practice_seconds + mock_seconds + 59) // 60)


def _get_weakest_skill(db: Session, user_id: int) -> WeakMetricDto | None:
    profile = db.scalar(
        select(UserSkillProfile)
        .where(UserSkillProfile.user_id == user_id, UserSkillProfile.attempt_count > 0)
        .order_by(UserSkillProfile.accuracy_pct, UserSkillProfile.attempt_count.desc())
        .limit(1)
    )
    if profile:
        return WeakMetricDto(skill=profile.skill_name or profile.skill_code, accuracy=float(profile.accuracy_pct), attemptCount=profile.attempt_count)

    fallback_rows = db.execute(
        select(PracticeAttemptAnswer.skill, PracticeAttemptAnswer.is_correct)
        .join(PracticeAttempt, PracticeAttempt.id == PracticeAttemptAnswer.practice_attempt_id)
        .where(PracticeAttempt.user_id == user_id, PracticeAttemptAnswer.skill.is_not(None))
    ).all() + db.execute(
        select(MockTestAttemptAnswer.skill, MockTestAttemptAnswer.is_correct)
        .join(MockTestAttempt, MockTestAttempt.id == MockTestAttemptAnswer.mock_test_attempt_id)
        .where(MockTestAttempt.user_id == user_id, MockTestAttemptAnswer.skill.is_not(None))
    ).all()
    grouped: dict[str, list[bool]] = {}
    for skill, is_correct in fallback_rows:
        if not skill or not skill.strip():
            continue
        key = skill.strip()
        grouped.setdefault(key, []).append(is_correct)
    if not grouped:
        return None
    data = [
        WeakMetricDto(skill=skill, attemptCount=len(values), accuracy=round(sum(1 for value in values if value) * 100 / len(values), 2))
        for skill, values in grouped.items()
    ]
    return sorted(data, key=lambda item: (item.accuracy, -item.attemptCount))[0]


def _get_weakest_part(db: Session, user_id: int) -> WeakPartDto | None:
    part = db.scalar(
        select(UserPartStat)
        .where(UserPartStat.user_id == user_id, UserPartStat.attempt_count > 0)
        .order_by(UserPartStat.accuracy_pct, UserPartStat.attempt_count.desc())
        .limit(1)
    )
    if part:
        return WeakPartDto(part=part.part, accuracy=float(part.accuracy_pct), attemptCount=part.attempt_count)

    fallback_rows = db.execute(
        select(PracticeAttemptAnswer.part, PracticeAttemptAnswer.is_correct)
        .join(PracticeAttempt, PracticeAttempt.id == PracticeAttemptAnswer.practice_attempt_id)
        .where(PracticeAttempt.user_id == user_id)
    ).all() + db.execute(
        select(MockTestAttemptAnswer.part, MockTestAttemptAnswer.is_correct)
        .join(MockTestAttempt, MockTestAttempt.id == MockTestAttemptAnswer.mock_test_attempt_id)
        .where(MockTestAttempt.user_id == user_id)
    ).all()
    grouped: dict[int, list[bool]] = {}
    for part_value, is_correct in fallback_rows:
        if part_value and part_value > 0:
            grouped.setdefault(part_value, []).append(is_correct)
    if not grouped:
        return None
    data = [
        WeakPartDto(part=part_value, attemptCount=len(values), accuracy=round(sum(1 for value in values if value) * 100 / len(values), 2))
        for part_value, values in grouped.items()
    ]
    return sorted(data, key=lambda item: (item.accuracy, -item.attemptCount))[0]


def _build_latest_assessment_snapshot(db: Session, user_id: int, user: User | None, analytics_entity: UserSkillAnalytics | None) -> LatestDiagnosticDto | None:
    latest_mock = db.scalar(
        select(MockTestAttempt)
        .where(MockTestAttempt.user_id == user_id)
        .order_by(func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc).desc())
        .limit(1)
    )
    analytics = to_dto(analytics_entity)
    estimated_score = latest_mock.total_score if latest_mock else (user.current_score if user else 0)
    has_assessment_data = (
        latest_mock is not None
        or bool(estimated_score)
        or bool(analytics.topWeakSubskills)
        or analytics.updatedAtUtc is not None
    )
    if not has_assessment_data:
        return None
    return LatestDiagnosticDto(
        estimatedScore=estimated_score or 0,
        estimatedLevel=_resolve_estimated_level(estimated_score or 0),
        levelRange=_resolve_estimated_range(estimated_score or 0),
        theta=None,
        submittedAtUtc=(latest_mock.submitted_at_utc or latest_mock.created_at_utc) if latest_mock else analytics.updatedAtUtc,
        weakSubskills=analytics.topWeakSubskills,
    )


def _calculate_streak_days(history: list[HistoryPointDto]) -> int:
    streak = 0
    for item in sorted(history, key=lambda row: row.date, reverse=True):
        if item.studyMinutes <= 0 and item.attemptsCount <= 0:
            break
        streak += 1
    return streak


def _resolve_estimated_level(score: int) -> str:
    if score <= 450:
        return "Foundation"
    if score <= 750:
        return "Developing"
    return "Advanced"


def _resolve_estimated_range(score: int) -> str:
    if score <= 450:
        return "10-450"
    if score <= 750:
        return "455-750"
    return "755-990"
