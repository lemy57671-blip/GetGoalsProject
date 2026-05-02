from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatIntent(str, Enum):
    GENERAL = "general"
    WORD_MEANING = "word_meaning"
    COLLOCATION_PREPOSITION = "collocation_preposition"
    GAP_REQUIREMENT = "gap_requirement"
    CORRECT_ANSWER = "correct_answer"
    OPTION_REASON = "option_reason"
    FULL_OPTION_ANALYSIS = "full_option_analysis"
    TRANSLATION = "translation"
    EXPLANATION = "explanation"
    GRAMMAR_STRUCTURE = "grammar_structure"
    GRAMMAR_FORMULA_REQUEST = "grammar_formula_request"
    TARGET_COMPLETION_REQUEST = "target_completion_request"
    GRAMMAR_STRUCTURE_DEFINITION = "grammar_structure_definition"
    COLLOCATION_PREPOSITION_REQUEST = "collocation_preposition_request"
    RELATIVE_PRONOUN_REQUEST = "relative_pronoun_request"
    EXPLAIN = "explain"
    HINT = "hint"
    WHY_CORRECT = "why_correct"
    WHY_WRONG = "why_wrong"
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    TRANSLATE = "translate"
    SHORTER = "shorter"
    VOCABULARY_DEFINITION_ONLY = "vocabulary_definition_only"
    VOCABULARY_LOOKUP = "vocabulary_lookup"
    ANSWER_REQUEST = "answer_request"
    EXPLANATION_REQUEST = "explanation_request"
    TRANSLATION_REQUEST = "translation_request"
    VOCABULARY_REQUEST = "vocabulary_request"
    OPTION_ANALYSIS_REQUEST = "option_analysis_request"
    WHY_OPTION_WRONG = "why_option_wrong"
    GRAMMAR_REQUEST = "grammar_request"
    QUESTION_GOAL_REQUEST = "question_goal_request"
    GENERAL_QUESTION = "general_question"
    EXPLAIN_QUESTION = "explain_question"
    GRAMMAR_HELP = "grammar_help"
    VOCABULARY_HELP = "vocabulary_help"
    FIX_SENTENCE = "fix_sentence"
    GENERATE_EXAMPLES = "generate_examples"
    STUDY_PLAN = "study_plan"
    WEAK_SKILL_ANALYSIS = "weak_skill_analysis"
    MOCK_TEST_REVIEW = "mock_test_review"
    WEEKLY_CHECK_ADVICE = "weekly_check_advice"
    GENERAL_CHAT = "general_chat"


class ChatMessageDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: Optional[int] = None
    role: str = "assistant"
    content: str = ""
    intent: Optional[str] = None
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")


class IntentResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    intent: ChatIntent = ChatIntent.GENERAL
    confidence: float = 0.75
    reason: str = ""
    target_text: Optional[str] = None
    target_option_label: Optional[str] = None


class ChatContextSection(BaseModel):
    title: str = ""
    lines: list[str] = Field(default_factory=list)


class ChatContextBundle(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    question_id: Optional[int] = Field(default=None, alias="questionId")
    question_number: Optional[int] = Field(default=None, alias="questionNumber")
    part: Optional[int] = None
    prompt: Optional[str] = None
    question_text: Optional[str] = Field(default=None, alias="questionText")
    passage_text: Optional[str] = Field(default=None, alias="passageText")
    options: list[Any] = Field(default_factory=list)
    selected_answer: Optional[Any] = Field(default=None, alias="selectedAnswer")
    correct_answer: Optional[Any] = Field(default=None, alias="correctAnswer")
    explanation: Optional[str] = None
    raw: Optional[dict[str, Any]] = None
    sections: list[ChatContextSection] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    message: str = ""
    content: Optional[str] = None
    text: Optional[str] = None

    conversation_id: Optional[int] = Field(default=None, alias="conversationId")
    question_id: Optional[int] = Field(default=None, alias="questionId")
    current_question_id: Optional[int] = Field(default=None, alias="currentQuestionId")
    sql_id: Optional[int] = Field(default=None, alias="sqlId")

    question_number: Optional[int] = Field(default=None, alias="questionNumber")
    part: Optional[int] = None
    prompt: Optional[str] = None
    question_text: Optional[str] = Field(default=None, alias="questionText")
    passage_text: Optional[str] = Field(default=None, alias="passageText")
    options: list[Any] = Field(default_factory=list)
    selected_answer: Optional[Any] = Field(default=None, alias="selectedAnswer")
    selected_answer_index: Optional[int] = Field(default=None, alias="selectedAnswerIndex")
    selected_option_label: Optional[str] = Field(default=None, alias="selectedOptionLabel")
    correct_answer: Optional[Any] = Field(default=None, alias="correctAnswer")
    explanation: Optional[str] = None

    intent: Optional[str] = None
    context_type: Optional[str] = Field(default=None, alias="contextType")
    attempt_id: Optional[int] = Field(default=None, alias="attemptId")
    context: Optional[dict[str, Any]] = None
    question: Optional[dict[str, Any]] = None
    current_question: Optional[dict[str, Any]] = Field(default=None, alias="currentQuestion")


class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # Field chính cho FE cũ/mới
    content: str = ""
    answer: str = ""
    message: Optional[str] = None
    reply: Optional[str] = None

    conversation_id: Optional[int] = Field(default=None, alias="conversationId")
    role: str = "assistant"
    intent: str = "general"

    suggestions: list[str] = Field(default_factory=list)
    messages: list[ChatMessageDto] = Field(default_factory=list)

    requires_pro: bool = Field(default=False, alias="requiresPro")
    intent_confidence: Optional[float] = Field(default=None, alias="intentConfidence")
    intent_reason: Optional[str] = Field(default=None, alias="intentReason")
    context_missing: list[str] = Field(default_factory=list, alias="contextMissing")
