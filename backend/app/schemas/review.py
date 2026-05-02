from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    question_id: int
    attempt_id: int | None = None
    note_text: str = Field(default="", max_length=20000)


class NoteUpdate(BaseModel):
    note_text: str = Field(default="", max_length=20000)


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    attempt_id: int | None = None
    note_text: str
    created_at: datetime
    updated_at: datetime


class HighlightCreate(BaseModel):
    question_id: int
    attempt_id: int | None = None
    target_type: str = "question_text"
    target_key: str | None = None
    selected_text: str = Field(default="", max_length=20000)
    start_offset: int | None = None
    end_offset: int | None = None
    color: str = "yellow"
    note_text: str | None = None


class HighlightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    attempt_id: int | None = None
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
    question_id: int
    attempt_id: int | None = None


class BookmarkResponse(BaseModel):
    question_id: int
    bookmarked: bool


class ReviewOptionResponse(BaseModel):
    option_label: str
    option_text_en: str
    is_correct: bool = False
    sort_order: int = 0


class ReviewItemResponse(BaseModel):
    question_id: int
    question_number: int | None = None
    part_number: int | None = None
    question_text_en: str = ""
    passage_text: str | None = None
    options: list[ReviewOptionResponse] = Field(default_factory=list)
    correct_option_label: str | None = None
    correct_answer_text: str | None = None
    explanation_detail: str | None = None
    option_analysis: str | None = None
    vocabulary_notes: str | None = None
    translation_vi: str | None = None
    final_translation_vi: str | None = None
    user_selected_option_label: str | None = None
    is_correct: bool | None = None
    bookmarked: bool = False
    notes: list[NoteResponse] = Field(default_factory=list)
    highlights: list[HighlightResponse] = Field(default_factory=list)
    source_attempt_id: int | None = None
    source_type: str | None = None
    source_queue_id: int | None = None
    status: str = "active"

