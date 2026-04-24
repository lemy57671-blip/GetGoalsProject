from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import PracticeAttempt, User, UserRoadmap, UserRoadmapWeek, UserRoadmapWeekItem, UserSkillAnalytics
from app.schemas.roadmap import (
    RoadmapCurrentDto,
    RoadmapEvidenceResponseDto,
    RoadmapSetQuestionsResponseDto,
    RoadmapSetEvidenceDto,
    RoadmapSuggestedSetCriteriaDto,
    RoadmapSuggestedSetDto,
    RoadmapWeekDto,
    RoadmapWeekSetsResponseDto,
)
from app.services.skill_analytics import analyze_latest_performance, get_default_subskills, to_dto, to_title
from app.services.toeic import build_suggested_weekly_sets, get_questions_for_suggested_set
from app.utils.json_helpers import deserialize_list


ROADMAP_SET_SUBTITLE_RE = re.compile(r"roadmap\s+week\s+(\d+)\s+-\s+set\s+(\d+)", re.IGNORECASE)


def generate_for_user(db: Session, user_id: int) -> RoadmapCurrentDto | None:
    analytics = analyze_latest_performance(db, user_id)
    user = db.get(User, user_id)
    if user is None:
        return None

    has_focused_analytics = analytics is not None and (bool(analytics.weakest_skill.strip()) or analytics.weakest_part is not None)
    rules = _load_rules()
    skill_rule = _resolve_skill_rule(rules, analytics.weakest_skill if analytics else "")
    active_roadmaps = db.scalars(select(UserRoadmap).where(UserRoadmap.user_id == user_id, UserRoadmap.is_active == True)).all()
    for existing in active_roadmaps:
        existing.is_active = False
        existing.updated_at_utc = datetime.utcnow()

    title_label = skill_rule.label or (analytics.weakest_skill_label if analytics else "TOEIC Foundation") or "TOEIC Foundation"
    roadmap = UserRoadmap(
        user_id=user_id,
        title=f"8-week roadmap for {title_label}" if has_focused_analytics else "8-week TOEIC foundation roadmap",
        source_type="performance_history" if has_focused_analytics else "starter_fallback",
        based_on_attempt_id=analytics.based_on_attempt_id if analytics else None,
        weakest_skill=analytics.weakest_skill if analytics else "",
        weakest_skill_label=analytics.weakest_skill_label if analytics and analytics.weakest_skill_label else title_label,
        weakest_part=analytics.weakest_part if analytics else None,
        total_weeks=8,
        is_active=True,
        created_at_utc=datetime.utcnow(),
        updated_at_utc=datetime.utcnow(),
    )

    target_minutes = max(user.study_minutes_per_day or 30, 20)
    top_weak_subskills = deserialize_list(analytics.top_weak_subskills_json if analytics else None)
    week_rules = _build_week_rules(skill_rule, analytics) if has_focused_analytics and analytics else _build_starter_week_rules()

    for index in range(8):
        week_rule = week_rules[index]
        suggested_set_criteria = build_suggested_weekly_sets(
            week_rule.focusSkill,
            week_rule.focusPart,
            week_rule.subskills,
            week_rule.difficulty,
            week_rule.recommendedQuestionCount if week_rule.recommendedQuestionCount > 0 else 30,
        )
        week = UserRoadmapWeek(
            week_number=index + 1,
            sort_order=index + 1,
            title=week_rule.title,
            description=week_rule.description,
            focus_skill=week_rule.focusSkill,
            focus_part=week_rule.focusPart,
            subskills_json=json.dumps(week_rule.subskills if week_rule.subskills else top_weak_subskills[:3]),
            recommended_question_count=max(week_rule.recommendedQuestionCount, 90),
            estimated_minutes=max(week_rule.estimatedMinutes, target_minutes * 3),
            status="recommended" if index == 0 else "not_started",
            created_at_utc=datetime.utcnow(),
            updated_at_utc=datetime.utcnow(),
        )
        for item_index, criteria in enumerate(suggested_set_criteria):
            week.items.append(
                UserRoadmapWeekItem(
                    item_type="suggested_set",
                    set_key=f"week-{index + 1}-set-{item_index + 1}",
                    title=_build_set_title(item_index, week_rule, criteria),
                    description=_build_set_description(item_index, criteria),
                    focus_skill=criteria.focusSkill,
                    focus_part=criteria.focusPart,
                    subskills_json=json.dumps(criteria.subskills),
                    question_count=criteria.questionCount,
                    difficulty=criteria.difficulty,
                    tags_json=json.dumps(criteria.tags),
                    metadata_json=criteria.model_dump_json(),
                    sort_order=item_index + 1,
                    created_at_utc=datetime.utcnow(),
                    updated_at_utc=datetime.utcnow(),
                )
            )
        roadmap.weeks.append(week)

    db.add(roadmap)
    db.commit()
    return get_current_roadmap(db, user_id)


def get_current_roadmap(db: Session, user_id: int) -> RoadmapCurrentDto | None:
    roadmap = db.scalar(
        select(UserRoadmap)
        .options(selectinload(UserRoadmap.weeks).selectinload(UserRoadmapWeek.items))
        .where(UserRoadmap.user_id == user_id, UserRoadmap.is_active == True)
    )
    if roadmap is None:
        return None
    analytics = db.scalar(select(UserSkillAnalytics).where(UserSkillAnalytics.user_id == user_id))
    return _to_current_dto(roadmap, analytics)


def get_week_sets(db: Session, week_id: int) -> RoadmapWeekSetsResponseDto | None:
    week = db.scalar(select(UserRoadmapWeek).options(selectinload(UserRoadmapWeek.items)).where(UserRoadmapWeek.id == week_id))
    if week is None:
        return None
    return RoadmapWeekSetsResponseDto(
        roadmapId=week.roadmap_id,
        weekId=week.id,
        weekNumber=week.week_number,
        title=week.title,
        description=week.description,
        focusSkill=week.focus_skill,
        focusPart=week.focus_part,
        subskills=deserialize_list(week.subskills_json),
        status=week.status,
        suggestedSets=[_to_suggested_set_dto(item) for item in sorted(week.items, key=lambda value: value.sort_order)],
    )


def get_set_questions(db: Session, week_id: int, set_id: int) -> RoadmapSetQuestionsResponseDto | None:
    item = db.scalar(select(UserRoadmapWeekItem).where(UserRoadmapWeekItem.roadmap_week_id == week_id, UserRoadmapWeekItem.id == set_id))
    if item is None:
        return None
    criteria = _deserialize_criteria(item.metadata_json, item)
    questions = get_questions_for_suggested_set(db, criteria)
    return RoadmapSetQuestionsResponseDto(
        weekId=week_id,
        setId=item.id,
        setKey=item.set_key,
        title=item.title,
        description=item.description,
        focusSkill=item.focus_skill,
        focusPart=item.focus_part,
        tags=deserialize_list(item.tags_json),
        questions=questions,
    )


def get_roadmap_evidence(db: Session, user_id: int, limit: int = 100) -> RoadmapEvidenceResponseDto:
    normalized_limit = max(1, min(limit, 500))
    attempts = db.scalars(
        select(PracticeAttempt)
        .where(
            PracticeAttempt.user_id == user_id,
            func.lower(PracticeAttempt.mode) == "roadmap-set",
        )
        .order_by(func.coalesce(PracticeAttempt.submitted_at_utc, PracticeAttempt.created_at_utc).desc())
        .limit(normalized_limit)
    ).all()

    items_by_key: dict[tuple[int, int], RoadmapSetEvidenceDto] = {}
    skipped_unparseable_count = 0
    for attempt in attempts:
        parsed = _parse_roadmap_set_subtitle(attempt.subtitle)
        if parsed is None:
            skipped_unparseable_count += 1
            continue

        week_id, set_id = parsed
        key = (week_id, set_id)
        if key in items_by_key:
            continue

        items_by_key[key] = RoadmapSetEvidenceDto(
            weekId=week_id,
            setId=set_id,
            attemptId=attempt.id,
            title=attempt.title,
            subtitle=attempt.subtitle,
            accuracy=float(attempt.accuracy_pct),
            correctCount=attempt.correct_count,
            totalQuestions=attempt.total_questions,
            submittedAtUtc=attempt.submitted_at_utc or attempt.created_at_utc,
            confidence="heuristic",
            source="practice_attempt_metadata",
            reason="Matched by PracticeAttempt.mode and parseable roadmap week/set ids in subtitle.",
        )

    return RoadmapEvidenceResponseDto(
        items=list(items_by_key.values()),
        skippedUnparseableCount=skipped_unparseable_count,
    )


def start_week(db: Session, week_id: int) -> RoadmapWeekDto | None:
    week = db.scalar(select(UserRoadmapWeek).options(selectinload(UserRoadmapWeek.items)).where(UserRoadmapWeek.id == week_id))
    if week is None:
        return None
    if week.status.lower() in {"not_started", "recommended"}:
        week.status = "in_progress"
        week.started_at_utc = week.started_at_utc or datetime.utcnow()
        week.updated_at_utc = datetime.utcnow()
        db.commit()
    return _to_week_dto(week)


def complete_week(db: Session, week_id: int) -> RoadmapWeekDto | None:
    week = db.scalar(select(UserRoadmapWeek).options(selectinload(UserRoadmapWeek.items)).where(UserRoadmapWeek.id == week_id))
    if week is None:
        return None
    week.status = "completed"
    week.started_at_utc = week.started_at_utc or datetime.utcnow()
    week.completed_at_utc = datetime.utcnow()
    week.updated_at_utc = datetime.utcnow()
    db.commit()
    return _to_week_dto(week)


def _load_rules() -> "_RoadmapRulesDocument":
    if not settings.roadmap_rules_path.exists():
        return _RoadmapRulesDocument()
    raw = settings.roadmap_rules_path.read_text(encoding="utf-8-sig")
    parsed = json.loads(raw)
    skill_roadmaps = {}
    for key, value in parsed.get("skillRoadmaps", {}).items():
        skill_roadmaps[key] = _SkillRoadmapRule(
            label=value.get("label", ""),
            weeks=[_WeekRule(**week) for week in value.get("weeks", [])],
        )
    return _RoadmapRulesDocument(skillRoadmaps=skill_roadmaps)


def _resolve_skill_rule(document: "_RoadmapRulesDocument", weakest_skill: str) -> "_SkillRoadmapRule":
    if weakest_skill in document.skillRoadmaps:
        return document.skillRoadmaps[weakest_skill]
    if weakest_skill.startswith("listening_") and "listening_detail" in document.skillRoadmaps:
        return document.skillRoadmaps["listening_detail"]
    if weakest_skill.startswith("reading_") and "reading_detail" in document.skillRoadmaps:
        return document.skillRoadmaps["reading_detail"]
    if "grammar" in document.skillRoadmaps:
        return document.skillRoadmaps["grammar"]
    return _SkillRoadmapRule()


def _build_week_rules(rule: "_SkillRoadmapRule", analytics: UserSkillAnalytics) -> list["_WeekRule"]:
    configured = sorted(rule.weeks, key=lambda item: item.weekNumber)
    if len(configured) >= 8:
        return configured[:8]
    result = list(configured)
    fallback_skill = analytics.weakest_skill or "grammar"
    fallback_part = analytics.weakest_part
    while len(result) < 8:
        week_number = len(result) + 1
        result.append(
            _WeekRule(
                weekNumber=week_number,
                title=f"Week {week_number} reinforcement",
                description=f"Continue building consistency around {to_title(fallback_skill)}.",
                focusSkill=fallback_skill,
                focusPart=fallback_part,
                subskills=[],
                difficulty="easy" if week_number <= 2 else "medium" if week_number <= 5 else "mixed",
                recommendedQuestionCount=30,
                estimatedMinutes=90,
            )
        )
    return sorted(result, key=lambda item: item.weekNumber)[:8]


def _build_starter_week_rules() -> list["_WeekRule"]:
    result = []
    titles = {
        1: "Week 1 foundation reset",
        2: "Week 2 listening rhythm",
        3: "Week 3 reading accuracy",
        4: "Week 4 mixed reinforcement",
        5: "Week 5 speed and control",
        6: "Week 6 targeted review",
        7: "Week 7 mock-style blend",
        8: "Week 8 consolidation",
    }
    for week_number in range(1, 9):
        result.append(
            _WeekRule(
                weekNumber=week_number,
                title=titles[week_number],
                description="Build stable practice habits across listening and reading using mixed TOEIC sets.",
                focusSkill="",
                focusPart=None,
                subskills=[],
                difficulty="easy" if week_number <= 2 else "medium" if week_number <= 5 else "mixed",
                recommendedQuestionCount=30,
                estimatedMinutes=90,
            )
        )
    return result


def _build_set_title(item_index: int, week_rule: "_WeekRule", criteria: RoadmapSuggestedSetCriteriaDto) -> str:
    focus_label = "Foundation" if not week_rule.focusSkill else to_title(week_rule.focusSkill)
    return {
        0: f"{focus_label} focus set",
        1: "Targeted subskill set",
    }.get(item_index, "Mixed weekly review")


def _build_set_description(item_index: int, criteria: RoadmapSuggestedSetCriteriaDto) -> str:
    focus_label = "foundation skills" if not criteria.focusSkill else to_title(criteria.focusSkill)
    if item_index == 0:
        return f"30 curated questions around {focus_label}."
    if item_index == 1:
        return f"Target weak subskills: {', '.join(to_title(item) for item in criteria.subskills)}." if criteria.subskills else "Target the closest related subskills for this week."
    return "Mixed review to keep retention across the week focus and related parts."


def _to_current_dto(roadmap: UserRoadmap, analytics: UserSkillAnalytics | None) -> RoadmapCurrentDto:
    return RoadmapCurrentDto(
        id=roadmap.id,
        userId=roadmap.user_id,
        title=roadmap.title,
        sourceType=roadmap.source_type,
        weakestSkill=roadmap.weakest_skill,
        weakestSkillLabel=roadmap.weakest_skill_label,
        weakestPart=roadmap.weakest_part,
        totalWeeks=roadmap.total_weeks,
        isActive=roadmap.is_active,
        basedOnAttemptId=roadmap.based_on_attempt_id,
        createdAtUtc=roadmap.created_at_utc,
        updatedAtUtc=roadmap.updated_at_utc,
        analytics=to_dto(analytics),
        weeks=[_to_week_dto(item) for item in sorted(roadmap.weeks, key=lambda value: value.week_number)],
    )


def _to_week_dto(week: UserRoadmapWeek) -> RoadmapWeekDto:
    return RoadmapWeekDto(
        id=week.id,
        weekNumber=week.week_number,
        title=week.title,
        description=week.description,
        focusSkill=week.focus_skill,
        focusPart=week.focus_part,
        subskills=deserialize_list(week.subskills_json),
        recommendedQuestionCount=week.recommended_question_count,
        estimatedMinutes=week.estimated_minutes,
        status=week.status,
        startedAtUtc=week.started_at_utc,
        completedAtUtc=week.completed_at_utc,
        suggestedSets=[_to_suggested_set_dto(item) for item in sorted(week.items, key=lambda value: value.sort_order)],
    )


def _to_suggested_set_dto(item: UserRoadmapWeekItem) -> RoadmapSuggestedSetDto:
    return RoadmapSuggestedSetDto(
        id=item.id,
        setKey=item.set_key,
        itemType=item.item_type,
        title=item.title,
        description=item.description,
        focusSkill=item.focus_skill,
        focusPart=item.focus_part,
        subskills=deserialize_list(item.subskills_json),
        questionCount=item.question_count,
        difficulty=item.difficulty,
        tags=deserialize_list(item.tags_json),
        criteria=_deserialize_criteria(item.metadata_json, item),
    )


def _parse_roadmap_set_subtitle(subtitle: str | None) -> tuple[int, int] | None:
    if not subtitle or not subtitle.strip():
        return None
    match = ROADMAP_SET_SUBTITLE_RE.search(subtitle)
    if match is None:
        return None
    try:
        return int(match.group(1)), int(match.group(2))
    except (TypeError, ValueError):
        return None


def _deserialize_criteria(raw: str | None, item: UserRoadmapWeekItem) -> RoadmapSuggestedSetCriteriaDto:
    if raw and raw.strip():
        try:
            return RoadmapSuggestedSetCriteriaDto.model_validate_json(raw)
        except Exception:
            pass
    return RoadmapSuggestedSetCriteriaDto(
        focusSkill=item.focus_skill,
        focusPart=item.focus_part,
        subskills=deserialize_list(item.subskills_json),
        difficulty=item.difficulty,
        questionCount=item.question_count,
        tags=deserialize_list(item.tags_json),
    )


@dataclass
class _RoadmapRulesDocument:
    skillRoadmaps: dict[str, "_SkillRoadmapRule"] = None

    def __post_init__(self) -> None:
        if self.skillRoadmaps is None:
            self.skillRoadmaps = {}


@dataclass
class _SkillRoadmapRule:
    label: str = ""
    weeks: list["_WeekRule"] = None

    def __post_init__(self) -> None:
        if self.weeks is None:
            self.weeks = []


@dataclass
class _WeekRule:
    weekNumber: int = 0
    title: str = ""
    description: str = ""
    focusSkill: str = ""
    focusPart: int | None = None
    subskills: list[str] = None
    difficulty: str = "mixed"
    recommendedQuestionCount: int = 30
    estimatedMinutes: int = 90

    def __post_init__(self) -> None:
        if self.subskills is None:
            self.subskills = []
