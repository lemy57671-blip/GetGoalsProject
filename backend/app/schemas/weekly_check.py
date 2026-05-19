from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.attempts import AttemptResultDto
from app.schemas.toeic import ToeicRunnerQuestionDto


class WeeklyCheckCurrentDto(BaseModel):
    attemptId: int | None = None
    weeklyCheckId: str = ""
    title: str = "Weekly Check"
    description: str = ""
    totalQuestions: int = 0
    estimatedMinutes: int = 0
    focusSkill: str = ""
    focusSkillLabel: str = ""
    focusPart: int | None = None
    sourceAnalytics: str = ""
    difficulty: str = "mixed"
    topWeakSubskills: list[str] = Field(default_factory=list)
    questions: list[ToeicRunnerQuestionDto] = Field(default_factory=list)


class WeeklyCheckAnswerRequest(BaseModel):
    questionId: int
    part: int
    selectedAnswerIndex: int | None = None
    isFlagged: bool = False


class WeeklyCheckSubmitRequest(BaseModel):
    attemptId: int | None = None
    userId: int | None = None
    weeklyCheckId: str = ""
    title: str | None = None
    description: str | None = None
    totalQuestions: int = 0
    estimatedMinutes: int | None = None
    focusSkill: str | None = None
    focusPart: int | None = None
    sourceAnalytics: str | None = None
    startedAtUtc: datetime | None = None
    timeSpentSeconds: int = 0
    answers: list[WeeklyCheckAnswerRequest] = Field(default_factory=list)


class WeeklyCheckSubmitResponse(BaseModel):
    attemptId: int
    attemptType: str = "weekly_check"
    reviewQueuedCount: int = 0
    skillStatsUpdated: int = 0
    partStatsUpdated: int = 0
    result: AttemptResultDto | None = None
