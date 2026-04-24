from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AttemptAssetDto(BaseModel):
    path: str = ""


class SavePracticeAttemptAnswerRequest(BaseModel):
    questionId: int
    questionNumber: int
    part: int
    test: int
    section: str | None = None
    partLabel: str | None = None
    skill: str | None = None
    subskill: str | None = None
    type: str | None = None
    groupId: str | None = None
    question: str | None = None
    options: list[str] = Field(default_factory=list)
    selectedAnswerIndex: int | None = None
    selectedAnswerText: str | None = None
    correctAnswerIndex: int | None = None
    correctAnswer: str | None = None
    correctAnswerText: str | None = None
    isCorrect: bool = False
    isFlagged: bool = False
    explanation: str | None = None
    audio: AttemptAssetDto | None = None
    graphic: AttemptAssetDto | None = None
    image: AttemptAssetDto | None = None


class SavePracticeAttemptRequest(BaseModel):
    userId: int | None = None
    title: str = ""
    subtitle: str | None = None
    mode: str = "exam"
    parts: str = ""
    difficulty: str = "mixed"
    totalQuestions: int = 0
    answeredCount: int = 0
    correctCount: int = 0
    accuracyPct: float = 0
    score: int | None = None
    timeSpentSeconds: int = 0
    startedAtUtc: datetime | None = None
    submittedAtUtc: datetime | None = None
    answers: list[SavePracticeAttemptAnswerRequest] = Field(default_factory=list)


class SaveMockTestAttemptAnswerRequest(BaseModel):
    questionId: int
    questionNumber: int
    part: int
    test: int
    section: str | None = None
    partLabel: str | None = None
    skill: str | None = None
    subskill: str | None = None
    type: str | None = None
    groupId: str | None = None
    question: str | None = None
    options: list[str] = Field(default_factory=list)
    selectedAnswerIndex: int | None = None
    selectedAnswerText: str | None = None
    correctAnswerIndex: int | None = None
    correctAnswer: str | None = None
    correctAnswerText: str | None = None
    isCorrect: bool = False
    isFlagged: bool = False
    explanation: str | None = None
    audio: AttemptAssetDto | None = None
    graphic: AttemptAssetDto | None = None
    image: AttemptAssetDto | None = None


class SaveMockTestAttemptRequest(BaseModel):
    userId: int | None = None
    attemptType: str = "mock-test"
    title: str = ""
    totalQuestions: int = 0
    answeredCount: int = 0
    correctCount: int = 0
    listeningScore: int = 0
    readingScore: int = 0
    totalScore: int = 0
    accuracyPct: float = 0
    timeSpentSeconds: int = 0
    status: str = "submitted"
    startedAtUtc: datetime | None = None
    submittedAtUtc: datetime | None = None
    answers: list[SaveMockTestAttemptAnswerRequest] = Field(default_factory=list)


class SaveDiagnosticAttemptRequest(BaseModel):
    userId: int | None = None
    targetScore: int | None = None
    weeks: int | None = None
    minutesPerDay: int | None = None
    score: int = 0
    accuracyPct: float = 0
    correctCount: int = 0
    totalQuestions: int = 0
    levelName: str | None = None
    levelRange: str | None = None
    weakSubskillsJson: str | None = None
    topErrorsJson: str | None = None
    answers: list[dict] = Field(default_factory=list)


class AttemptSkillBreakdownDto(BaseModel):
    skill: str = ""
    total: int = 0
    correct: int = 0
    accuracyPct: float = 0


class AttemptPartBreakdownDto(BaseModel):
    part: int = 0
    total: int = 0
    correct: int = 0
    accuracyPct: float = 0


class AttemptWeakAreaDto(BaseModel):
    type: str = ""
    label: str = ""
    accuracyPct: float = 0
    total: int = 0
    correct: int = 0
    suggestion: str = ""


class AttemptResultQuestionDto(BaseModel):
    questionId: int
    questionNumber: int
    test: int
    part: int
    section: str = ""
    partLabel: str | None = None
    type: str | None = None
    groupId: str | None = None
    skill: str = ""
    subskill: str | None = None
    question: str = ""
    options: list[str] = Field(default_factory=list)
    userAnswer: str | None = None
    userAnswerIndex: int | None = None
    correctAnswer: str | None = None
    correctAnswerIndex: int | None = None
    isCorrect: bool = False
    explanation: str | None = None
    audio: AttemptAssetDto | None = None
    graphic: AttemptAssetDto | None = None
    image: AttemptAssetDto | None = None


class AttemptResultDto(BaseModel):
    attemptId: int
    attemptType: str = ""
    title: str = ""
    totalQuestions: int = 0
    correctCount: int = 0
    wrongCount: int = 0
    unansweredCount: int = 0
    accuracyPct: float = 0
    startedAt: datetime | None = None
    submittedAt: datetime | None = None
    durationSeconds: int = 0
    durationMinutes: int | None = None
    scaledScore: int | None = None
    listeningScore: int | None = None
    readingScore: int | None = None
    skillBreakdown: list[AttemptSkillBreakdownDto] = Field(default_factory=list)
    partBreakdown: list[AttemptPartBreakdownDto] = Field(default_factory=list)
    weakAreas: list[AttemptWeakAreaDto] = Field(default_factory=list)
    questions: list[AttemptResultQuestionDto] = Field(default_factory=list)


class SaveAttemptResponse(BaseModel):
    attemptId: int
    reviewQueuedCount: int
    skillStatsUpdated: int
    partStatsUpdated: int
    result: AttemptResultDto | None = None
