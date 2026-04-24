from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.schemas.diagnostic import (
    DiagnosticAnalysisDto,
    DiagnosticAssetDto,
    DiagnosticLevelDto,
    DiagnosticQuestionDto,
    DiagnosticQuestionsResponse,
    DiagnosticRoadmapWeekDto,
    DiagnosticSkillStatDto,
    DiagnosticSubskillRowDto,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
    DiagnosticTestInfoDto,
    DiagnosticTopErrorDto,
    DiagnosticWrongItemDto,
)
from app.schemas.toeic import ToeicRunnerQuestionDto
from app.services.toeic import get_mixed_runner_questions


DIAGNOSTIC_PARTS = [1, 2, 3, 4, 5, 6, 7]
DIAGNOSTIC_QUESTION_COUNT = 28


@dataclass
class _StatBucket:
    correct: int = 0
    total: int = 0


def get_diagnostic_questions(db: Session) -> DiagnosticQuestionsResponse:
    questions = _load_bank(db)
    return DiagnosticQuestionsResponse(
        test_info=DiagnosticTestInfoDto(total_questions=len(questions)),
        questions=[_map_question(item) for item in questions],
    )


def submit_diagnostic(db: Session, payload: DiagnosticSubmitRequest) -> DiagnosticSubmitResponse:
    questions = _load_bank(db)
    answers = _normalize_answers(payload.answers)
    total = len(questions)
    answered_count = 0
    correct_count = 0
    wrong_items: list[DiagnosticWrongItemDto] = []
    skill_buckets: dict[str, _StatBucket] = {}
    subskill_buckets: dict[str, _StatBucket] = {}
    error_counter: Counter[str] = Counter()

    for index, question in enumerate(questions):
        selected = answers.get(index)
        correct_index = question.correctAnswerIndex
        if selected is None:
            continue

        answered_count += 1
        is_correct = correct_index is not None and selected == correct_index
        if is_correct:
            correct_count += 1

        skill = _normalize_label(question.skill, "general_english")
        subskill = _normalize_label(question.subskill, skill)
        skill_bucket = skill_buckets.setdefault(skill, _StatBucket())
        subskill_bucket = subskill_buckets.setdefault(subskill, _StatBucket())
        skill_bucket.total += 1
        subskill_bucket.total += 1
        if is_correct:
            skill_bucket.correct += 1
            subskill_bucket.correct += 1
        else:
            error_counter[subskill] += 1
            wrong_items.append(
                DiagnosticWrongItemDto(
                    id=question.id,
                    skill=skill,
                    subskill=subskill,
                    questionText=question.question,
                    chosen=selected,
                    correct=correct_index,
                    options=list(question.options),
                )
            )

    accuracy_pct = 0 if total == 0 else int(round((correct_count / total) * 100))
    level = _resolve_level(accuracy_pct)
    score = _resolve_score(accuracy_pct)
    skill_stats = {
        key: DiagnosticSkillStatDto(correct=value.correct, total=value.total, acc=_percent(value.correct, value.total))
        for key, value in sorted(skill_buckets.items())
    }
    sorted_subskills = sorted(
        (
            DiagnosticSubskillRowDto(subskill=key, correct=value.correct, total=value.total, acc=_percent(value.correct, value.total))
            for key, value in subskill_buckets.items()
        ),
        key=lambda item: (item.acc, item.total, item.subskill),
    )
    weak_subskills = [item.subskill for item in sorted_subskills if item.total > 0][:5]
    strong_subskills = [item.subskill for item in sorted(sorted_subskills, key=lambda item: (-item.acc, -item.total, item.subskill))[:5]]
    top_errors = [DiagnosticTopErrorDto(type=key, count=count) for key, count in error_counter.most_common(5)]

    return DiagnosticSubmitResponse(
        analysis=DiagnosticAnalysisDto(
            score=score,
            level=level,
            accuracyPct=accuracy_pct,
            correctCount=correct_count,
            answeredCount=answered_count,
            total=total,
            skillStats=skill_stats,
            subskillRows=sorted_subskills,
            weakSubskills=weak_subskills,
            strongSubskills=strong_subskills,
            topErrors=top_errors,
            wrongList=wrong_items[:20],
        ),
        roadmap=_build_roadmap(payload, weak_subskills, strong_subskills, level),
    )


def _load_bank(db: Session) -> list[ToeicRunnerQuestionDto]:
    return get_mixed_runner_questions(db, DIAGNOSTIC_PARTS, count=DIAGNOSTIC_QUESTION_COUNT)


def _map_question(question: ToeicRunnerQuestionDto) -> DiagnosticQuestionDto:
    return DiagnosticQuestionDto(
        id=question.id,
        question=question.question,
        options=list(question.options),
        correct=question.correctAnswerIndex,
        skill=question.skill,
        subskill=question.subskill,
        prompt_type=question.type,
        image=DiagnosticAssetDto(path=question.image.path) if question.image else None,
        audio=DiagnosticAssetDto(path=question.audio.path) if question.audio else None,
    )


def _normalize_answers(raw: dict[str, int]) -> dict[int, int]:
    normalized: dict[int, int] = {}
    for key, value in raw.items():
        try:
            normalized[int(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return normalized


def _normalize_label(value: str | None, fallback: str) -> str:
    normalized = (value or "").strip().lower().replace(" ", "_")
    return normalized or fallback


def _percent(correct: int, total: int) -> float:
    return 0 if total <= 0 else round((correct / total) * 100, 2)


def _resolve_score(accuracy_pct: int) -> int:
    score = int(round(5 + (accuracy_pct / 100) * 985))
    return max(5, min(score, 990))


def _resolve_level(accuracy_pct: int) -> DiagnosticLevelDto:
    if accuracy_pct < 35:
        return DiagnosticLevelDto(code="starter", name="Starter", range="250-450")
    if accuracy_pct < 55:
        return DiagnosticLevelDto(code="elementary", name="Elementary", range="450-600")
    if accuracy_pct < 75:
        return DiagnosticLevelDto(code="intermediate", name="Intermediate", range="600-750")
    if accuracy_pct < 90:
        return DiagnosticLevelDto(code="upper_intermediate", name="Upper Intermediate", range="750-850")
    return DiagnosticLevelDto(code="advanced", name="Advanced", range="850-990")


def _build_roadmap(
    payload: DiagnosticSubmitRequest,
    weak_subskills: list[str],
    strong_subskills: list[str],
    level: DiagnosticLevelDto,
) -> list[DiagnosticRoadmapWeekDto]:
    total_weeks = max(1, min(payload.weeks or 8, 12))
    minutes_per_day = max(10, payload.minutes_per_day or 30)
    focus_pool = weak_subskills or strong_subskills or [level.code]
    roadmap: list[DiagnosticRoadmapWeekDto] = []
    for week_number in range(1, total_weeks + 1):
        focus = focus_pool[(week_number - 1) % len(focus_pool)]
        focus_label = focus.replace("_", " ")
        roadmap.append(
            DiagnosticRoadmapWeekDto(
                week=week_number,
                focus=focus,
                title=f"Week {week_number} - {focus_label.title()}",
                tasks=[
                    f"Study {focus_label} for {minutes_per_day} minutes each day.",
                    f"Complete one focused TOEIC block and review all mistakes in {focus_label}.",
                    f"End the week with a mixed review set and note three takeaways for {focus_label}.",
                ],
            )
        )
    return roadmap
