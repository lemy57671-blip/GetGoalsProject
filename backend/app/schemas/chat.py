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
    CORRECT_ANSWER_CHECK = "correct_answer_check"
    HOW_TO_SOLVE = "how_to_solve"
    WHY_CORRECT = "why_correct"
    OPTION_REASON = "option_reason"
    SELECTED_WRONG_REASON = "selected_wrong_reason"
    COMPARE_OPTIONS = "compare_options"
    FULL_OPTION_ANALYSIS = "full_option_analysis"
    TRANSLATION = "translation"
    OPTION_TRANSLATION = "option_translation"
    TRANSLATION_PIECE = "translation_piece"
    EXPLANATION = "explanation"
    EXPLANATION_SHORT = "explanation_short"
    EXPLANATION_SIMPLIFY = "explanation_simplify"
    SELECTED_ANSWER_CHECK = "selected_answer_check"
    TENSE_REQUIREMENT = "tense_requirement"
    WORD_FORM_REQUIREMENT = "word_form_requirement"
    VOCABULARY_MEANING = "vocabulary_meaning"
    VOCABULARY_EXPAND = "vocabulary_expand"
    GRAMMAR_RULE = "grammar_rule"
    GRAMMAR_FORMULA = "grammar_formula"
    GRAMMAR_EXPLANATION = "grammar_explanation"
    SIGNAL = "signal"
    SUMMARY = "summary"
    PARAPHRASE = "paraphrase"
    QUESTION_TYPE = "question_type"
    PART_STRATEGY = "part_strategy"
    TRAP = "trap"
    TRAP_EXPLANATION = "trap_explanation"
    TESTED_POINT = "tested_point"
    GRAMMAR_STRUCTURE = "grammar_structure"
    GRAMMAR_FORMULA_REQUEST = "grammar_formula_request"
    TARGET_COMPLETION_REQUEST = "target_completion_request"
    GRAMMAR_STRUCTURE_DEFINITION = "grammar_structure_definition"
    COLLOCATION_PREPOSITION_REQUEST = "collocation_preposition_request"
    RELATIVE_PRONOUN_REQUEST = "relative_pronoun_request"
    EXPLAIN = "explain"
    HINT = "hint"
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
    runtime_question_id: Optional[int] = Field(default=None, alias="runtimeQuestionId")
    runner_question_id: Optional[int] = Field(default=None, alias="runnerQuestionId")
    diagnostic_question_id: Optional[int] = Field(default=None, alias="diagnosticQuestionId")
    review_item_id: Optional[int] = Field(default=None, alias="reviewItemId")
    docx_question_id: Optional[int] = Field(default=None, alias="docxQuestionId")
    source_question_id: Optional[int] = Field(default=None, alias="sourceQuestionId")
    sql_id: Optional[int] = Field(default=None, alias="sqlId")

    question_number: Optional[int] = Field(default=None, alias="questionNumber")
    part: Optional[int] = None
    source: Optional[str] = None
    mode: Optional[str] = None
    prompt: Optional[str] = None
    question_text: Optional[str] = Field(default=None, alias="questionText")
    passage: Optional[Any] = None
    passage_text: Optional[str] = Field(default=None, alias="passageText")
    options: list[Any] = Field(default_factory=list)
    selected_answer: Optional[Any] = Field(default=None, alias="selectedAnswer")
    selected_answer_index: Optional[int] = Field(default=None, alias="selectedAnswerIndex")
    selected_option_label: Optional[str] = Field(default=None, alias="selectedOptionLabel")
    selected_option_key: Optional[str] = Field(default=None, alias="selectedOptionKey")
    selected_option_text: Optional[str] = Field(default=None, alias="selectedOptionText")
    correct_answer: Optional[Any] = Field(default=None, alias="correctAnswer")
    correct_answer_text: Optional[str] = Field(default=None, alias="correctAnswerText")
    correct_option_key: Optional[str] = Field(default=None, alias="correctOptionKey")
    correct_option_text: Optional[str] = Field(default=None, alias="correctOptionText")
    explanation: Optional[str] = None
    explanation_text: Optional[str] = Field(default=None, alias="explanationText")
    explanation_detail: Optional[str] = Field(default=None, alias="explanationDetail")
    translation_vi: Optional[str] = Field(default=None, alias="translationVi")
    final_translation_vi: Optional[str] = Field(default=None, alias="finalTranslationVi")
    raw_explanation: Optional[str] = Field(default=None, alias="rawExplanation")
    raw_block: Optional[str] = Field(default=None, alias="rawBlock")
    option_analysis: Optional[str] = Field(default=None, alias="optionAnalysis")
    vocabulary_notes: Optional[str] = Field(default=None, alias="vocabularyNotes")
    selected_text: Optional[str] = Field(default=None, alias="selectedText")
    current_highlighted_text: Optional[str] = Field(default=None, alias="currentHighlightedText")
    audio: Optional[Any] = None
    image: Optional[Any] = None
    skill: Optional[str] = None
    subskill: Optional[str] = None

    intent: Optional[str] = None
    answer_mode: Optional[str] = Field(default=None, alias="answerMode")
    use_sql_only: Optional[bool] = Field(default=None, alias="useSqlOnly")
    include_correct_answer: Optional[bool] = Field(default=None, alias="includeCorrectAnswer")
    context_type: Optional[str] = Field(default=None, alias="contextType")
    current_question_key: Optional[str] = Field(default=None, alias="currentQuestionKey")
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
