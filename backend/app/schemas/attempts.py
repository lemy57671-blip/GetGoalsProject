from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.toeic import ToeicRunnerQuestionDto


class AttemptAssetDto(BaseModel):
    path: str = ""


class AttemptResultOptionDto(BaseModel):
    key: str = ""
    text: str = ""
    isCorrect: bool = False
    sortOrder: int = 0


class AttemptResultPassageDto(BaseModel):
    id: int | None = None
    groupCode: str | None = None
    title: str | None = None
    text: str | None = None
    audioPath: str | None = None
    imagePath: str | None = None
    audio: AttemptAssetDto | None = None
    image: AttemptAssetDto | None = None


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
    attemptId: int | None = None
    userId: int | None = None
    source: str | None = None
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
    attemptId: int | None = None
    userId: int | None = None
    source: str | None = None
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


class SaveDiagnosticAttemptAnswerRequest(BaseModel):
    questionId: int
    questionNumber: int = 0
    part: int | None = None
    skill: str | None = None
    subskill: str | None = None
    selectedAnswerIndex: int | None = None
    correctAnswerIndex: int | None = None
    isCorrect: bool = False


class SaveDiagnosticAttemptRequest(BaseModel):
    userId: int | None = None
    currentScore: int | None = None
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
    answers: list[SaveDiagnosticAttemptAnswerRequest] = Field(default_factory=list)


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
    runtimeQuestionId: int | None = None
    missingReason: str | None = None
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
    questionText: str | None = None
    options: list[str] = Field(default_factory=list)
    optionRows: list[AttemptResultOptionDto] = Field(default_factory=list)
    userAnswer: str | None = None
    userAnswerIndex: int | None = None
    selectedOptionKey: str | None = None
    selectedOptionText: str | None = None
    correctAnswer: str | None = None
    correctAnswerIndex: int | None = None
    correctOptionKey: str | None = None
    correctOptionText: str | None = None
    isCorrect: bool = False
    explanation: str | None = None
    explanationText: str | None = None
    rawBlock: str | None = None
    rawText: str | None = None
    passage: AttemptResultPassageDto | None = None
    audio: AttemptAssetDto | None = None
    audioPath: str | None = None
    graphic: AttemptAssetDto | None = None
    image: AttemptAssetDto | None = None
    imagePath: str | None = None


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


class AttemptQuestionStartRequest(BaseModel):
    sourceType: str = "practice"
    parts: list[int] = Field(default_factory=list)
    part: int | None = None
    skill: str | None = None
    subskill: str | None = None
    difficulty: str = "mixed"
    count: int = 10
    test: int | None = None
    roadmapWeekId: int | None = None
    roadmapSetId: int | None = None
    seedContext: str | None = None


class AttemptQuestionStartResponse(BaseModel):
    attemptId: int
    sourceType: str
    questions: list[ToeicRunnerQuestionDto] = Field(default_factory=list)
    shortage: bool = False
    shortageParts: list[int] = Field(default_factory=list)
    repeated: bool = False
    repeatReason: str | None = None
    message: str | None = None
