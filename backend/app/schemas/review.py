from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_id: int = Field(validation_alias=AliasChoices("question_id", "questionId"))
    source: str | None = None
    attempt_id: int | None = Field(default=None, validation_alias=AliasChoices("attempt_id", "attemptId"))
    runtime_question_id: int | None = Field(default=None, validation_alias=AliasChoices("runtime_question_id", "runtimeQuestionId"))
    diagnostic_question_id: int | None = Field(default=None, validation_alias=AliasChoices("diagnostic_question_id", "diagnosticQuestionId"))
    note_text: str = Field(default="", max_length=20000, validation_alias=AliasChoices("note_text", "noteText"))


class NoteUpdate(BaseModel):
    note_text: str = Field(default="", max_length=20000)


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    source: str | None = None
    attempt_id: int | None = None
    runtime_question_id: int | None = None
    diagnostic_question_id: int | None = None
    note_text: str
    created_at: datetime
    updated_at: datetime


class HighlightCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_id: int = Field(validation_alias=AliasChoices("question_id", "questionId"))
    source: str | None = None
    attempt_id: int | None = Field(default=None, validation_alias=AliasChoices("attempt_id", "attemptId"))
    runtime_question_id: int | None = Field(default=None, validation_alias=AliasChoices("runtime_question_id", "runtimeQuestionId"))
    diagnostic_question_id: int | None = Field(default=None, validation_alias=AliasChoices("diagnostic_question_id", "diagnosticQuestionId"))
    target_type: str = Field(default="question_text", validation_alias=AliasChoices("target_type", "targetType"))
    target_key: str | None = Field(default=None, validation_alias=AliasChoices("target_key", "targetKey"))
    selected_text: str = Field(default="", max_length=20000, validation_alias=AliasChoices("selected_text", "selectedText"))
    start_offset: int | None = Field(default=None, validation_alias=AliasChoices("start_offset", "startOffset"))
    end_offset: int | None = Field(default=None, validation_alias=AliasChoices("end_offset", "endOffset"))
    color: str = "yellow"
    note_text: str | None = Field(default=None, validation_alias=AliasChoices("note_text", "noteText"))


class HighlightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    source: str | None = None
    attempt_id: int | None = None
    runtime_question_id: int | None = None
    diagnostic_question_id: int | None = None
    target_type: str
    target_key: str | None = None
    selected_text: str
    start_offset: int | None = None
    end_offset: int | None = None
    color: str
    note_text: str | None = None
    created_at: datetime
    updated_at: datetime


class BookmarkToggleRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_id: int = Field(validation_alias=AliasChoices("question_id", "questionId"))
    source: str | None = None
    attempt_id: int | None = Field(default=None, validation_alias=AliasChoices("attempt_id", "attemptId"))
    runtime_question_id: int | None = Field(default=None, validation_alias=AliasChoices("runtime_question_id", "runtimeQuestionId"))
    diagnostic_question_id: int | None = Field(default=None, validation_alias=AliasChoices("diagnostic_question_id", "diagnosticQuestionId"))


class BookmarkResponse(BaseModel):
    question_id: int
    source: str | None = None
    runtime_question_id: int | None = None
    diagnostic_question_id: int | None = None
    bookmarked: bool


class ReviewOptionResponse(BaseModel):
    option_label: str
    option_text_en: str
    is_correct: bool = False
    sort_order: int = 0
    option_key: str | None = None
    option_text: str | None = None
    key: str | None = None
    text: str | None = None


class ReviewAssetResponse(BaseModel):
    path: str


class ReviewPassageResponse(BaseModel):
    id: int | None = None
    group_code: str | None = None
    title: str | None = None
    text: str | None = None
    passage_text: str | None = None
    audio_path: str | None = None
    image_path: str | None = None
    audio: ReviewAssetResponse | None = None
    image: ReviewAssetResponse | None = None


class ReviewItemResponse(BaseModel):
    id: int | None = None
    source: str | None = None
    question_id: int
    attempt_id: int | None = None
    runtime_question_id: int | None = None
    diagnostic_question_id: int | None = None
    missing_reason: str | None = None
    question_number: int | None = None
    part: int | None = None
    part_number: int | None = None
    section: str | None = None
    part_label: str | None = None
    question_type: str | None = None
    skill_code: str | None = None
    subskill_code: str | None = None
    topic: str | None = None
    difficulty: str | None = None
    test_number: int | None = None
    question_text_en: str = ""
    question_text: str | None = None
    passage_text: str | None = None
    passage: ReviewPassageResponse | None = None
    audio: ReviewAssetResponse | None = None
    image: ReviewAssetResponse | None = None
    options: list[ReviewOptionResponse] = Field(default_factory=list)
    correct_option_label: str | None = None
    correct_option_key: str | None = None
    correct_answer_text: str | None = None
    explanation_detail: str | None = None
    option_analysis: str | None = None
    vocabulary_notes: str | None = None
    raw_explanation: str | None = None
    raw_block: str | None = None
    translation_vi: str | None = None
    final_translation_vi: str | None = None
    user_selected_option_label: str | None = None
    selected_option_key: str | None = None
    is_correct: bool | None = None
    is_skipped: bool = False
    review_reason: str | None = None
    review_reasons: list[str] = Field(default_factory=list)
    has_note: bool = False
    has_highlight: bool = False
    is_bookmarked: bool = False
    bookmarked: bool = False
    notes: list[NoteResponse] = Field(default_factory=list)
    highlights: list[HighlightResponse] = Field(default_factory=list)
    source_attempt_id: int | None = None
    source_type: str | None = None
    source_label: str | None = None
    attempt_type: str | None = None
    source_queue_id: int | None = None
    status: str = "active"

