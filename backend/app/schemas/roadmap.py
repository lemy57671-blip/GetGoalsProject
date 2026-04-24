from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.toeic import ToeicRunnerQuestionDto


class AnalyticsBreakdownItemDto(BaseModel):
    code: str = ""
    label: str = ""
    accuracy: float = 0
    correctCount: int = 0
    attemptCount: int = 0


class AnalyticsPartBreakdownItemDto(BaseModel):
    part: int = 0
    accuracy: float = 0
    correctCount: int = 0
    attemptCount: int = 0


class UserSkillAnalyticsDto(BaseModel):
    userId: int = 0
    weakestSkill: str = ""
    weakestSkillLabel: str = ""
    weakestPart: int | None = None
    topWeakSubskills: list[str] = Field(default_factory=list)
    skillBreakdown: list[AnalyticsBreakdownItemDto] = Field(default_factory=list)
    subskillBreakdown: list[AnalyticsBreakdownItemDto] = Field(default_factory=list)
    partBreakdown: list[AnalyticsPartBreakdownItemDto] = Field(default_factory=list)
    basedOnAttemptId: int | None = None
    updatedAtUtc: datetime | None = None


class RoadmapSuggestedSetCriteriaDto(BaseModel):
    strategy: str = "focus"
    focusSkill: str = ""
    focusPart: int | None = None
    includeParts: list[int] = Field(default_factory=list)
    subskills: list[str] = Field(default_factory=list)
    difficulty: str = "mixed"
    questionCount: int = 30
    tags: list[str] = Field(default_factory=list)


class RoadmapSuggestedSetDto(BaseModel):
    id: int
    setKey: str = ""
    itemType: str = "suggested_set"
    title: str = ""
    description: str = ""
    focusSkill: str = ""
    focusPart: int | None = None
    subskills: list[str] = Field(default_factory=list)
    questionCount: int = 0
    difficulty: str = "mixed"
    tags: list[str] = Field(default_factory=list)
    criteria: RoadmapSuggestedSetCriteriaDto = Field(default_factory=RoadmapSuggestedSetCriteriaDto)


class RoadmapWeekDto(BaseModel):
    id: int
    weekNumber: int
    title: str = ""
    description: str = ""
    focusSkill: str = ""
    focusPart: int | None = None
    subskills: list[str] = Field(default_factory=list)
    recommendedQuestionCount: int = 0
    estimatedMinutes: int = 0
    status: str = "not_started"
    startedAtUtc: datetime | None = None
    completedAtUtc: datetime | None = None
    suggestedSets: list[RoadmapSuggestedSetDto] = Field(default_factory=list)


class RoadmapCurrentDto(BaseModel):
    id: int
    userId: int
    title: str = ""
    sourceType: str = "performance_history"
    weakestSkill: str = ""
    weakestSkillLabel: str = ""
    weakestPart: int | None = None
    totalWeeks: int = 0
    isActive: bool = False
    basedOnAttemptId: int | None = None
    createdAtUtc: datetime
    updatedAtUtc: datetime
    analytics: UserSkillAnalyticsDto | None = None
    weeks: list[RoadmapWeekDto] = Field(default_factory=list)


class RoadmapWeekSetsResponseDto(BaseModel):
    roadmapId: int
    weekId: int
    weekNumber: int
    title: str = ""
    description: str = ""
    focusSkill: str = ""
    focusPart: int | None = None
    subskills: list[str] = Field(default_factory=list)
    status: str = "not_started"
    suggestedSets: list[RoadmapSuggestedSetDto] = Field(default_factory=list)


class RoadmapSetQuestionsResponseDto(BaseModel):
    weekId: int
    setId: int
    setKey: str = ""
    title: str = ""
    description: str = ""
    focusSkill: str = ""
    focusPart: int | None = None
    tags: list[str] = Field(default_factory=list)
    questions: list[ToeicRunnerQuestionDto] = Field(default_factory=list)


class RoadmapSetEvidenceDto(BaseModel):
    weekId: int
    setId: int
    attemptId: int
    title: str = ""
    subtitle: str | None = None
    accuracy: float = 0
    correctCount: int = 0
    totalQuestions: int = 0
    submittedAtUtc: datetime | None = None
    confidence: str = "heuristic"
    source: str = "practice_attempt_metadata"
    reason: str = ""


class RoadmapEvidenceResponseDto(BaseModel):
    items: list[RoadmapSetEvidenceDto] = Field(default_factory=list)
    skippedUnparseableCount: int = 0
    matchRule: str = "mode=roadmap-set and subtitle='Roadmap week <weekId> - set <setId>'"
