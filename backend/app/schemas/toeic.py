from __future__ import annotations

from pydantic import BaseModel, Field


class ToeicImportStatusDto(BaseModel):
    ready: bool = False
    mode: str = "sql-server"
    summaryPath: str = ""
    message: str = ""
    nextStep: str = ""


class ToeicSourceFilesDto(BaseModel):
    docx: str = ""
    audioZip: str = ""
    mappingCsv: str = ""


class ToeicInventoryDto(BaseModel):
    mappingRows: int = 0
    audioFiles: int = 0
    docxParagraphs: int = 0
    detectedParts: list[int] = Field(default_factory=list)


class ToeicPartInventoryDto(BaseModel):
    part: int = 0
    name: str = ""
    skill: str = ""
    count: int = 0
    audioCount: int = 0
    testsAvailable: list[int] = Field(default_factory=list)
    sampleQuestionRange: str = ""
    audioReady: bool = False


class ToeicBundleSummaryDto(BaseModel):
    sourceFiles: ToeicSourceFilesDto = Field(default_factory=ToeicSourceFilesDto)
    inventory: ToeicInventoryDto = Field(default_factory=ToeicInventoryDto)
    parts: list[ToeicPartInventoryDto] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ToeicRecommendedPackDto(BaseModel):
    id: str = ""
    part: int = 0
    title: str = ""
    skill: str = ""
    why: str = ""
    difficulty: str = ""
    suggestedQuestionCount: int = 0
    suggestedTests: list[int] = Field(default_factory=list)
    audioReady: bool = False


class ToeicRecommendationDto(BaseModel):
    track: str = ""
    reason: str = ""
    currentScore: int | None = None
    targetScore: int | None = None
    weakSkills: list[str] = Field(default_factory=list)
    recommendedPacks: list[ToeicRecommendedPackDto] = Field(default_factory=list)


class ToeicRunnerAssetDto(BaseModel):
    path: str = ""


class ToeicRunnerPassageDto(BaseModel):
    id: int | None = None
    groupCode: str | None = None
    title: str = ""
    text: str = ""
    audio: ToeicRunnerAssetDto | None = None
    image: ToeicRunnerAssetDto | None = None


class ToeicRunnerQuestionDto(BaseModel):
    id: int
    questionId: int | None = None
    dbId: int | None = None
    docxQuestionId: int | None = None
    sourceQuestionId: int | None = None
    section: str = "Listening"
    part: int = 1
    partLabel: str = "Part 1"
    type: str = "question"
    question: str = ""
    skill: str = ""
    subskill: str | None = None
    groupId: str | None = None
    test: int = 0
    questionNumber: int = 0
    options: list[str] = Field(default_factory=list)
    correctAnswer: str | None = None
    correctAnswerIndex: int | None = None
    explanation: str | None = None
    difficulty: str = "mixed"
    abilityBand: str = "intermediate"
    minScore: int | None = None
    maxScore: int | None = None
    image: ToeicRunnerAssetDto | None = None
    graphic: ToeicRunnerAssetDto | None = None
    audio: ToeicRunnerAssetDto | None = None
    audioUrl: str | None = None
    passage: ToeicRunnerPassageDto | None = None


class ToeicReviewFocusRunnerDto(BaseModel):
    items: list[ToeicRunnerQuestionDto] = Field(default_factory=list)
    matchStrategy: str = "no_match"
    matchStrategiesUsed: list[str] = Field(default_factory=list)
    sourceQuestionId: int | None = None
    excludedOriginal: bool = True
    requestedCount: int = 0
    returnedCount: int = 0
    usedPart: int | None = None
    usedSkill: str | None = None
    usedSubskill: str | None = None
    usedDifficulty: str = "mixed"
