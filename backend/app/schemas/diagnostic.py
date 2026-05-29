from __future__ import annotations

from pydantic import BaseModel, Field


class DiagnosticAssetDto(BaseModel):
    path: str | None = None


class DiagnosticQuestionDto(BaseModel):
    id: int
    question: str = ""
    options: list[str] = Field(default_factory=list)
    correct: int | None = None
    skill: str | None = None
    subskill: str | None = None
    prompt_type: str | None = None
    image: DiagnosticAssetDto | None = None
    audio: DiagnosticAssetDto | None = None


class DiagnosticTestInfoDto(BaseModel):
    name: str = "TOEIC Placement Test"
    duration_minutes: int = 25
    total_questions: int = 0


class DiagnosticQuestionsResponse(BaseModel):
    test_info: DiagnosticTestInfoDto = Field(default_factory=DiagnosticTestInfoDto)
    questions: list[DiagnosticQuestionDto] = Field(default_factory=list)


class DiagnosticSubmitRequest(BaseModel):
    answers: dict[str, int] = Field(default_factory=dict)
    current_score: int | None = None
    target_score: int = 750
    weeks: int = 8
    minutes_per_day: int = 30


class DiagnosticLevelDto(BaseModel):
    code: str = ""
    name: str = ""
    range: str = ""


class DiagnosticSkillStatDto(BaseModel):
    correct: int = 0
    total: int = 0
    acc: float = 0


class DiagnosticSubskillRowDto(BaseModel):
    subskill: str = ""
    correct: int = 0
    total: int = 0
    acc: float = 0


class DiagnosticTopErrorDto(BaseModel):
    type: str = ""
    count: int = 0


class DiagnosticWrongItemDto(BaseModel):
    id: int
    skill: str = ""
    subskill: str = ""
    questionText: str = ""
    chosen: int | None = None
    correct: int | None = None
    options: list[str] = Field(default_factory=list)


class DiagnosticAnalysisDto(BaseModel):
    score: int = 0
    weight_score: int | None = None
    weighted_correct: float = 0
    weighted_total: float = 0
    weight_score_ratio: float = 0
    level: DiagnosticLevelDto = Field(default_factory=DiagnosticLevelDto)
    accuracyPct: int = 0
    correctCount: int = 0
    answeredCount: int = 0
    total: int = 0
    skillStats: dict[str, DiagnosticSkillStatDto] = Field(default_factory=dict)
    subskillRows: list[DiagnosticSubskillRowDto] = Field(default_factory=list)
    weakSubskills: list[str] = Field(default_factory=list)
    strongSubskills: list[str] = Field(default_factory=list)
    topErrors: list[DiagnosticTopErrorDto] = Field(default_factory=list)
    wrongList: list[DiagnosticWrongItemDto] = Field(default_factory=list)


class DiagnosticRoadmapWeekDto(BaseModel):
    week: int = 0
    focus: str = ""
    title: str = ""
    tasks: list[str] = Field(default_factory=list)


class DiagnosticSubmitResponse(BaseModel):
    analysis: DiagnosticAnalysisDto = Field(default_factory=DiagnosticAnalysisDto)
    roadmap: list[DiagnosticRoadmapWeekDto] = Field(default_factory=list)
