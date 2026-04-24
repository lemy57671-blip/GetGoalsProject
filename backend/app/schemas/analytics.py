from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.roadmap import RoadmapCurrentDto


class HistoryPointDto(BaseModel):
    date: str = ""
    studyMinutes: int = 0
    attemptsCount: int = 0
    correctAnswers: int = 0
    wrongAnswers: int = 0
    accuracy: float = 0


class WeakMetricDto(BaseModel):
    skill: str = ""
    accuracy: float = 0
    attemptCount: int = 0


class WeakPartDto(BaseModel):
    part: int = 0
    accuracy: float = 0
    attemptCount: int = 0


class LatestMockTestDto(BaseModel):
    title: str = ""
    totalScaledScore: int = 0
    listeningScaledScore: int = 0
    readingScaledScore: int = 0
    accuracy: float = 0
    submittedAtUtc: datetime | None = None


class LatestDiagnosticDto(BaseModel):
    estimatedScore: int = 0
    estimatedLevel: str | None = None
    levelRange: str | None = None
    theta: float | None = None
    submittedAtUtc: datetime | None = None
    weakSubskills: list[str] = Field(default_factory=list)


class DashboardOverviewDto(BaseModel):
    totalPracticeAttempts: int = 0
    recentAccuracy: float = 0
    totalStudyMinutes: int = 0
    pendingReviewCount: int = 0
    weakestSkill: WeakMetricDto | None = None
    weakestPart: WeakPartDto | None = None
    latestMockTest: LatestMockTestDto | None = None
    latestDiagnostic: LatestDiagnosticDto | None = None
    recentActiveDays: int = 0
    streakDays: int = 0
    activeRoadmap: RoadmapCurrentDto | None = None


class SkillProfileDto(BaseModel):
    skillCode: str = ""
    skillName: str = ""
    accuracy: float = 0
    correctCount: int = 0
    attemptCount: int = 0
    lastPracticedAtUtc: datetime | None = None


class PartStatDto(BaseModel):
    part: int = 0
    accuracy: float = 0
    correctCount: int = 0
    attemptCount: int = 0
    averageTimeSeconds: int = 0
    updatedAtUtc: datetime | None = None


class RecentPracticeAttemptDto(BaseModel):
    id: int
    title: str = ""
    subtitle: str | None = None
    mode: str = ""
    parts: str = ""
    correctCount: int = 0
    totalQuestions: int = 0
    accuracy: float = 0
    timeSpentSeconds: int = 0
    submittedAtUtc: datetime | None = None


class RecentMockTestDto(BaseModel):
    id: int
    title: str = ""
    totalScaledScore: int = 0
    listeningScaledScore: int = 0
    readingScaledScore: int = 0
    accuracy: float = 0
    timeSpentSeconds: int = 0
    submittedAtUtc: datetime | None = None


class ReviewQueueItemDto(BaseModel):
    id: int
    questionId: int
    part: int | None = None
    skill: str | None = None
    status: str = ""
    sourceAttemptType: str | None = None
    sourceAttemptId: int | None = None
    note: str | None = None
    addedAtUtc: datetime
    reviewedAtUtc: datetime | None = None


class ReviewQuestionDetailDto(BaseModel):
    id: int
    queueId: int
    questionId: int
    question: str = ""
    options: list[str] = Field(default_factory=list)
    userAnswer: str | None = None
    userAnswerIndex: int | None = None
    correctAnswer: str | None = None
    correctAnswerIndex: int | None = None
    isCorrect: bool = False
    explanation: str | None = None
    skill: str = ""
    subskill: str | None = None
    part: int = 0
    difficulty: str = "mixed"
    status: str = ""
    sourceAttemptType: str | None = None
    sourceAttemptId: int | None = None
    note: str | None = None
    addedAtUtc: datetime
    reviewedAtUtc: datetime | None = None
    passageTitle: str | None = None
    passageText: str | None = None
    audioUrl: str | None = None
    imageUrl: str | None = None
    graphicUrl: str | None = None


class ReviewSummaryDto(BaseModel):
    pendingCount: int = 0
    reviewedCount: int = 0
    topWeakSkills: list[WeakMetricDto] = Field(default_factory=list)
    recentReviewItems: list[ReviewQueueItemDto] = Field(default_factory=list)


class ProfileSummaryDto(BaseModel):
    currentScore: int | None = None
    targetScore: int | None = None
    weakSkills: list[str] = Field(default_factory=list)
    latestDiagnostic: LatestDiagnosticDto | None = None
    pendingReviewCount: int = 0


class ProgressSummaryDto(BaseModel):
    weeklyStudyMinutes: list[HistoryPointDto] = Field(default_factory=list)
    totalAttempts: int = 0
    totalCorrectAnswers: int = 0
    totalWrongAnswers: int = 0
    averageAccuracy: float = 0
    skillProfiles: list[SkillProfileDto] = Field(default_factory=list)
    partStats: list[PartStatDto] = Field(default_factory=list)
    recentPracticeAttempts: list[RecentPracticeAttemptDto] = Field(default_factory=list)
    recentMockTests: list[RecentMockTestDto] = Field(default_factory=list)
    pendingReviewCount: int = 0
