from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import MockTestAttempt, PracticeAttempt, PracticeAttemptAnswer, User, UserPartStat, UserSkillProfile
from app.schemas.attempts import AttemptAssetDto, AttemptPartBreakdownDto, AttemptResultDto, AttemptResultQuestionDto, AttemptSkillBreakdownDto, AttemptWeakAreaDto, SavePracticeAttemptAnswerRequest, SavePracticeAttemptRequest
from app.schemas.roadmap import RoadmapSuggestedSetCriteriaDto
from app.schemas.toeic import ToeicRunnerPassageDto, ToeicRunnerQuestionDto
from app.schemas.weekly_check import WeeklyCheckCurrentDto, WeeklyCheckSubmitRequest, WeeklyCheckSubmitResponse
from app.services.attempts import get_practice_attempt_result, save_practice_attempt
from app.services.skill_analytics import analyze_latest_performance, get_default_subskills, to_dto, to_title
from app.services.toeic import build_question_lookup_key, get_question_lookup, get_questions_for_suggested_set


DEFAULT_QUESTION_COUNT = 50
DEFAULT_ESTIMATED_MINUTES = 45


def get_current_weekly_check(db: Session, user_id: int) -> WeeklyCheckCurrentDto:
    analytics = _resolve_analytics(db, user_id)
    questions = _build_weekly_questions(db, user_id, analytics, DEFAULT_QUESTION_COUNT)
    return WeeklyCheckCurrentDto(
        weeklyCheckId=_build_weekly_check_id(user_id, analytics),
        title="Weekly Check",
        description=_build_description(analytics, len(questions)),
        totalQuestions=len(questions),
        estimatedMinutes=DEFAULT_ESTIMATED_MINUTES,
        focusSkill=analytics.focusSkillCode,
        focusSkillLabel=analytics.focusSkillLabel,
        focusPart=analytics.weakestPart,
        sourceAnalytics=analytics.sourceAnalytics,
        difficulty=analytics.difficulty,
        topWeakSubskills=list(analytics.topWeakSubskills),
        questions=questions,
    )


def submit_weekly_check(db: Session, user_id: int, request: WeeklyCheckSubmitRequest) -> WeeklyCheckSubmitResponse:
    current = get_current_weekly_check(db, user_id)
    answer_lookup = {build_question_lookup_key(item.part, item.questionId): item for item in request.answers}
    attempt_answers: list[SavePracticeAttemptAnswerRequest] = []

    for index, question in enumerate(current.questions):
        submitted_answer = answer_lookup.get(build_question_lookup_key(question.part, question.id))
        selected_answer_index = submitted_answer.selectedAnswerIndex if submitted_answer else None
        correct_answer_index = question.correctAnswerIndex
        is_correct = selected_answer_index is not None and correct_answer_index is not None and selected_answer_index == correct_answer_index
        attempt_answers.append(
            SavePracticeAttemptAnswerRequest(
                questionId=question.id,
                questionNumber=index + 1,
                part=question.part,
                test=question.test,
                section=question.section,
                partLabel=question.partLabel,
                skill=question.skill,
                subskill=question.subskill,
                type=question.type,
                groupId=question.groupId,
                question=question.question,
                options=list(question.options),
                selectedAnswerIndex=selected_answer_index,
                selectedAnswerText=_resolve_selected_answer_text(selected_answer_index, question.options),
                correctAnswerIndex=correct_answer_index,
                correctAnswer=_resolve_choice_label(correct_answer_index),
                correctAnswerText=_resolve_selected_answer_text(correct_answer_index, question.options),
                isCorrect=is_correct,
                isFlagged=submitted_answer.isFlagged if submitted_answer else False,
                explanation=question.explanation,
                audio=AttemptAssetDto(path=question.audio.path) if question.audio else None,
                graphic=AttemptAssetDto(path=question.graphic.path) if question.graphic else None,
                image=AttemptAssetDto(path=question.image.path) if question.image else None,
            )
        )

    total_questions = len(attempt_answers)
    answered_count = sum(1 for item in attempt_answers if item.selectedAnswerIndex is not None)
    correct_count = sum(1 for item in attempt_answers if item.isCorrect)
    accuracy_pct = round(correct_count * 100 / total_questions, 2) if total_questions else 0
    submitted_at_utc = datetime.utcnow()
    started_at_utc = request.startedAtUtc or submitted_at_utc
    save_request = SavePracticeAttemptRequest(
        source="weeklycheck",
        title=request.title.strip() if request.title and request.title.strip() else current.title,
        subtitle=request.description.strip() if request.description and request.description.strip() else current.description,
        mode="weekly-check",
        parts=",".join(str(value) for value in sorted({item.part for item in attempt_answers})),
        difficulty=current.difficulty,
        totalQuestions=total_questions,
        answeredCount=answered_count,
        correctCount=correct_count,
        accuracyPct=accuracy_pct,
        score=None,
        timeSpentSeconds=max(request.timeSpentSeconds, 0),
        startedAtUtc=started_at_utc,
        submittedAtUtc=submitted_at_utc,
        answers=attempt_answers,
    )
    persisted = save_practice_attempt(db, user_id, save_request)
    return WeeklyCheckSubmitResponse(
        attemptId=persisted.attemptId,
        attemptType="weekly_check",
        reviewQueuedCount=persisted.reviewQueuedCount,
        skillStatsUpdated=persisted.skillStatsUpdated,
        partStatsUpdated=persisted.partStatsUpdated,
        result=persisted.result,
    )


def get_weekly_check_result(db: Session, user_id: int, attempt_id: int) -> AttemptResultDto | None:
    attempt = db.scalar(
        select(PracticeAttempt)
        .options(selectinload(PracticeAttempt.answers))
        .where(PracticeAttempt.id == attempt_id, PracticeAttempt.user_id == user_id, PracticeAttempt.mode == "weekly-check")
    )
    if attempt is None:
        return None
    hydrated = get_practice_attempt_result(db, user_id, attempt_id)
    if hydrated is not None:
        hydrated.attemptType = "weekly_check"
        hydrated.title = hydrated.title or "Weekly Check"
        return hydrated
    question_lookup = get_question_lookup(db)
    questions = [_build_result_question(answer, question_lookup) for answer in sorted(attempt.answers, key=lambda item: (item.question_number, item.question_id))]
    total_questions = attempt.total_questions or len(questions)
    unanswered_count = max(total_questions - attempt.answered_count, 0)
    wrong_count = max(attempt.answered_count - attempt.correct_count, 0)
    return AttemptResultDto(
        attemptId=attempt.id,
        attemptType="weekly_check",
        title=attempt.title or "Weekly Check",
        totalQuestions=total_questions,
        correctCount=attempt.correct_count,
        wrongCount=wrong_count,
        unansweredCount=unanswered_count,
        accuracyPct=float(attempt.accuracy_pct),
        startedAt=attempt.started_at_utc,
        submittedAt=attempt.submitted_at_utc or attempt.created_at_utc,
        durationSeconds=attempt.time_spent_seconds,
        durationMinutes=int((attempt.time_spent_seconds + 59) // 60) if attempt.time_spent_seconds > 0 else None,
        skillBreakdown=_build_skill_breakdown(questions),
        partBreakdown=_build_part_breakdown(questions),
        weakAreas=_build_weak_areas(questions),
        questions=questions,
    )


def _build_weekly_questions(db: Session, user_id: int, analytics: "_WeeklyAnalyticsContext", total_questions: int) -> list[ToeicRunnerQuestionDto]:
    normalized_count = min(max(total_questions, 30), 50)
    focus_count = round(normalized_count * 0.60) if analytics.hasFocus else 0
    part_count = round(normalized_count * 0.25) if analytics.weakestPart else 0
    mixed_count = max(normalized_count - focus_count - part_count, 0)

    weekly_seed = _build_weekly_seed(user_id, analytics)
    result: list[ToeicRunnerQuestionDto] = []
    seen: set[str] = set()

    if focus_count > 0:
        focus_criteria = RoadmapSuggestedSetCriteriaDto(
            strategy="weekly_focus",
            focusSkill=analytics.focusSkillCode,
            focusPart=analytics.weakestPart,
            includeParts=_resolve_skill_parts(analytics.focusSkillCode, analytics.weakestPart),
            subskills=analytics.topWeakSubskills[:3],
            difficulty=analytics.difficulty,
            questionCount=focus_count,
        )
        _add_unique_questions(result, seen, _order_deterministically(get_questions_for_suggested_set(db, focus_criteria), f"{weekly_seed}:focus"), focus_count)

    if part_count > 0 and analytics.weakestPart:
        part_criteria = RoadmapSuggestedSetCriteriaDto(
            strategy="weekly_part",
            focusSkill=analytics.focusSkillCode,
            focusPart=analytics.weakestPart,
            includeParts=[analytics.weakestPart],
            subskills=analytics.topWeakSubskills[:2],
            difficulty=analytics.difficulty,
            questionCount=part_count,
        )
        _add_unique_questions(result, seen, _order_deterministically(get_questions_for_suggested_set(db, part_criteria), f"{weekly_seed}:part"), focus_count + part_count)

    mixed_criteria = RoadmapSuggestedSetCriteriaDto(
        strategy="weekly_mixed_review",
        focusSkill=analytics.focusSkillCode,
        focusPart=analytics.weakestPart,
        includeParts=_resolve_mixed_parts(analytics.focusSkillCode, analytics.weakestPart),
        subskills=analytics.topWeakSubskills[:2],
        difficulty="mixed",
        questionCount=max(mixed_count, 10),
    )
    _add_unique_questions(result, seen, _order_deterministically(get_questions_for_suggested_set(db, mixed_criteria), f"{weekly_seed}:mixed"), normalized_count)

    if len(result) < normalized_count:
        fill_criteria = RoadmapSuggestedSetCriteriaDto(strategy="weekly_fill", includeParts=[1, 2, 3, 4, 5, 6, 7], difficulty="mixed", questionCount=normalized_count * 2)
        _add_unique_questions(result, seen, _order_deterministically(get_questions_for_suggested_set(db, fill_criteria), f"{weekly_seed}:fill"), normalized_count)

    final_questions = [ToeicRunnerQuestionDto.model_validate(item.model_dump()) for item in result[:normalized_count]]
    for index, question in enumerate(final_questions, start=1):
        question.questionNumber = index
    return final_questions


def _resolve_analytics(db: Session, user_id: int) -> "_WeeklyAnalyticsContext":
    user = db.get(User, user_id)
    refreshed_analytics = analyze_latest_performance(db, user_id)
    refreshed_dto = to_dto(refreshed_analytics)
    reference_score = _resolve_reference_score(db, user_id, user.current_score if user else None)
    if refreshed_dto.weakestSkill or refreshed_dto.weakestPart is not None:
        return _build_analytics_context(refreshed_dto.weakestSkill, refreshed_dto.weakestSkillLabel, refreshed_dto.weakestPart, refreshed_dto.topWeakSubskills, "performance_snapshot", _resolve_difficulty(reference_score), reference_score)

    skill_profiles = db.scalars(
        select(UserSkillProfile)
        .where(UserSkillProfile.user_id == user_id, UserSkillProfile.attempt_count > 0)
        .order_by(UserSkillProfile.accuracy_pct, UserSkillProfile.attempt_count.desc())
    ).all()
    part_stats = db.scalars(
        select(UserPartStat)
        .where(UserPartStat.user_id == user_id, UserPartStat.attempt_count > 0)
        .order_by(UserPartStat.accuracy_pct, UserPartStat.attempt_count.desc())
    ).all()
    if skill_profiles or part_stats:
        weakest_skill = skill_profiles[0] if skill_profiles else None
        weakest_part = part_stats[0] if part_stats else None
        return _build_analytics_context(
            weakest_skill.skill_code if weakest_skill else "",
            weakest_skill.skill_name if weakest_skill else "",
            weakest_part.part if weakest_part else None,
            get_default_subskills(weakest_skill.skill_code if weakest_skill else None),
            "practice_history",
            _resolve_difficulty(reference_score),
            reference_score,
        )
    return _build_analytics_context("", "Mixed TOEIC Review", None, [], "mixed_fallback", "mixed", reference_score)


def _resolve_reference_score(db: Session, user_id: int, fallback_score: int | None) -> int | None:
    latest_mock_score = db.scalar(select(MockTestAttempt.total_score).where(MockTestAttempt.user_id == user_id).order_by(func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc).desc()).limit(1))
    if latest_mock_score:
        return latest_mock_score
    latest_practice_score = db.scalar(select(PracticeAttempt.score).where(PracticeAttempt.user_id == user_id, PracticeAttempt.score.is_not(None)).order_by(func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc).desc()).limit(1))
    return latest_practice_score if latest_practice_score is not None else fallback_score


def _build_analytics_context(focus_skill_code: str | None, focus_skill_label: str | None, weakest_part: int | None, top_weak_subskills: list[str] | None, source_analytics: str, difficulty: str, current_score: int | None) -> "_WeeklyAnalyticsContext":
    resolved_skill_code = (focus_skill_code or "").strip()
    resolved_label = (focus_skill_label or "").strip() or (to_title(resolved_skill_code) if resolved_skill_code else "Mixed TOEIC Review")
    return _WeeklyAnalyticsContext(
        focusSkillCode=resolved_skill_code,
        focusSkillLabel=resolved_label,
        weakestPart=weakest_part,
        topWeakSubskills=list(dict.fromkeys(item.strip() for item in (top_weak_subskills or []) if item and item.strip())),
        sourceAnalytics=source_analytics,
        difficulty=difficulty,
        currentScore=current_score,
    )


def _build_description(analytics: "_WeeklyAnalyticsContext", question_count: int) -> str:
    if not analytics.hasFocus:
        return f"{question_count} mixed TOEIC questions built from the current question bank."
    segments = [f"{question_count} questions focused on {analytics.focusSkillLabel}"]
    if analytics.weakestPart:
        segments.append(f"Part {analytics.weakestPart}")
    if analytics.topWeakSubskills:
        segments.append(f"subskills: {', '.join(to_title(item) for item in analytics.topWeakSubskills[:3])}")
    segments.append(f"source: {analytics.sourceAnalytics}")
    return " | ".join(segments)


def _build_weekly_check_id(user_id: int, analytics: "_WeeklyAnalyticsContext") -> str:
    now = datetime.utcnow().isocalendar()
    focus_skill = analytics.focusSkillCode.lower() if analytics.focusSkillCode else "mixed"
    focus_part = str(analytics.weakestPart) if analytics.weakestPart else "mixed"
    return f"weekly-check-{now.year}-w{now.week}-u{user_id}-{focus_skill}-p{focus_part}"


def _build_weekly_seed(user_id: int, analytics: "_WeeklyAnalyticsContext") -> str:
    return f"{_build_weekly_check_id(user_id, analytics)}-{analytics.difficulty}"


def _order_deterministically(questions: list[ToeicRunnerQuestionDto], seed: str) -> list[ToeicRunnerQuestionDto]:
    def stable_hash(question: ToeicRunnerQuestionDto) -> int:
        raw = f"{seed}:{question.part}:{question.id}:{question.test}:{question.questionNumber}"
        return int.from_bytes(sha256(raw.encode("utf-8")).digest()[:4], "little")

    return sorted(questions, key=lambda item: (stable_hash(item), item.part, item.test, item.questionNumber))


def _add_unique_questions(destination: list[ToeicRunnerQuestionDto], seen: set[str], source: list[ToeicRunnerQuestionDto], max_count: int) -> None:
    for question in source:
        if len(destination) >= max_count:
            break
        key = build_question_lookup_key(question.part, question.id)
        if key in seen:
            continue
        seen.add(key)
        destination.append(question)


def _resolve_difficulty(score: int | None) -> str:
    if score is None:
        return "mixed"
    if score <= 450:
        return "easy"
    if score <= 750:
        return "medium"
    return "hard"


def _resolve_skill_parts(focus_skill: str, weakest_part: int | None) -> list[int]:
    if weakest_part and weakest_part > 0:
        return [weakest_part]
    return {
        "listening_response": [2],
        "listening_inference": [3, 4],
        "listening_main_idea": [3, 4],
        "listening_detail": [1, 3, 4],
        "grammar": [5],
        "vocabulary": [5, 6],
        "reading_context": [6],
        "reading_detail": [7],
        "reading_inference": [7],
    }.get((focus_skill or "").strip().lower(), [1, 2, 3, 4, 5, 6, 7])


def _resolve_mixed_parts(focus_skill: str, weakest_part: int | None) -> list[int]:
    result = _resolve_skill_parts(focus_skill, None)
    if weakest_part and weakest_part > 0:
        result.append(weakest_part)
        if weakest_part == 3:
            result.append(4)
        elif weakest_part == 4:
            result.append(3)
        elif weakest_part == 5:
            result.extend([6, 7])
    return sorted({value for value in result if 1 <= value <= 7})


def _build_result_question(answer: PracticeAttemptAnswer, question_lookup: dict[str, ToeicRunnerQuestionDto]) -> AttemptResultQuestionDto:
    source_question = question_lookup.get(build_question_lookup_key(answer.part, answer.question_id))
    options = list(source_question.options) if source_question else []
    selected_answer_text = _resolve_selected_answer_text(answer.selected_answer_index, options)
    correct_answer_text = _resolve_selected_answer_text(answer.correct_answer_index, options)
    return AttemptResultQuestionDto(
        questionId=answer.question_id,
        questionNumber=answer.question_number,
        test=source_question.test if source_question else 0,
        part=answer.part,
        section=source_question.section if source_question else ("Listening" if answer.part <= 4 else "Reading"),
        partLabel=source_question.partLabel if source_question else None,
        type=source_question.type if source_question else None,
        groupId=source_question.groupId if source_question else None,
        skill=source_question.skill if source_question and source_question.skill else (answer.skill or "general"),
        subskill=source_question.subskill if source_question else None,
        question=source_question.question if source_question else f"Question {answer.question_number}",
        options=options,
        userAnswer=_resolve_answer_label(answer.selected_answer_index, selected_answer_text),
        userAnswerIndex=answer.selected_answer_index,
        correctAnswer=_resolve_answer_label(answer.correct_answer_index, correct_answer_text),
        correctAnswerIndex=answer.correct_answer_index,
        isCorrect=answer.is_correct,
        explanation=_build_explanation((source_question.explanation if source_question else None) or answer.explanation, answer.selected_answer_index, answer.correct_answer_index, selected_answer_text, correct_answer_text),
        audio=AttemptAssetDto(path=source_question.audio.path) if source_question and source_question.audio else None,
        graphic=AttemptAssetDto(path=source_question.graphic.path) if source_question and source_question.graphic else None,
        image=AttemptAssetDto(path=source_question.image.path) if source_question and source_question.image else None,
    )


def _build_skill_breakdown(questions: list[AttemptResultQuestionDto]) -> list[AttemptSkillBreakdownDto]:
    grouped: dict[str, list[AttemptResultQuestionDto]] = {}
    for question in questions:
        key = question.skill.strip() if question.skill.strip() else "general"
        grouped.setdefault(key, []).append(question)
    data = []
    for key, group in grouped.items():
        total = len(group)
        correct = sum(1 for item in group if item.isCorrect)
        data.append(AttemptSkillBreakdownDto(skill=key, total=total, correct=correct, accuracyPct=round(correct * 100 / total, 2) if total else 0))
    return sorted(data, key=lambda item: (item.accuracyPct, -item.total))


def _build_part_breakdown(questions: list[AttemptResultQuestionDto]) -> list[AttemptPartBreakdownDto]:
    grouped: dict[int, list[AttemptResultQuestionDto]] = {}
    for question in questions:
        if question.part > 0:
            grouped.setdefault(question.part, []).append(question)
    data = []
    for part, group in grouped.items():
        total = len(group)
        correct = sum(1 for item in group if item.isCorrect)
        data.append(AttemptPartBreakdownDto(part=part, total=total, correct=correct, accuracyPct=round(correct * 100 / total, 2) if total else 0))
    return sorted(data, key=lambda item: item.part)


def _build_weak_areas(questions: list[AttemptResultQuestionDto]) -> list[AttemptWeakAreaDto]:
    result: list[AttemptWeakAreaDto] = []
    weakest_skill = _get_weak_area_seed({question.skill.strip() if question.skill.strip() else "general": [item for item in questions if (item.skill.strip() if item.skill.strip() else "general") == (question.skill.strip() if question.skill.strip() else "general")] for question in questions})
    if weakest_skill:
        result.append(AttemptWeakAreaDto(type="skill", label=weakest_skill.label, accuracyPct=weakest_skill.accuracyPct, total=weakest_skill.total, correct=weakest_skill.correct, suggestion=f"Review more questions from {weakest_skill.label} to raise weekly accuracy."))
    subskill_groups = {question.subskill.strip(): [item for item in questions if item.subskill and item.subskill.strip() == question.subskill.strip()] for question in questions if question.subskill and question.subskill.strip()}
    weakest_subskill = _get_weak_area_seed(subskill_groups)
    if weakest_subskill:
        result.append(AttemptWeakAreaDto(type="subskill", label=weakest_subskill.label, accuracyPct=weakest_subskill.accuracyPct, total=weakest_subskill.total, correct=weakest_subskill.correct, suggestion=f"Focus next practice on {weakest_subskill.label} patterns."))
    part_groups = {f"Part {question.part}": [item for item in questions if item.part == question.part] for question in questions if question.part > 0}
    weakest_part = _get_weak_area_seed(part_groups)
    if weakest_part:
        result.append(AttemptWeakAreaDto(type="part", label=weakest_part.label, accuracyPct=weakest_part.accuracyPct, total=weakest_part.total, correct=weakest_part.correct, suggestion=f"Run a follow-up practice set for {weakest_part.label} this week."))
    return result


def _get_weak_area_seed(groups: dict[str, list[AttemptResultQuestionDto]]) -> "_WeakAreaSeed | None":
    if not groups:
        return None
    candidates = []
    for label, group in groups.items():
        total = len(group)
        correct = sum(1 for item in group if item.isCorrect)
        candidates.append(_WeakAreaSeed(label=label, total=total, correct=correct, accuracyPct=round(correct * 100 / total, 2) if total else 0))
    return sorted(candidates, key=lambda item: (item.accuracyPct, -item.total))[0]


def _resolve_selected_answer_text(answer_index: int | None, options: list[str]) -> str | None:
    if answer_index is None or answer_index < 0 or answer_index >= len(options):
        return None
    return options[answer_index]


def _resolve_choice_label(answer_index: int | None) -> str | None:
    if answer_index is None or answer_index < 0:
        return None
    return chr(ord("A") + answer_index)


def _resolve_answer_label(answer_index: int | None, answer_text: str | None) -> str | None:
    if not answer_text:
        return None
    prefix = _resolve_choice_label(answer_index)
    return answer_text if prefix is None else f"{prefix}. {answer_text}"


def _build_explanation(explanation: str | None, selected_answer_index: int | None, correct_answer_index: int | None, selected_answer_text: str | None, correct_answer_text: str | None) -> str:
    if explanation and explanation.strip():
        return explanation.strip()
    selected = _resolve_answer_label(selected_answer_index, selected_answer_text)
    correct = _resolve_answer_label(correct_answer_index, correct_answer_text)
    if selected_answer_index is None:
        return "You skipped this question." if correct is None else f"You skipped this question. The correct answer is {correct}."
    if selected_answer_index == correct_answer_index:
        return "You selected the correct answer." if correct is None else f"You selected the correct answer {correct}."
    return "Detailed explanation is not available for this question." if selected is None or correct is None else f"You selected {selected}. The correct answer is {correct}."


@dataclass
class _WeeklyAnalyticsContext:
    focusSkillCode: str
    focusSkillLabel: str
    weakestPart: int | None
    topWeakSubskills: list[str]
    sourceAnalytics: str
    difficulty: str
    currentScore: int | None

    @property
    def hasFocus(self) -> bool:
        return bool(self.focusSkillCode.strip()) or self.weakestPart is not None


@dataclass
class _WeakAreaSeed:
    label: str
    total: int
    correct: int
    accuracyPct: float
