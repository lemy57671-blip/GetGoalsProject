from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from app.models import (
    MockTestAttempt,
    MockTestAttemptAnswer,
    PracticeAttempt,
    PracticeAttemptAnswer,
    User,
    UserPartStat,
    UserSkillAnalytics,
    UserSkillProfile,
)
from app.schemas.roadmap import AnalyticsBreakdownItemDto, AnalyticsPartBreakdownItemDto, UserSkillAnalyticsDto


def normalize_skill_code(rawSkill: str | None, rawSubskill: str | None = None) -> str:
    skill = (rawSkill or "").strip().lower()
    subskill = (rawSubskill or "").strip().lower()

    if "question-response" in skill or "question response" in skill or "response" in skill:
        return "listening_response"
    if "identifying actions" in skill or "photograph" in skill or "picture" in skill:
        return "listening_detail"
    if "conversation" in skill:
        if "main" in subskill or "purpose" in subskill:
            return "listening_main_idea"
        if "infer" in subskill or "intent" in subskill:
            return "listening_inference"
        return "listening_detail"
    if "text completion" in skill:
        return "reading_context"
    if "reading comprehension" in skill:
        if "infer" in subskill or "implied" in subskill:
            return "reading_inference"
        return "reading_detail"
    if "grammar" in skill:
        return "grammar"
    if "vocab" in skill:
        return "vocabulary"
    if "reading_context" in skill or "text_completion" in skill:
        return "reading_context"
    if "reading_detail" in skill or "scanning" in skill:
        return "reading_detail"
    if "reading_inference" in skill or "implied" in skill:
        return "reading_inference"
    if "listening_main_idea" in skill:
        return "listening_main_idea"
    if "listening_inference" in skill:
        return "listening_inference"
    if "listening_detail" in skill or "specific_information" in skill:
        return "listening_detail"
    if "listen" in skill:
        if "response" in subskill or "yes_no" in subskill or "wh_" in subskill:
            return "listening_response"
        if "infer" in subskill or "intent" in subskill:
            return "listening_inference"
        if "main" in subskill or "overview" in subskill:
            return "listening_main_idea"
        return "listening_detail"
    if "read" in skill:
        if "infer" in subskill or "implied" in subskill:
            return "reading_inference"
        if "context" in subskill or "sentence" in subskill:
            return "reading_context"
        return "reading_detail"
    if "picture" in subskill:
        return "listening_detail"
    if any(token in subskill for token in ("preposition", "modal", "passive")):
        return "grammar"
    if any(token in subskill for token in ("office", "finance", "marketing")):
        return "vocabulary"
    return "reading_detail"


def normalize_subskill_code(rawSubskill: str | None, rawSkill: str | None = None) -> str:
    subskill = (rawSubskill or "").strip().lower()
    if not subskill:
        skill_code = normalize_skill_code(rawSkill)
        return {
            "grammar": "grammar_foundation",
            "vocabulary": "business_vocabulary",
            "listening_response": "question_response",
            "listening_inference": "speaker_intent",
            "listening_main_idea": "main_idea",
            "reading_context": "sentence_insertion",
            "reading_inference": "implied_meaning",
        }.get(skill_code, "specific_information")

    mapping = {
        "listen_picture_description": "identifying_actions",
        "present_simple": "tense",
        "past_simple": "tense",
        "present_perfect": "tense",
        "future_will": "tense",
        "gerunds": "word_form",
        "infinitives": "word_form",
        "preposition_combos_basic": "preposition",
        "preposition_combos_advanced": "preposition",
        "modals_should_must": "modals",
        "modals_could_would": "modals",
        "passive_present": "voice",
        "passive_past": "voice",
        "relative_clauses": "clause_linking",
        "comparisons": "comparisons",
        "conditionals_type2": "conditionals",
        "business_office_basic": "business_vocabulary",
        "business_office_common": "business_vocabulary",
        "business_office_advanced": "business_vocabulary",
        "business_office_specialized": "business_vocabulary",
        "sales_marketing_basic": "business_vocabulary",
        "sales_marketing_advanced": "business_vocabulary",
        "finance_basic": "business_vocabulary",
        "finance_advanced": "business_vocabulary",
        "travel_business": "business_vocabulary",
        "hr_communication": "business_vocabulary",
        "general_grammar": "grammar_foundation",
        "general_vocab": "business_vocabulary",
    }
    return mapping.get(subskill, subskill)


def infer_part(rawSkill: str | None, rawSubskill: str | None = None) -> int:
    return {
        "listening_response": 2,
        "listening_inference": 3,
        "listening_main_idea": 4,
        "listening_detail": 1,
        "grammar": 5,
        "vocabulary": 5,
        "reading_context": 6,
        "reading_inference": 7,
        "reading_detail": 7,
    }.get(normalize_skill_code(rawSkill, rawSubskill), 7)


def to_title(value: str) -> str:
    if not value or not value.strip():
        return ""
    return " ".join(token.capitalize() for token in value.split("_") if token)


def get_default_subskills(focusSkillCode: str | None) -> list[str]:
    return {
        "grammar": ["grammar_foundation", "word_form", "clause_linking"],
        "vocabulary": ["business_vocabulary", "word_form", "reading_context"],
        "listening_detail": ["specific_information", "graphic_reference", "next_step"],
        "listening_inference": ["speaker_intent", "next_step", "specific_information"],
        "listening_main_idea": ["main_idea", "purpose", "speaker_context"],
        "listening_response": ["question_response", "speaker_intent", "specific_information"],
        "reading_context": ["sentence_insertion", "reading_context", "main_idea"],
        "reading_detail": ["scanning", "specific_information", "main_idea"],
        "reading_inference": ["implied_meaning", "main_idea", "scanning"],
    }.get((focusSkillCode or "").strip().lower(), [])


def to_dto(entity: UserSkillAnalytics | None) -> UserSkillAnalyticsDto:
    if entity is None:
        return UserSkillAnalyticsDto()
    return UserSkillAnalyticsDto(
        userId=entity.user_id,
        weakestSkill=entity.weakest_skill,
        weakestSkillLabel=entity.weakest_skill_label or to_title(entity.weakest_skill),
        weakestPart=entity.weakest_part,
        topWeakSubskills=_deserialize_list(entity.top_weak_subskills_json),
        skillBreakdown=[AnalyticsBreakdownItemDto(**item) for item in _deserialize_list(entity.skill_breakdown_json)],
        subskillBreakdown=[AnalyticsBreakdownItemDto(**item) for item in _deserialize_list(entity.subskill_breakdown_json)],
        partBreakdown=[AnalyticsPartBreakdownItemDto(**item) for item in _deserialize_list(entity.part_breakdown_json)],
        basedOnAttemptId=entity.based_on_attempt_id,
        updatedAtUtc=entity.updated_at_utc,
    )


@dataclass
class _AnswerSeed:
    attemptId: int
    submittedAtUtc: datetime
    part: int
    skillCode: str
    rawSkill: str | None
    isCorrect: bool
    source: str


def analyze_latest_performance(db: Session, user_id: int) -> UserSkillAnalytics | None:
    user_exists = db.scalar(select(func.count()).select_from(User).where(User.id == user_id))
    if not user_exists:
        return None

    skill_profiles = db.scalars(
        select(UserSkillProfile)
        .where(UserSkillProfile.user_id == user_id, UserSkillProfile.attempt_count > 0)
        .order_by(UserSkillProfile.accuracy_pct, desc(UserSkillProfile.attempt_count))
    ).all()

    part_stats = db.scalars(
        select(UserPartStat)
        .where(UserPartStat.user_id == user_id, UserPartStat.attempt_count > 0)
        .order_by(UserPartStat.accuracy_pct, desc(UserPartStat.attempt_count))
    ).all()

    recent_answers = _load_recent_answer_seeds(db, user_id)
    existing = db.scalar(select(UserSkillAnalytics).where(UserSkillAnalytics.user_id == user_id))

    if not skill_profiles and not part_stats and not recent_answers:
        return existing

    skill_breakdown = _build_skill_breakdown(skill_profiles, recent_answers)
    subskill_breakdown = _build_subskill_breakdown(recent_answers)
    part_breakdown = _build_part_breakdown(part_stats, recent_answers)
    weakest_skill = skill_breakdown[0] if skill_breakdown else None
    weakest_part = part_breakdown[0] if part_breakdown else None
    top_weak_subskills = [item.code for item in subskill_breakdown[:5] if item.code]
    if not top_weak_subskills and weakest_skill:
        top_weak_subskills = get_default_subskills(weakest_skill.code)

    latest_attempt_id = None
    if recent_answers:
        latest = sorted(recent_answers, key=lambda item: (item.submittedAtUtc, item.attemptId), reverse=True)[0]
        latest_attempt_id = latest.attemptId

    entity = existing or UserSkillAnalytics(user_id=user_id, created_at_utc=datetime.utcnow())
    entity.weakest_skill = weakest_skill.code if weakest_skill else ""
    entity.weakest_skill_label = weakest_skill.label if weakest_skill else ""
    entity.weakest_part = weakest_part.part if weakest_part else None
    entity.top_weak_subskills_json = json.dumps(top_weak_subskills)
    entity.skill_breakdown_json = json.dumps([item.model_dump() for item in skill_breakdown])
    entity.subskill_breakdown_json = json.dumps([item.model_dump() for item in subskill_breakdown])
    entity.part_breakdown_json = json.dumps([item.model_dump() for item in part_breakdown])
    entity.based_on_attempt_id = latest_attempt_id
    entity.updated_at_utc = datetime.utcnow()
    if existing is None:
        db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def _load_recent_answer_seeds(db: Session, user_id: int) -> list[_AnswerSeed]:
    from_date = datetime.utcnow() - timedelta(days=90)
    practice_rows = db.execute(
        select(
            PracticeAttemptAnswer.practice_attempt_id,
            PracticeAttempt.submitted_at_utc,
            PracticeAttempt.created_at_utc,
            PracticeAttemptAnswer.part,
            PracticeAttemptAnswer.skill,
            PracticeAttemptAnswer.is_correct,
        )
        .join(PracticeAttempt, PracticeAttempt.id == PracticeAttemptAnswer.practice_attempt_id)
        .where(
            PracticeAttempt.user_id == user_id,
            func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc) >= from_date,
        )
    ).all()
    mock_rows = db.execute(
        select(
            MockTestAttemptAnswer.mock_test_attempt_id,
            MockTestAttempt.submitted_at_utc,
            MockTestAttempt.created_at_utc,
            MockTestAttemptAnswer.part,
            MockTestAttemptAnswer.skill,
            MockTestAttemptAnswer.is_correct,
        )
        .join(MockTestAttempt, MockTestAttempt.id == MockTestAttemptAnswer.mock_test_attempt_id)
        .where(
            MockTestAttempt.user_id == user_id,
            func.coalesce(MockTestAttempt.submitted_at_utc, MockTestAttempt.created_at_utc) >= from_date,
        )
    ).all()

    seeds: list[_AnswerSeed] = []
    for row in practice_rows:
        seeds.append(
            _AnswerSeed(
                attemptId=row[0],
                submittedAtUtc=row[1] or row[2],
                part=row[3],
                skillCode=normalize_skill_code(row[4]),
                rawSkill=row[4],
                isCorrect=row[5],
                source="practice",
            )
        )
    for row in mock_rows:
        seeds.append(
            _AnswerSeed(
                attemptId=row[0],
                submittedAtUtc=row[1] or row[2],
                part=row[3],
                skillCode=normalize_skill_code(row[4]),
                rawSkill=row[4],
                isCorrect=row[5],
                source="mock-test",
            )
        )

    return sorted(seeds, key=lambda item: (item.submittedAtUtc, item.attemptId), reverse=True)[:300]


def _build_skill_breakdown(skill_profiles: list[UserSkillProfile], recent_answers: list[_AnswerSeed]) -> list[AnalyticsBreakdownItemDto]:
    if skill_profiles:
        return [
            AnalyticsBreakdownItemDto(
                code=item.skill_code,
                label=item.skill_name or to_title(item.skill_code),
                accuracy=float(item.accuracy_pct),
                correctCount=item.correct_count,
                attemptCount=item.attempt_count,
            )
            for item in skill_profiles
        ]

    grouped: dict[str, list[_AnswerSeed]] = {}
    for item in recent_answers:
        grouped.setdefault(item.skillCode, []).append(item)
    return sorted(
        [
            AnalyticsBreakdownItemDto(
                code=code,
                label=to_title(code),
                accuracy=round(sum(1 for row in group if row.isCorrect) * 100 / len(group), 2) if group else 0,
                correctCount=sum(1 for row in group if row.isCorrect),
                attemptCount=len(group),
            )
            for code, group in grouped.items()
            if code
        ],
        key=lambda item: (item.accuracy, -item.attemptCount),
    )


def _build_subskill_breakdown(recent_answers: list[_AnswerSeed]) -> list[AnalyticsBreakdownItemDto]:
    grouped: dict[str, list[_AnswerSeed]] = {}
    for item in recent_answers:
        if item.isCorrect:
            continue
        code = normalize_subskill_code(None, item.rawSkill) if item.rawSkill else (get_default_subskills(item.skillCode)[:1] or ["specific_information"])[0]
        grouped.setdefault(code, []).append(item)

    result = [
        AnalyticsBreakdownItemDto(code=code, label=to_title(code), accuracy=0, correctCount=0, attemptCount=len(group))
        for code, group in grouped.items()
    ]
    return sorted(result, key=lambda item: (-item.attemptCount, item.label))


def _build_part_breakdown(part_stats: list[UserPartStat], recent_answers: list[_AnswerSeed]) -> list[AnalyticsPartBreakdownItemDto]:
    if part_stats:
        return [
            AnalyticsPartBreakdownItemDto(
                part=item.part,
                accuracy=float(item.accuracy_pct),
                correctCount=item.correct_count,
                attemptCount=item.attempt_count,
            )
            for item in part_stats
        ]

    grouped: dict[int, list[_AnswerSeed]] = {}
    for item in recent_answers:
        if item.part > 0:
            grouped.setdefault(item.part, []).append(item)

    result = []
    for part, group in grouped.items():
        correct_count = sum(1 for row in group if row.isCorrect)
        result.append(
            AnalyticsPartBreakdownItemDto(
                part=part,
                accuracy=round(correct_count * 100 / len(group), 2) if group else 0,
                correctCount=correct_count,
                attemptCount=len(group),
            )
        )
    return sorted(result, key=lambda item: (item.accuracy, -item.attemptCount))


def _deserialize_list(raw: str | None) -> list:
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
