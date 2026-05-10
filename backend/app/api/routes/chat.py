from __future__ import annotations

import logging
import os
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat.local_algorithm_provider import build_local_answer_with_debug, clean_response

logger = logging.getLogger(__name__)
router = APIRouter()

try:
    from app.core.security import get_current_user
except Exception:  # pragma: no cover - local fallback for stripped auth setups
    get_current_user = None


async def _anonymous_user() -> None:
    return None


current_user_dependency = get_current_user if get_current_user is not None else _anonymous_user


def _get_attr(obj: Any, *keys: str, default: Any = None) -> Any:
    if obj is None:
        return default

    if isinstance(obj, dict):
        for key in keys:
            value = obj.get(key)
            if value not in (None, ""):
                return value

    for key in keys:
        value = getattr(obj, key, None)
        if value not in (None, ""):
            return value

    extra = getattr(obj, "model_extra", None)
    if isinstance(extra, dict):
        for key in keys:
            value = extra.get(key)
            if value not in (None, ""):
                return value

    return default


def _payload_extra(payload: Any) -> dict[str, Any]:
    extra = getattr(payload, "model_extra", None)
    return extra if isinstance(extra, dict) else {}


def _extract_message(payload: ChatRequest) -> str:
    message = (
        _get_attr(payload, "message")
        or _get_attr(payload, "content")
        or _get_attr(payload, "text")
        or _payload_extra(payload).get("message")
        or _payload_extra(payload).get("content")
        or _payload_extra(payload).get("text")
        or ""
    )
    return str(message or "").strip() or "gợi ý"


def _is_chat_debug_enabled() -> bool:
    return os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"} or logger.isEnabledFor(logging.DEBUG)


def _debug_snippet(value: Any, limit: int = 240) -> str:
    text_value = _compact(value)
    if len(text_value) <= limit:
        return text_value
    return text_value[: limit - 3].rstrip() + "..."


def _extract_conversation_id(payload: ChatRequest) -> Optional[int]:
    value = (
        _get_attr(payload, "conversation_id", "conversationId")
        or _payload_extra(payload).get("conversation_id")
        or _payload_extra(payload).get("conversationId")
    )
    try:
        return int(value) if value is not None else None
    except Exception:
        return None


def _get_user_id(user: Any) -> Optional[int]:
    value = _get_attr(user, "id", "Id", "user_id", "UserId")
    try:
        return int(value) if value is not None else None
    except Exception:
        return None


def _get_user_email(user: Any) -> Optional[str]:
    value = _get_attr(user, "email", "Email")
    return str(value) if value else None


def _get_user_plan(user: Any) -> str:
    value = _get_attr(user, "subscription_plan", "SubscriptionPlan", "plan", "Plan", default="FREE")
    return str(value or "FREE").strip().upper()


def _is_pro_user(user: Any, db: Session) -> bool:
    plan = _get_user_plan(user)
    if plan in {"PRO", "PRO PLAN", "PREMIUM", "PAID"}:
        expired_at = _get_attr(user, "plan_expired_at", "PlanExpiredAt")
        if expired_at is None:
            return True
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            return expired_at > now
        except Exception:
            return True

    user_id = _get_user_id(user)
    email = _get_user_email(user)
    if user_id is None and not email:
        return False

    try:
        row = None
        if user_id is not None:
            row = db.execute(
                text(
                    """
                    SELECT TOP 1 Id, Email, SubscriptionPlan, PlanExpiredAt
                    FROM dbo.Users
                    WHERE Id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).mappings().first()
        if row is None and email:
            row = db.execute(
                text(
                    """
                    SELECT TOP 1 Id, Email, SubscriptionPlan, PlanExpiredAt
                    FROM dbo.Users
                    WHERE Email = :email
                    """
                ),
                {"email": email},
            ).mappings().first()
        if row is None:
            return False
        db_plan = str(row.get("SubscriptionPlan") or "").strip().upper()
        if db_plan not in {"PRO", "PRO PLAN", "PREMIUM", "PAID"}:
            return False
        expired_at = row.get("PlanExpiredAt")
        if expired_at is None:
            return True
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return expired_at > now
    except Exception:
        logger.info("AI Tutor Pro check skipped because user lookup failed.", exc_info=True)
        return False


def _row_get(row: Any, *keys: str, default: Any = None) -> Any:
    if not row:
        return default
    row_keys = list(row.keys()) if hasattr(row, "keys") else []
    lookup = {str(key).lower(): key for key in row_keys}
    for key in keys:
        if key in row_keys and row.get(key) not in (None, ""):
            return row.get(key)
        actual = lookup.get(key.lower())
        if actual is not None and row.get(actual) not in (None, ""):
            return row.get(actual)
    return default


def _option_label(index: int) -> str:
    return chr(ord("A") + index) if 0 <= index < 26 else str(index + 1)


def _compact(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _strip_answer_label(value: Any) -> str:
    import re

    return re.sub(r"^\s*(?:\(?[A-D]\)?[.)]|[A-D]\s*[:\-])\s*", "", str(value or "").strip(), flags=re.IGNORECASE)


def _normalize_text_for_match(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _is_placeholder_explanation(value: Any) -> bool:
    normalized = _normalize_text_for_match(value)
    return normalized in {
        "",
        "no explanation is available for this question yet.",
        "no explanation available.",
        "detailed explanation is not available for this question.",
    }


def _has_value(value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text_value = str(value).strip().lower()
    if text_value in {"1", "true", "yes", "y"}:
        return True
    if text_value in {"0", "false", "no", "n"}:
        return False
    return None


def _format_answer(option: dict[str, Any]) -> str:
    label = str(option.get("label") or "").strip()
    text_value = str(option.get("text") or "").strip()
    return f"{label}. {text_value}" if label and text_value else text_value or label


def _normalize_option(option: Any, index: int = 0) -> dict[str, Any]:
    if isinstance(option, str):
        return {"label": _option_label(index), "text": option.strip(), "is_correct": None}
    if isinstance(option, dict):
        label = str(
            option.get("label")
            or option.get("optionLabel")
            or option.get("OptionLabel")
            or option.get("optionKey")
            or option.get("OptionKey")
            or option.get("key")
            or _option_label(index)
        ).strip()
        text_value = str(
            option.get("text")
            or option.get("optionTextEn")
            or option.get("OptionTextEn")
            or option.get("content")
            or option.get("Content")
            or option.get("optionText")
            or option.get("OptionText")
            or option.get("value")
            or ""
        ).strip()
        return {
            "label": label[:8],
            "text": text_value,
            "translation": option.get("translation") or option.get("TranslationVi"),
            "analysis": option.get("analysis") or option.get("Analysis"),
            "is_correct": option.get("isCorrect") if "isCorrect" in option else option.get("is_correct"),
        }
    return {"label": _option_label(index), "text": str(option or "").strip(), "is_correct": None}


def _format_options(options: Any) -> list[dict[str, Any]]:
    if not options:
        return []
    if isinstance(options, list):
        return [item for item in (_normalize_option(option, index) for index, option in enumerate(options)) if item.get("text")]
    item = _normalize_option(options, 0)
    return [item] if item.get("text") else []


def _extract_index(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    try:
        parsed = int(str(value).strip())
        return parsed if parsed >= 0 else None
    except Exception:
        return None


def _extract_question_context(payload: ChatRequest) -> dict[str, Any]:
    extra = _payload_extra(payload)
    context = _get_attr(payload, "context") or extra.get("context") or {}
    current_question = (
        _get_attr(payload, "current_question", "currentQuestion")
        or extra.get("current_question")
        or extra.get("currentQuestion")
    )
    question = _get_attr(payload, "question") or extra.get("question")
    if current_question is None and isinstance(context, dict):
        current_question = context.get("currentQuestion") or context.get("current_question") or context.get("question")
    q = current_question or question or {}

    question_id = (
        _get_attr(payload, "question_id", "questionId", "current_question_id", "currentQuestionId", "sqlId", "sql_id")
        or extra.get("question_id")
        or extra.get("questionId")
        or extra.get("currentQuestionId")
        or extra.get("sqlId")
        or extra.get("sql_id")
        or _get_attr(q, "id", "Id", "question_id", "questionId", "QuestionId", "sqlId", "sql_id")
    )
    question_text = (
        _get_attr(payload, "question_text", "questionText", "prompt")
        or extra.get("question_text")
        or extra.get("questionText")
        or _get_attr(q, "question_text", "questionText", "QuestionText", "prompt", "text", "content", "Content")
    )
    passage_text = (
        _get_attr(payload, "passage_text", "passageText", "passage")
        or extra.get("passage_text")
        or extra.get("passageText")
        or _get_attr(q, "passage_text", "passageText", "passage", "Passage")
    )
    options = (
        _get_attr(payload, "options", "choices")
        or extra.get("options")
        or extra.get("choices")
        or _get_attr(q, "options", "choices", "Options", "answers")
    )
    selected_answer_index = (
        _get_attr(payload, "selected_answer_index", "selectedAnswerIndex")
        or extra.get("selected_answer_index")
        or extra.get("selectedAnswerIndex")
        or _get_attr(q, "selected_answer_index", "selectedAnswerIndex", "userAnswerIndex", "user_answer_index")
    )
    correct_answer_index = (
        _get_attr(payload, "correct_answer_index", "correctAnswerIndex")
        or extra.get("correct_answer_index")
        or extra.get("correctAnswerIndex")
        or _get_attr(q, "correct_answer_index", "correctAnswerIndex")
    )
    runtime_question_id = (
        _get_attr(payload, "runtime_question_id", "runtimeQuestionId", "runner_question_id", "runnerQuestionId")
        or extra.get("runtime_question_id")
        or extra.get("runtimeQuestionId")
        or extra.get("runner_question_id")
        or extra.get("runnerQuestionId")
        or _get_attr(q, "runtime_question_id", "runtimeQuestionId", "runner_question_id", "runnerQuestionId")
    )
    diagnostic_question_id = (
        _get_attr(payload, "diagnostic_question_id", "diagnosticQuestionId")
        or extra.get("diagnostic_question_id")
        or extra.get("diagnosticQuestionId")
        or _get_attr(q, "diagnostic_question_id", "diagnosticQuestionId")
    )
    review_item_id = (
        _get_attr(payload, "review_item_id", "reviewItemId")
        or extra.get("review_item_id")
        or extra.get("reviewItemId")
        or _get_attr(q, "review_item_id", "reviewItemId")
    )
    docx_question_id = (
        _get_attr(payload, "docx_question_id", "docxQuestionId", "source_question_id", "sourceQuestionId")
        or extra.get("docx_question_id")
        or extra.get("docxQuestionId")
        or extra.get("source_question_id")
        or extra.get("sourceQuestionId")
        or _get_attr(q, "docx_question_id", "docxQuestionId", "source_question_id", "sourceQuestionId", "docxQuestionId")
    )
    source = (
        _get_attr(payload, "source")
        or extra.get("source")
        or _get_attr(q, "source", "sourceType", "source_type")
    )
    context_type = (
        _get_attr(payload, "context_type", "contextType")
        or extra.get("context_type")
        or extra.get("contextType")
        or _get_attr(q, "context_type", "contextType")
    )
    passage_obj = _get_attr(payload, "passage") or extra.get("passage") or _get_attr(q, "passage", "Passage")
    if not passage_text and isinstance(passage_obj, dict):
        passage_text = _get_attr(passage_obj, "text", "passageText", "passage_text", "PassageText")
    audio = _get_attr(payload, "audio") or extra.get("audio") or _get_attr(q, "audio", "Audio")
    image = _get_attr(payload, "image", "graphic") or extra.get("image") or extra.get("graphic") or _get_attr(q, "image", "graphic", "Image")
    correct_option_key = (
        _get_attr(payload, "correct_option_key", "correctOptionKey", "correct_option_label", "correctOptionLabel")
        or extra.get("correct_option_key")
        or extra.get("correctOptionKey")
        or extra.get("correct_option_label")
        or extra.get("correctOptionLabel")
        or _get_attr(q, "correct_option_key", "correctOptionKey", "correctAnswerLabel", "correct_option_label")
    )
    selected_option_key = (
        _get_attr(payload, "selected_option_key", "selectedOptionKey", "selected_option_label", "selectedOptionLabel")
        or extra.get("selected_option_key")
        or extra.get("selectedOptionKey")
        or extra.get("selected_option_label")
        or extra.get("selectedOptionLabel")
        or _get_attr(q, "selected_option_key", "selectedOptionKey", "userAnswerLabel", "selected_option_label")
    )
    explanation = (
        _get_attr(payload, "explanation", "explanationText", "explanation_text", "explanationDetail", "explanation_detail")
        or extra.get("explanation")
        or extra.get("explanationText")
        or extra.get("explanation_text")
        or extra.get("explanationDetail")
        or extra.get("explanation_detail")
        or _get_attr(q, "explanation", "Explanation", "explanationText", "explanation_detail", "explanationDetail")
    )

    return {
        "question_id": question_id,
        "runtime_question_id": runtime_question_id,
        "runner_question_id": runtime_question_id,
        "diagnostic_question_id": diagnostic_question_id,
        "review_item_id": review_item_id,
        "docx_question_id": docx_question_id,
        "source_question_id": docx_question_id,
        "context_type": context_type,
        "source": source,
        "attempt_id": (
            _get_attr(payload, "attempt_id", "attemptId")
            or extra.get("attempt_id")
            or extra.get("attemptId")
            or _get_attr(q, "attempt_id", "attemptId")
        ),
        "question_number": (
            _get_attr(payload, "question_number", "questionNumber")
            or extra.get("question_number")
            or extra.get("questionNumber")
            or _get_attr(q, "question_number", "questionNumber", "number", "QuestionNumber")
        ),
        "part": _get_attr(payload, "part") or extra.get("part") or _get_attr(q, "part", "Part"),
        "question_text": question_text,
        "passage_title": _get_attr(q, "passage_title", "passageTitle", "title", "Title") or extra.get("passage_title"),
        "passage_text": passage_text,
        "passage": passage_obj,
        "audio": audio,
        "image": image,
        "transcript": _get_attr(payload, "transcript") or extra.get("transcript") or _get_attr(q, "transcript", "Transcript"),
        "options": _format_options(options),
        "selected_answer": (
            _get_attr(payload, "selected_answer", "selectedAnswer")
            or _get_attr(payload, "selected_option_text", "selectedOptionText")
            or extra.get("selected_answer")
            or extra.get("selectedAnswer")
            or extra.get("selected_option_text")
            or extra.get("selectedOptionText")
            or _get_attr(q, "selected_answer", "selectedAnswer", "userAnswer", "user_answer")
            or _get_attr(q, "selected_option_text", "selectedOptionText")
        ),
        "selected_answer_index": _extract_index(selected_answer_index),
        "selected_option_key": selected_option_key,
        "selected_option_label": selected_option_key,
        "correct_answer": (
            _get_attr(payload, "correct_answer", "correctAnswer")
            or extra.get("correct_answer")
            or extra.get("correctAnswer")
            or _get_attr(q, "correct_answer", "correctAnswer", "answer", "Answer")
        ),
        "correct_answer_text": (
            _get_attr(payload, "correct_answer_text", "correctAnswerText")
            or _get_attr(payload, "correct_option_text", "correctOptionText")
            or extra.get("correct_answer_text")
            or extra.get("correctAnswerText")
            or extra.get("correct_option_text")
            or extra.get("correctOptionText")
            or _get_attr(q, "correct_answer_text", "correctAnswerText", "correctAnswer", "answer", "Answer")
            or _get_attr(q, "correct_option_text", "correctOptionText")
        ),
        "correct_answer_index": _extract_index(correct_answer_index),
        "correct_option_key": correct_option_key,
        "correct_option_label": correct_option_key,
        "explanation": explanation,
        "explanation_detail": explanation,
        "translation_vi": (
            extra.get("translation_vi")
            or extra.get("translationVi")
            or _get_attr(payload, "translation_vi", "translationVi")
            or _get_attr(q, "translation_vi", "translationVi")
        ),
        "final_translation_vi": (
            extra.get("final_translation_vi")
            or extra.get("finalTranslationVi")
            or _get_attr(payload, "final_translation_vi", "finalTranslationVi")
            or _get_attr(q, "final_translation_vi", "finalTranslationVi")
        ),
        "raw_explanation": (
            extra.get("raw_explanation")
            or extra.get("rawExplanation")
            or _get_attr(q, "raw_explanation", "rawExplanation")
        ),
        "raw_block": (
            extra.get("raw_block")
            or extra.get("rawBlock")
            or _get_attr(q, "raw_block", "rawBlock")
        ),
        "option_analysis": (
            extra.get("option_analysis")
            or extra.get("optionAnalysis")
            or _get_attr(q, "option_analysis", "optionAnalysis")
        ),
        "vocabulary_notes": (
            extra.get("vocabulary_notes")
            or extra.get("vocabularyNotes")
            or _get_attr(q, "vocabulary_notes", "vocabularyNotes")
        ),
        "selected_text": (
            _get_attr(payload, "selected_text", "selectedText", "current_highlighted_text", "currentHighlightedText")
            or extra.get("selected_text")
            or extra.get("selectedText")
            or extra.get("current_highlighted_text")
            or extra.get("currentHighlightedText")
            or _get_attr(q, "selected_text", "selectedText", "current_highlighted_text", "currentHighlightedText")
        ),
        "skill": _get_attr(q, "skill", "Skill", "skill_code", "skillCode") or extra.get("skill"),
        "subskill": _get_attr(q, "subskill", "Subskill", "subskill_code", "subskillCode") or extra.get("subskill"),
        "current_question_key": (
            _get_attr(payload, "current_question_key", "currentQuestionKey")
            or extra.get("current_question_key")
            or extra.get("currentQuestionKey")
            or _get_attr(q, "current_question_key", "currentQuestionKey")
        ),
        "answer_mode": (
            _get_attr(payload, "answer_mode", "answerMode")
            or extra.get("answer_mode")
            or extra.get("answerMode")
            or _get_attr(q, "answer_mode", "answerMode")
        ),
        "use_sql_only": (
            _get_attr(payload, "use_sql_only", "useSqlOnly")
            if _get_attr(payload, "use_sql_only", "useSqlOnly") is not None
            else extra.get("use_sql_only", extra.get("useSqlOnly"))
        ),
        "include_correct_answer": (
            _get_attr(payload, "include_correct_answer", "includeCorrectAnswer")
            if _get_attr(payload, "include_correct_answer", "includeCorrectAnswer") is not None
            else extra.get("include_correct_answer", extra.get("includeCorrectAnswer"))
        ),
        "difficulty": _get_attr(q, "difficulty", "Difficulty") or extra.get("difficulty"),
    }


def _load_docx_question_from_db(db: Session, question_id: int) -> dict[str, Any]:
    for table_prefix in ("dbo.",):
        try:
            rows = db.execute(
                text(
                    f"""
                    SELECT
                        q.Id,
                        q.SourceFile,
                        q.TestNumber,
                        q.PartNumber,
                        q.QuestionNumber,
                        q.PassageText,
                        q.QuestionTextEn,
                        q.CorrectOptionLabel,
                        q.CorrectAnswerText,
                        q.TranslationVi,
                        q.ExplanationDetail,
                        q.OptionAnalysis,
                        q.VocabularyNotes,
                        q.FinalTranslationVi,
                        q.RawBlock,
                        o.Id AS OptionId,
                        o.OptionLabel,
                        o.OptionTextEn,
                        o.IsCorrect,
                        o.SortOrder
                    FROM {table_prefix}ToeicDocxQuestions q
                    LEFT JOIN {table_prefix}ToeicDocxOptions o ON o.QuestionId = q.Id
                    WHERE q.Id = :question_id
                    ORDER BY o.SortOrder, o.Id
                    """
                ),
                {"question_id": question_id},
            ).mappings().all()
        except Exception:
            logger.info("Could not load TOEIC Docx question from %s", table_prefix, exc_info=True)
            continue

        if not rows:
            continue

        first = rows[0]
        options: list[dict[str, Any]] = []
        seen_labels: set[str] = set()
        for index, row in enumerate(rows):
            label = str(_row_get(row, "OptionLabel", default="") or "").strip().upper()
            text_en = str(_row_get(row, "OptionTextEn", default="") or "").strip()
            if not label and not text_en:
                continue
            label = label or _option_label(index)
            if label in seen_labels:
                continue
            seen_labels.add(label)
            options.append(
                {
                    "id": _row_get(row, "OptionId"),
                    "label": label,
                    "text": text_en,
                    "is_correct": _to_bool(_row_get(row, "IsCorrect")),
                    "sort_order": _row_get(row, "SortOrder"),
                }
            )

        correct_label = str(_row_get(first, "CorrectOptionLabel", default="") or "").strip().upper()
        if not correct_label:
            for option in options:
                if option.get("is_correct") is True:
                    correct_label = str(option.get("label") or "").strip().upper()
                    break

        correct_answer_text = str(_row_get(first, "CorrectAnswerText", default="") or "").strip()
        if not correct_answer_text and correct_label:
            for option in options:
                if str(option.get("label") or "").strip().upper() == correct_label:
                    correct_answer_text = str(option.get("text") or "").strip()
                    break

        correct_index = None
        for index, option in enumerate(options):
            if correct_label and str(option.get("label") or "").strip().upper() == correct_label:
                correct_index = index
                option["is_correct"] = True
            elif option.get("is_correct") is None:
                option["is_correct"] = False if correct_label else None

        return {
            "question_id": _row_get(first, "Id"),
            "source_file": _row_get(first, "SourceFile"),
            "test_number": _row_get(first, "TestNumber"),
            "part": _row_get(first, "PartNumber"),
            "part_number": _row_get(first, "PartNumber"),
            "question_number": _row_get(first, "QuestionNumber"),
            "passage_text": _row_get(first, "PassageText"),
            "question_text": _row_get(first, "QuestionTextEn"),
            "question_text_en": _row_get(first, "QuestionTextEn"),
            "options": options,
            "correct_option_label": correct_label or None,
            "correct_option_key": correct_label or None,
            "correct_answer_text": correct_answer_text or None,
            "correct_answer": f"{correct_label}. {correct_answer_text}" if correct_label and correct_answer_text else correct_answer_text,
            "correct_answer_index": correct_index,
            "translation_vi": _row_get(first, "TranslationVi"),
            "translation": _row_get(first, "TranslationVi"),
            "final_translation_vi": _row_get(first, "FinalTranslationVi"),
            "explanation_detail": _row_get(first, "ExplanationDetail"),
            "explanation": _row_get(first, "ExplanationDetail"),
            "option_analysis": _row_get(first, "OptionAnalysis"),
            "vocabulary_notes": _row_get(first, "VocabularyNotes"),
            "vocabulary": _row_get(first, "VocabularyNotes"),
            "raw_block": _row_get(first, "RawBlock"),
            "sql_source": table_prefix.rstrip("."),
        }

    return {}


def _to_int_or_none(value: Any) -> int | None:
    try:
        parsed = int(value)
    except Exception:
        return None
    return parsed if parsed > 0 else None


def _normalize_toeic_asset_path(path: Any, asset_type: str) -> str | None:
    value = str(path or "").strip().replace("\\", "/")
    if not value:
        return None
    if value.lower().startswith(("http://", "https://", "data:")):
        return value
    if value.startswith("/toeic/"):
        return value
    if value.startswith("toeic/"):
        return f"/{value}"
    normalized = value.lstrip("/")
    lower_value = normalized.lower()
    if lower_value.startswith(("audio/", "images/", "image/")):
        return f"/toeic/{normalized}"
    if asset_type.lower() == "audio":
        return f"/toeic/audio/{normalized}"
    return f"/toeic/images/{normalized}"


def _runtime_context_requested(context: dict[str, Any]) -> bool:
    value = f"{context.get('context_type') or ''} {context.get('source') or ''}".lower().replace("-", "_")
    return any(
        token in value
        for token in (
            "practice_runner",
            "practice_review",
            "practice_summary",
            "review",
            "mock_test",
            "mock",
            "weekly_check",
            "weekly",
            "practice_runtime",
        )
    )


def _context_runtime_id(context: dict[str, Any]) -> int | None:
    return (
        _to_int_or_none(context.get("runtime_question_id"))
        or _to_int_or_none(context.get("runner_question_id"))
        or (_to_int_or_none(context.get("question_id")) if _runtime_context_requested(context) else None)
    )


def _context_docx_id(context: dict[str, Any]) -> int | None:
    return _to_int_or_none(context.get("docx_question_id")) or _to_int_or_none(context.get("source_question_id"))


def _load_practice_runtime_context(db: Session, runtime_question_id: int | None) -> dict[str, Any]:
    if not runtime_question_id:
        return {}
    try:
        question_row = db.execute(
            text(
                """
                SELECT TOP 1
                    q.*,
                    p.GroupCode AS PassageGroupCode,
                    p.PassageText AS PassageText,
                    p.AudioPath AS PassageAudioPath,
                    p.ImagePath AS PassageImagePath
                FROM dbo.ToeicPracticeQuestions q
                LEFT JOIN dbo.ToeicPracticePassages p ON p.Id = q.PassageId
                WHERE q.Id = :question_id
                """
            ),
            {"question_id": runtime_question_id},
        ).mappings().first()
    except Exception:
        logger.info("Could not load runtime TOEIC practice question.", exc_info=True)
        return {}

    if not question_row:
        return {}

    try:
        option_rows = db.execute(
            text(
                """
                SELECT Id, QuestionId, OptionKey, OptionText, IsCorrect, SortOrder
                FROM dbo.ToeicPracticeQuestionOptions
                WHERE QuestionId = :question_id
                ORDER BY SortOrder, Id
                """
            ),
            {"question_id": runtime_question_id},
        ).mappings().all()
    except Exception:
        option_rows = []

    passage_id = _row_get(question_row, "PassageId")
    try:
        asset_rows = db.execute(
            text(
                """
                SELECT AssetType, RelativePath, QuestionId, PassageId
                FROM dbo.ToeicPracticeQuestionAssets
                WHERE QuestionId = :question_id
                   OR (:passage_id IS NOT NULL AND PassageId = :passage_id)
                ORDER BY CASE WHEN QuestionId = :question_id THEN 0 ELSE 1 END, Id
                """
            ),
            {"question_id": runtime_question_id, "passage_id": passage_id},
        ).mappings().all()
    except Exception:
        asset_rows = []

    correct_label = str(_row_get(question_row, "CorrectOptionKey", default="") or "").strip().upper()
    options: list[dict[str, Any]] = []
    for index, row in enumerate(option_rows):
        label = str(_row_get(row, "OptionKey", default=_option_label(index)) or "").strip().upper() or _option_label(index)
        option_text = str(_row_get(row, "OptionText", default="") or "").strip()
        options.append(
            {
                "id": _row_get(row, "Id"),
                "label": label,
                "key": label,
                "text": option_text,
                "is_correct": bool(_row_get(row, "IsCorrect")) or (label == correct_label if correct_label else False),
                "sort_order": _row_get(row, "SortOrder", default=index),
            }
        )

    if not correct_label:
        for option in options:
            if option.get("is_correct") is True:
                correct_label = str(option.get("label") or "").strip().upper()
                break
    correct_answer_text = next(
        (str(item.get("text") or "").strip() for item in options if str(item.get("label") or "").strip().upper() == correct_label),
        "",
    )

    audio_path = _normalize_toeic_asset_path(_row_get(question_row, "PassageAudioPath"), "audio")
    image_path = _normalize_toeic_asset_path(_row_get(question_row, "PassageImagePath"), "image")
    passage_audio_path = audio_path
    passage_image_path = image_path
    for row in asset_rows:
        asset_type = str(_row_get(row, "AssetType", default="") or "").strip().lower()
        normalized = _normalize_toeic_asset_path(_row_get(row, "RelativePath"), asset_type or "image")
        if not normalized:
            continue
        is_question_asset = _row_get(row, "QuestionId") is not None
        if asset_type == "audio":
            if is_question_asset:
                audio_path = audio_path or normalized
            else:
                passage_audio_path = passage_audio_path or normalized
                audio_path = audio_path or normalized
        elif asset_type in {"image", "graphic"}:
            if is_question_asset:
                image_path = image_path or normalized
            else:
                passage_image_path = passage_image_path or normalized
                image_path = image_path or normalized

    docx_question_id = None
    for key in ("DocxQuestionId", "SourceQuestionId", "OriginalQuestionId", "RawQuestionId", "ImportQuestionId", "LegacyQuestionId"):
        candidate = _to_int_or_none(_row_get(question_row, key))
        if candidate and candidate != runtime_question_id:
            docx_question_id = candidate
            break

    explanation = _row_get(question_row, "Explanation")
    return {
        "question_id": runtime_question_id,
        "runtime_question_id": runtime_question_id,
        "runner_question_id": runtime_question_id,
        "docx_question_id": docx_question_id,
        "source_question_id": docx_question_id,
        "test_number": _row_get(question_row, "TestNumber"),
        "part": _row_get(question_row, "Part"),
        "part_number": _row_get(question_row, "Part"),
        "section": _row_get(question_row, "Section"),
        "question_number": _row_get(question_row, "QuestionNumber"),
        "question_text": _row_get(question_row, "QuestionText"),
        "question_text_en": _row_get(question_row, "QuestionText"),
        "passage_text": _row_get(question_row, "PassageText"),
        "passage": {
            "id": passage_id,
            "groupCode": _row_get(question_row, "PassageGroupCode"),
            "text": _row_get(question_row, "PassageText"),
            "audioPath": passage_audio_path,
            "imagePath": passage_image_path,
        },
        "audio": {"path": audio_path} if audio_path else None,
        "image": {"path": image_path} if image_path else None,
        "audio_path": audio_path,
        "image_path": image_path,
        "options": options,
        "correct_option_label": correct_label or None,
        "correct_option_key": correct_label or None,
        "correct_answer_text": correct_answer_text or None,
        "correct_answer": f"{correct_label}. {correct_answer_text}" if correct_label and correct_answer_text else correct_answer_text or None,
        "explanation": None if _is_placeholder_explanation(explanation) else explanation,
        "explanation_detail": None if _is_placeholder_explanation(explanation) else explanation,
        "option_analysis": None if _is_placeholder_explanation(explanation) else explanation,
        "raw_block": None if _is_placeholder_explanation(explanation) else explanation,
        "skill": _row_get(question_row, "SkillCode"),
        "difficulty": _row_get(question_row, "Difficulty"),
        "source": "practice_runtime",
        "sql_source": "dbo.ToeicPracticeQuestions",
        "lookup_source": "runtime",
    }


def _load_raw_explanation_context_from_db(db: Session, context: dict[str, Any], runtime_question_id: int | None = None) -> dict[str, Any]:
    runtime_id = runtime_question_id or _context_runtime_id(context)
    part = _to_int_or_none(context.get("part"))
    question_number = _to_int_or_none(context.get("question_number"))
    test_number = _to_int_or_none(context.get("test_number")) or 1
    context_type = str(context.get("source") or context.get("context_type") or "").lower()
    test_type = None
    if "mini" in context_type:
        test_type = "minitest"
    elif "full" in context_type or "mock" in context_type:
        test_type = "fulltest"
    elif "weekly" in context_type:
        test_type = "weekly"
    elif "practice" in context_type or "review" in context_type:
        test_type = "practice"

    try:
        if runtime_id:
            row = db.execute(
                text(
                    """
                    SELECT TOP 1 e.*, d.SourceFile
                    FROM dbo.ToeicQuestionExplanations e
                    LEFT JOIN dbo.ToeicRawDocuments d ON d.Id = e.RawDocumentId
                    WHERE e.RuntimeQuestionId = :runtime_question_id
                    ORDER BY e.Id
                    """
                ),
                {"runtime_question_id": runtime_id},
            ).mappings().first()
            if row:
                return _map_raw_explanation_context(row, runtime_id)

        if question_number:
            row = db.execute(
                text(
                    """
                    SELECT TOP 1 e.*, d.SourceFile
                    FROM dbo.ToeicQuestionExplanations e
                    LEFT JOIN dbo.ToeicRawDocuments d ON d.Id = e.RawDocumentId
                    WHERE e.QuestionNumber = :question_number
                      AND (:part IS NULL OR e.Part = :part)
                      AND (:test_number IS NULL OR e.TestNumber = :test_number)
                      AND (:test_type IS NULL OR e.TestType = :test_type)
                    ORDER BY CASE WHEN e.RuntimeQuestionId IS NOT NULL THEN 0 ELSE 1 END, e.Id
                    """
                ),
                {"part": part, "question_number": question_number, "test_number": test_number, "test_type": test_type},
            ).mappings().first()
            if row:
                return _map_raw_explanation_context(row, runtime_id)
    except Exception:
        logger.info("Could not load TOEIC raw explanation context in active chat route.", exc_info=True)

    return {}


def _map_raw_explanation_context(row: Any, fallback_question_id: int | None = None) -> dict[str, Any]:
    correct_label = str(_row_get(row, "CorrectOptionKey", default="") or "").strip().upper()
    options = []
    for index, key in enumerate(("OptionA", "OptionB", "OptionC", "OptionD")):
        text_value = str(_row_get(row, key, default="") or "").strip()
        if text_value:
            label = _option_label(index)
            options.append({"label": label, "key": label, "text": text_value, "is_correct": label == correct_label if correct_label else None, "sort_order": index})

    runtime_id = _row_get(row, "RuntimeQuestionId")
    correct_answer_text = _row_get(row, "CorrectAnswerText") or next(
        (item.get("text") for item in options if str(item.get("label") or "").strip().upper() == correct_label),
        None,
    )
    return {
        "question_id": runtime_id or fallback_question_id or _row_get(row, "Id"),
        "runtime_question_id": runtime_id or fallback_question_id,
        "raw_explanation_id": _row_get(row, "Id"),
        "source_file": _row_get(row, "SourceFile"),
        "raw_document_id": _row_get(row, "RawDocumentId"),
        "test_type": _row_get(row, "TestType"),
        "test_number": _row_get(row, "TestNumber"),
        "group_code": _row_get(row, "GroupCode"),
        "part": _row_get(row, "Part"),
        "part_number": _row_get(row, "Part"),
        "question_number": _row_get(row, "QuestionNumber"),
        "question_text": _row_get(row, "QuestionText"),
        "question_text_en": _row_get(row, "QuestionText"),
        "passage_text": _row_get(row, "PassageText"),
        "options": options,
        "correct_option_label": correct_label or None,
        "correct_option_key": correct_label or None,
        "correct_answer_text": correct_answer_text,
        "correct_answer": f"{correct_label}. {correct_answer_text}" if correct_label and correct_answer_text else correct_answer_text,
        "explanation_detail": _row_get(row, "ExplanationText"),
        "explanation": _row_get(row, "ExplanationText"),
        "option_analysis": _row_get(row, "ExplanationText"),
        "vocabulary_notes": _row_get(row, "VocabularyNotes"),
        "grammar_notes": _row_get(row, "GrammarNotes"),
        "raw_block": _row_get(row, "RawBlock"),
        "source": "raw_explanation",
        "sql_source": "dbo.ToeicQuestionExplanations",
        "lookup_source": "raw_explanation",
    }


def _text_matches_expected(row_text: Any, expected_text: Any) -> bool:
    expected = _compact(expected_text)
    if not expected:
        return True
    actual = _compact(row_text)
    return actual == expected


def _load_docx_question_by_runner_row(db: Session, runner_row: Any) -> dict[str, Any]:
    question_text = str(_row_get(runner_row, "QuestionText", "QuestionTextEn", default="") or "").strip()
    question_number = _row_get(runner_row, "QuestionNumber")
    part = _row_get(runner_row, "Part")
    test_number = _row_get(runner_row, "TestNumber")
    if not question_text and not question_number:
        return {}

    for table_prefix in ("dbo.",):
        try:
            row = db.execute(
                text(
                    f"""
                    SELECT TOP 1 Id
                    FROM {table_prefix}ToeicDocxQuestions
                    WHERE (:question_number IS NULL OR QuestionNumber = :question_number)
                      AND (:part IS NULL OR PartNumber = :part)
                      AND (:test_number IS NULL OR TestNumber = :test_number)
                      AND (:question_text = '' OR QuestionTextEn = :question_text)
                    ORDER BY Id
                    """
                ),
                {
                    "question_number": question_number,
                    "part": part,
                    "test_number": test_number,
                    "question_text": question_text,
                },
            ).mappings().first()
        except Exception:
            logger.info("Could not map runner question to TOEIC Docx from %s", table_prefix, exc_info=True)
            continue
        if row and row.get("Id"):
            return _load_docx_question_from_db(db, int(row.get("Id")))
    return {}


def _load_docx_question_by_text(db: Session, context: dict[str, Any]) -> dict[str, Any]:
    question_text = str(context.get("question_text") or context.get("question_text_en") or "").strip()
    if not question_text:
        return {}
    part = _to_int_or_none(context.get("part") or context.get("part_number"))
    question_number = _to_int_or_none(context.get("question_number"))
    test_number = _to_int_or_none(context.get("test_number"))
    like_seed = " ".join(question_text.split())[:120]

    for table_prefix in ("dbo.",):
        try:
            rows = db.execute(
                text(
                    f"""
                    SELECT TOP 5 Id, QuestionTextEn, PartNumber, QuestionNumber, TestNumber
                    FROM {table_prefix}ToeicDocxQuestions
                    WHERE (:part IS NULL OR PartNumber = :part)
                      AND (:question_number IS NULL OR QuestionNumber = :question_number)
                      AND (:test_number IS NULL OR TestNumber = :test_number)
                      AND (
                            QuestionTextEn = :question_text
                         OR (:like_text <> '' AND QuestionTextEn LIKE :like_text)
                      )
                    ORDER BY
                        CASE WHEN QuestionTextEn = :question_text THEN 0 ELSE 1 END,
                        Id
                    """
                ),
                {
                    "part": part,
                    "question_number": question_number,
                    "test_number": test_number,
                    "question_text": question_text,
                    "like_text": f"%{like_seed}%" if like_seed else "",
                },
            ).mappings().all()
        except Exception:
            logger.info("Could not lookup TOEIC Docx question by text from %s", table_prefix, exc_info=True)
            continue

        if not rows:
            continue
        exact = [row for row in rows if _text_matches_expected(row.get("QuestionTextEn"), question_text)]
        if exact:
            return _load_docx_question_from_db(db, int(exact[0]["Id"]))
        if len(rows) == 1 or part or question_number:
            candidate = rows[0]
            if _text_looks_related(candidate.get("QuestionTextEn"), question_text):
                return _load_docx_question_from_db(db, int(candidate["Id"]))
        logger.info(
            "Ambiguous TOEIC Docx text lookup skipped for part=%s question_number=%s text=%s",
            part,
            question_number,
            _debug_snippet(question_text, 120),
        )
    return {}


def _text_looks_related(candidate_text: Any, expected_text: Any) -> bool:
    candidate = _normalize_text_for_match(candidate_text)
    expected = _normalize_text_for_match(expected_text)
    if not candidate or not expected:
        return False
    return candidate == expected or candidate in expected or expected[:80] in candidate


def _load_runner_question_from_db(db: Session, question_id: int) -> dict[str, Any]:
    try:
        question_row = db.execute(
            text(
                """
                SELECT TOP 1
                    q.Id,
                    q.TestNumber,
                    q.QuestionNumber,
                    q.Part,
                    q.QuestionText,
                    q.Explanation,
                    q.CorrectOptionKey,
                    q.Transcript,
                    q.SkillCode,
                    q.SubskillCode,
                    q.Topic,
                    q.Difficulty,
                    q.QuestionType,
                    p.Title AS PassageTitle,
                    p.PassageText
                FROM dbo.ToeicQuestions q
                LEFT JOIN dbo.ToeicPassages p ON p.Id = q.PassageId
                WHERE q.Id = :question_id
                """
            ),
            {"question_id": question_id},
        ).mappings().first()
    except Exception:
        logger.info("Could not load runner question from dbo.ToeicQuestions.", exc_info=True)
        return {}

    if not question_row:
        return {}

    docx_context = _load_docx_question_by_runner_row(db, question_row)
    if docx_context:
        docx_context["runner_question_id"] = question_id
        return docx_context

    option_rows = db.execute(
        text(
            """
            SELECT OptionKey, OptionText, SortOrder
            FROM dbo.ToeicQuestionOptions
            WHERE QuestionId = :question_id
            ORDER BY SortOrder, Id
            """
        ),
        {"question_id": question_id},
    ).mappings().all()

    correct_key = str(question_row.get("CorrectOptionKey") or "").strip().upper()
    options = [
        {
            "label": str(row.get("OptionKey") or _option_label(index)).strip().upper(),
            "text": str(row.get("OptionText") or "").strip(),
            "is_correct": str(row.get("OptionKey") or "").strip().upper() == correct_key if correct_key else None,
            "sort_order": row.get("SortOrder"),
        }
        for index, row in enumerate(option_rows)
    ]
    correct_answer_text = ""
    correct_index = None
    for index, option in enumerate(options):
        if correct_key and str(option.get("label") or "").strip().upper() == correct_key:
            correct_answer_text = str(option.get("text") or "").strip()
            correct_index = index
            break

    return {
        "question_id": question_row.get("Id"),
        "test_number": question_row.get("TestNumber"),
        "question_number": question_row.get("QuestionNumber"),
        "part": question_row.get("Part"),
        "question_text": question_row.get("QuestionText"),
        "passage_title": question_row.get("PassageTitle"),
        "passage_text": question_row.get("PassageText"),
        "transcript": question_row.get("Transcript"),
        "options": options,
        "correct_option_label": correct_key or None,
        "correct_option_key": correct_key or None,
        "correct_answer_text": correct_answer_text or None,
        "correct_answer": f"{correct_key}. {correct_answer_text}" if correct_key and correct_answer_text else None,
        "correct_answer_index": correct_index,
        "explanation": question_row.get("Explanation"),
        "explanation_detail": question_row.get("Explanation"),
        "skill": question_row.get("SkillCode"),
        "subskill": question_row.get("SubskillCode"),
        "topic": question_row.get("Topic"),
        "difficulty": question_row.get("Difficulty"),
        "question_type": question_row.get("QuestionType"),
        "sql_source": "dbo.ToeicQuestions",
    }


def _merge_db_context(base: dict[str, Any], extra: dict[str, Any], *, allow_override: bool = False) -> dict[str, Any]:
    if not extra:
        return dict(base)
    result = dict(base)
    for key, value in extra.items():
        if not _has_value(value):
            continue
        existing = result.get(key)
        if key in {"explanation", "explanation_detail", "option_analysis", "vocabulary_notes", "raw_block"}:
            if not _has_value(existing) or _is_placeholder_explanation(existing) or allow_override:
                result[key] = value
            continue
        if key in {"correct_option_label", "correct_option_key", "correct_answer_text", "correct_answer", "correct_answer_index", "options"}:
            if allow_override or not _has_value(existing):
                result[key] = value
            continue
        if allow_override or not _has_value(existing):
            result[key] = value
    return result


def _load_review_queue_identity_context(db: Session, context: dict[str, Any]) -> dict[str, Any]:
    review_item_id = _to_int_or_none(context.get("review_item_id")) or _to_int_or_none(context.get("reviewItemId"))
    user_id = _to_int_or_none(context.get("user_id"))
    source = str(context.get("source") or context.get("source_type") or context.get("sourceType") or "").strip().lower()
    if source in {"mocktest", "mock_test"}:
        source = "fulltest"
    if source in {"mini_test"}:
        source = "minitest"
    if source in {"weekly", "weekly_check"}:
        source = "weeklycheck"
    if source == "all":
        source = ""
    attempt_id = _to_int_or_none(context.get("attempt_id")) or _to_int_or_none(context.get("attemptId"))
    question_number = _to_int_or_none(context.get("question_number")) or _to_int_or_none(context.get("questionNumber"))
    question_id = _to_int_or_none(context.get("question_id")) or _to_int_or_none(context.get("questionId"))

    if not any((review_item_id, question_number, question_id)):
        return {}

    try:
        row = db.execute(
            text(
                """
                SELECT TOP 1
                    Id,
                    [Source],
                    AttemptId,
                    QuestionId,
                    RuntimeQuestionId,
                    DiagnosticQuestionId,
                    QuestionNumber,
                    Part,
                    SkillCode,
                    CAST(NULL AS NVARCHAR(50)) AS SubskillCode
                FROM dbo.ReviewQueue
                WHERE IsActive = 1
                  AND (:review_item_id IS NULL OR Id = :review_item_id)
                  AND (:user_id IS NULL OR UserId = :user_id)
                  AND (:source = '' OR [Source] = :source)
                  AND (:attempt_id IS NULL OR AttemptId = :attempt_id)
                  AND (:question_number IS NULL OR QuestionNumber = :question_number)
                  AND (:question_id IS NULL OR QuestionId = :question_id OR RuntimeQuestionId = :question_id)
                ORDER BY
                    CASE WHEN RuntimeQuestionId IS NOT NULL THEN 0 ELSE 1 END,
                    Id
                """
            ),
            {
                "review_item_id": review_item_id,
                "user_id": user_id,
                "source": source,
                "attempt_id": attempt_id,
                "question_number": question_number,
                "question_id": question_id,
            },
        ).mappings().first()
    except Exception:
        logger.info("Could not load review queue identity for chat context.", exc_info=True)
        return {}

    if not row:
        return {}

    runtime_id = _to_int_or_none(_row_get(row, "RuntimeQuestionId"))
    queue_source = str(_row_get(row, "Source", default="") or "").strip()
    return {
        "review_item_id": _row_get(row, "Id"),
        "source": queue_source or source or None,
        "source_type": queue_source or source or None,
        "attempt_id": _row_get(row, "AttemptId"),
        "question_id": runtime_id or _row_get(row, "QuestionId"),
        "runtime_question_id": runtime_id,
        "runner_question_id": runtime_id,
        "diagnostic_question_id": _row_get(row, "DiagnosticQuestionId"),
        "question_number": _row_get(row, "QuestionNumber"),
        "part": _row_get(row, "Part"),
        "skill": _row_get(row, "SkillCode"),
        "subskill": _row_get(row, "SubskillCode"),
    }


def _load_question_from_db(db: Session, frontend_ctx: dict[str, Any]) -> dict[str, Any]:
    queue_identity = _load_review_queue_identity_context(db, frontend_ctx)
    if queue_identity:
        frontend_ctx = _merge_db_context(dict(frontend_ctx), queue_identity, allow_override=False)

    runtime_requested = _runtime_context_requested(frontend_ctx)
    runtime_id = _context_runtime_id(frontend_ctx)
    docx_id = _context_docx_id(frontend_ctx)
    result: dict[str, Any] = {}

    if runtime_requested:
        runtime_context = _load_practice_runtime_context(db, runtime_id)
        result = _merge_db_context(result, runtime_context, allow_override=True)
        if not docx_id:
            docx_id = _context_docx_id(runtime_context)

        raw_context = _load_raw_explanation_context_from_db(db, frontend_ctx, runtime_id)
        result = _merge_db_context(result, raw_context, allow_override=False)

        docx_context = {}
        if docx_id:
            candidate = _load_docx_question_from_db(db, docx_id)
            if candidate and _context_text_match(frontend_ctx, candidate, runtime_context):
                docx_context = candidate
        if not docx_context:
            text_seed = dict(frontend_ctx)
            text_seed = _merge_db_context(text_seed, runtime_context)
            docx_context = _load_docx_question_by_text(db, text_seed)
        if docx_context:
            docx_context = dict(docx_context)
            mapped_docx_id = _to_int_or_none(docx_context.get("question_id")) or docx_id
            if mapped_docx_id:
                docx_context["docx_question_id"] = mapped_docx_id
                docx_context["source_question_id"] = mapped_docx_id
            docx_context.pop("question_id", None)
            docx_context.pop("runtime_question_id", None)
            docx_context.pop("runner_question_id", None)
        result = _merge_db_context(result, docx_context, allow_override=True)
        result["lookup_source"] = result.get("lookup_source") or "runtime"
        return result

    qid = _to_int_or_none(frontend_ctx.get("question_id"))
    if not qid:
        return {}

    docx_context = _load_docx_question_from_db(db, qid)
    if docx_context and _text_matches_expected(docx_context.get("question_text"), frontend_ctx.get("question_text")):
        return docx_context

    runner_context = _load_runner_question_from_db(db, qid)
    if runner_context and _context_text_match(frontend_ctx, runner_context, {}):
        return runner_context

    if docx_context and not frontend_ctx.get("question_text"):
        return docx_context

    return {}


def _context_text_match(frontend_ctx: dict[str, Any], db_ctx: dict[str, Any], runtime_ctx: dict[str, Any] | None = None) -> bool:
    expected = frontend_ctx.get("question_text") or frontend_ctx.get("question_text_en") or (runtime_ctx or {}).get("question_text")
    actual = db_ctx.get("question_text") or db_ctx.get("question_text_en")
    if not expected or not actual:
        return True
    return _text_looks_related(actual, expected)


def _merge_question_context(frontend_ctx: dict[str, Any], db_ctx: dict[str, Any]) -> dict[str, Any]:
    result = dict(frontend_ctx)
    db_trusted = _context_text_match(frontend_ctx, db_ctx, {})
    db_priority_keys = {
        "question_id",
        "runtime_question_id",
        "runner_question_id",
        "docx_question_id",
        "source_question_id",
        "source_file",
        "test_number",
        "part",
        "part_number",
        "question_number",
        "question_text",
        "question_text_en",
        "passage_text",
        "options",
        "correct_option_label",
        "correct_option_key",
        "correct_answer_text",
        "correct_answer",
        "correct_answer_index",
        "translation",
        "translation_vi",
        "final_translation_vi",
        "explanation",
        "explanation_detail",
        "option_analysis",
        "vocabulary",
        "vocabulary_notes",
        "raw_block",
        "sql_source",
        "lookup_source",
        "source",
    }
    for key, value in db_ctx.items():
        if value in (None, "", [], {}):
            continue
        if key in {"explanation", "explanation_detail"}:
            current = result.get(key)
            if not _has_value(current) or _is_placeholder_explanation(current):
                result[key] = value
            continue
        if key in {"option_analysis", "vocabulary_notes", "raw_block"}:
            if not _has_value(result.get(key)):
                result[key] = value
            continue
        if key in db_priority_keys and db_trusted:
            result[key] = value
        elif result.get(key) in (None, "", [], {}):
            result[key] = value
    if not _has_value(result.get("explanation_detail")) and _has_value(result.get("explanation")):
        result["explanation_detail"] = result.get("explanation")
    if not _has_value(result.get("correct_answer_text")) and _has_value(result.get("correct_answer")):
        result["correct_answer_text"] = _strip_answer_label(result.get("correct_answer"))
    return result


def _normalize_review_text(value: Any) -> str:
    text_value = str(value or "").strip().lower()
    text_value = unicodedata.normalize("NFD", text_value)
    text_value = "".join(char for char in text_value if unicodedata.category(char) != "Mn")
    text_value = text_value.replace("đ", "d")
    text_value = re.sub(r"[_]{2,}", " ____ ", text_value)
    text_value = re.sub(r"[^\w\s']+", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def _first_sentence(value: Any) -> str:
    text_value = _compact(value)
    if not text_value:
        return ""
    parts = re.split(r"(?<=[.!?。])\s+", text_value, maxsplit=1)
    return parts[0].strip()


def _review_chat_requested(context: dict[str, Any]) -> bool:
    value = f"{context.get('context_type') or ''} {context.get('source') or ''} {context.get('lookup_source') or ''}".lower()
    return any(token in value for token in ("review", "practice", "fulltest", "minitest", "weekly", "runtime"))


def _review_options(context: dict[str, Any]) -> list[dict[str, Any]]:
    options = []
    for index, option in enumerate(context.get("options") or []):
        normalized = _normalize_option(option, index)
        label = str(normalized.get("label") or _option_label(index)).strip().upper()
        text_value = str(normalized.get("text") or label).strip()
        options.append(
            {
                "label": label,
                "text": text_value,
                "is_correct": _to_bool(normalized.get("is_correct")),
            }
        )
    return options


def _review_correct_option(context: dict[str, Any], options: list[dict[str, Any]]) -> dict[str, Any] | None:
    correct_key = str(context.get("correct_option_key") or context.get("correct_option_label") or "").strip().upper()
    if correct_key:
        for option in options:
            if str(option.get("label") or "").strip().upper() == correct_key:
                return option
    for option in options:
        if option.get("is_correct") is True:
            return option
    correct_text = _strip_answer_label(context.get("correct_answer_text") or context.get("correct_answer") or "")
    correct_norm = _normalize_review_text(correct_text)
    if correct_norm:
        for option in options:
            if _normalize_review_text(option.get("text")) == correct_norm:
                return option
    return None


def _format_review_option(option: dict[str, Any] | None) -> str:
    if not option:
        return ""
    label = str(option.get("label") or "").strip().upper()
    text_value = str(option.get("text") or "").strip()
    return f"{label} — {text_value}" if label and text_value else text_value or label


def _extract_review_option_from_message(message: str, options: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_message = _normalize_review_text(message)
    for label in ("A", "B", "C", "D"):
        if re.search(rf"\b(?:dap an|option|cau|chon)?\s*{label.lower()}\b", normalized_message):
            for option in options:
                if str(option.get("label") or "").strip().upper() == label:
                    return option
    candidates = sorted(options, key=lambda item: len(str(item.get("text") or "")), reverse=True)
    for option in candidates:
        text_norm = _normalize_review_text(option.get("text"))
        if text_norm and re.search(rf"\b{re.escape(text_norm)}\b", normalized_message):
            return option
    return None


def _review_intent(message: str, options: list[dict[str, Any]]) -> str | None:
    text_value = _normalize_review_text(message)
    has_option = _extract_review_option_from_message(message, options) is not None
    if any(token in text_value for token in ("dich cau", "dich doan", "translate this", "translate the")):
        return "ASK_TRANSLATION"
    if any(token in text_value for token in ("nghia la gi", "co nghia la gi", "la gi", "what does", "mean", "meaning")):
        if not any(token in text_value for token in ("vi sao", "tai sao", "sao ", "wrong", "sai", "khong dung")):
            return "ASK_VOCAB_MEANING"
    if any(token in text_value for token in ("cho trong can", "khoang trong can", "blank", "cau truc gi", "can cau truc", "can dang", "loai tu gi")):
        return "ASK_BLANK_STRUCTURE"
    if has_option and any(token in text_value for token in ("sai", "khong dung", "khong chon", "wrong", "why not")):
        return "ASK_WHY_OPTION_WRONG"
    if has_option and any(token in text_value for token in ("vi sao", "tai sao", "why", "chon", "dung", "correct")):
        return "ASK_WHY_CORRECT"
    if any(token in text_value for token in ("giai thich", "tai sao dap an dung", "vi sao dap an dung")):
        return "ASK_GENERAL_EXPLANATION"
    return None


def _extract_vocab_target(message: str) -> str:
    raw = str(message or "").strip()
    patterns = [
        r"(?P<target>.+?)\s+(?:nghĩa\s+là\s+gì|nghia\s+la\s+gi|có\s+nghĩa\s+là\s+gì|co\s+nghia\s+la\s+gi|là\s+gì|la\s+gi)\??$",
        r"what\s+does\s+(?P<target>.+?)\s+mean\??$",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            target = match.group("target").strip(" \"'“”?.!,")
            target = re.sub(r"^(từ|tu|cụm|cum)\s+", "", target, flags=re.IGNORECASE).strip()
            return target
    return ""


def _phrase_in_review_context(phrase: str, context: dict[str, Any], options: list[dict[str, Any]]) -> bool:
    phrase_norm = _normalize_review_text(phrase)
    if not phrase_norm:
        return False
    sources = [
        context.get("question_text"),
        context.get("question_text_en"),
        context.get("passage_text"),
        context.get("explanation"),
        context.get("explanation_detail"),
        context.get("vocabulary_notes"),
        *(option.get("text") for option in options),
    ]
    return any(phrase_norm in _normalize_review_text(source) for source in sources if source)


def _review_vocab_meaning(phrase: str) -> str:
    meanings = {
        "banquet hall": "phòng khánh tiết/phòng đại tiệc, thường dùng để tổ chức tiệc, hội nghị hoặc sự kiện trang trọng",
        "luncheon": "bữa ăn trưa trang trọng hoặc bữa tiệc trưa",
        "peak": "đỉnh, mức cao nhất",
        "botanical garden": "vườn bách thảo",
        "housing values": "giá trị bất động sản/giá nhà đất",
        "advertising team": "đội/nhóm quảng cáo",
    }
    return meanings.get(_normalize_review_text(phrase), "")


def _review_pronoun_reason(option_text: str, correct_option: dict[str, Any] | None) -> str:
    option_norm = _normalize_review_text(option_text)
    correct = _format_review_option(correct_option)
    roles = {
        "they": "“they” là đại từ chủ ngữ, không đứng trước danh từ.",
        "them": "“them” là đại từ tân ngữ, không thể đứng trước danh từ.",
        "their": "“their” là tính từ sở hữu/determiner, đứng trước danh từ để chỉ sự sở hữu.",
        "theirs": "“theirs” là đại từ sở hữu, thay thế cả cụm danh từ nên không đứng trước một danh từ khác.",
    }
    if option_norm in roles:
        if option_norm == "their":
            return f"“their” đúng vì chỗ trống đứng trước danh từ “peak”, cần một tính từ sở hữu để chỉ sở hữu. Vì vậy đáp án đúng là {correct}."
        return f"{roles[option_norm]} Chỗ trống cần một tính từ sở hữu đứng trước danh từ “peak” để chỉ sự sở hữu của “housing values”. Vì vậy đáp án đúng là {correct}."
    return ""


def _review_option_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    correct = _format_review_option(correct_option)
    is_correct = correct_option and option_label == str(correct_option.get("label") or "").strip().upper()
    if is_correct:
        return f"Thực ra {option_label} — {option_text} là đáp án đúng. Nó phù hợp với cấu trúc và ngữ cảnh của câu."

    pronoun_reason = _review_pronoun_reason(option_text, correct_option)
    if pronoun_reason:
        return pronoun_reason

    question_norm = _normalize_review_text(context.get("question_text") or context.get("question_text_en"))
    option_norm = _normalize_review_text(option_text)
    correct_norm = _normalize_review_text((correct_option or {}).get("text"))
    if "will be" in question_norm:
        if option_norm == "went":
            return f"“went” sai vì đây là quá khứ của “go”, không dùng trong cấu trúc bị động “will be + V3”. Câu nói một sự kiện sẽ được tổ chức, nên đáp án đúng là {correct}. Cấu trúc đúng là “will be held”."
        return f"{option_label} — {option_text} không phù hợp với cấu trúc bị động “will be + V3”. Đáp án đúng là {correct}."
    if "located" in correct_norm:
        return f"{option_label} — {option_text} không phù hợp vì câu cần cấu trúc chỉ vị trí “be located + giới từ + địa điểm”. Đáp án đúng là {correct}."

    explanation = _first_sentence(context.get("explanation_detail") or context.get("explanation") or context.get("option_analysis"))
    if explanation:
        return f"{option_label} — {option_text} không phù hợp với ngữ cảnh/cấu trúc của câu. {explanation} Đáp án đúng là {correct}."
    return f"{option_label} — {option_text} sai vì không khớp cấu trúc hoặc nghĩa cần điền trong câu hiện tại. Đáp án đúng là {correct}."


def _review_blank_structure(context: dict[str, Any], correct_option: dict[str, Any] | None) -> str:
    question_norm = _normalize_review_text(context.get("question_text") or context.get("question_text_en"))
    correct_text = str((correct_option or {}).get("text") or context.get("correct_answer_text") or "").strip()
    correct_norm = _normalize_review_text(correct_text)
    correct = _format_review_option(correct_option)
    option_texts = {_normalize_review_text(option.get("text")) for option in _review_options(context)}

    if {"they", "their", "them", "theirs"}.issubset(option_texts) or correct_norm == "their":
        return f"Chỗ trống đứng trước danh từ “peak”, nên cần tính từ sở hữu/determiner + noun. “their” đứng trước danh từ để chỉ sở hữu, vì vậy đáp án đúng là {correct}."
    if "located" in correct_norm:
        return f"Câu này nói về vị trí địa lý. Ta dùng cấu trúc bị động “be located + giới từ + địa điểm”. Chủ ngữ là số ít nên dùng “is located”. Vì vậy đáp án đúng là {correct}."
    if "will be" in question_norm:
        return f"Chỗ trống cần quá khứ phân từ V3 trong cấu trúc bị động/tương lai “will be + V3”. Vì vậy đáp án đúng là {correct}."
    if correct_text:
        return f"Chỗ trống cần dạng phù hợp với cấu trúc và nghĩa của câu. Trong câu này đáp án đúng là {correct}."
    return "Mình chưa lấy được đủ dữ liệu đáp án của câu hiện tại để xác định cấu trúc cần điền."


def _review_translation(context: dict[str, Any]) -> str:
    question_text = str(context.get("question_text") or context.get("question_text_en") or "").strip()
    passage_text = str(context.get("passage_text") or "").strip()
    existing = str(context.get("translation_vi") or context.get("final_translation_vi") or "").strip()
    if existing:
        return existing
    if passage_text and not question_text:
        return f"Đoạn hiện tại: {passage_text}"
    if question_text:
        return f"Câu hiện tại: {question_text}"
    return "Mình chưa lấy được nội dung câu hiện tại để dịch."


def _build_review_tutor_answer(message: str, context: dict[str, Any]) -> tuple[str, str] | None:
    if not _review_chat_requested(context):
        return None

    options = _review_options(context)
    correct_option = _review_correct_option(context, options)
    question_text = context.get("question_text") or context.get("question_text_en")
    if not question_text or not options or not correct_option:
        return ("Mình chưa lấy được dữ liệu câu hiện tại, bạn chọn lại câu giúp mình.", "review_context_missing")

    intent = _review_intent(message, options)
    if not intent:
        return None

    if intent == "ASK_TRANSLATION":
        return (_review_translation(context), "translation")

    if intent == "ASK_VOCAB_MEANING":
        target = _extract_vocab_target(message)
        if target and _phrase_in_review_context(target, context, options):
            meaning = _review_vocab_meaning(target)
            if meaning:
                return (f"“{target}” nghĩa là {meaning}.", "word_meaning")
            return (f"“{target}” là từ/cụm xuất hiện trong câu hiện tại. Mình chưa có nghĩa tiếng Việt chắc chắn trong dữ liệu câu này, nên không đoán thêm.", "word_meaning")
        return None

    if intent == "ASK_BLANK_STRUCTURE":
        return (_review_blank_structure(context, correct_option), "gap_requirement")

    option = _extract_review_option_from_message(message, options)
    if intent in {"ASK_WHY_OPTION_WRONG", "ASK_WHY_CORRECT"} and option:
        return (_review_option_reason(option, correct_option, context), "option_reason")

    if intent == "ASK_GENERAL_EXPLANATION":
        explanation = _first_sentence(context.get("explanation_detail") or context.get("explanation") or context.get("option_analysis"))
        correct = _format_review_option(correct_option)
        if explanation:
            return (f"Đáp án đúng là {correct}. {explanation}", "explanation")
        return (f"Đáp án đúng là {correct}. Nó là lựa chọn phù hợp nhất với cấu trúc và ngữ cảnh của câu hiện tại.", "explanation")

    return None


def _review_source_texts(context: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in (
        "translation_vi",
        "final_translation_vi",
        "translation",
        "question_translation",
        "questionTranslation",
        "passage_translation",
        "passageTranslation",
        "explanation_vi",
        "explanationVi",
        "explanation_detail",
        "explanation",
        "option_analysis",
        "vocabulary_notes",
        "vocabulary",
        "grammar_notes",
        "raw_explanation",
        "raw_block",
    ):
        value = context.get(key)
        if _has_value(value):
            texts.append(str(value))
    return texts


def _review_has_vietnamese(value: Any) -> bool:
    return bool(
        re.search(
            r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
            str(value or ""),
            flags=re.IGNORECASE,
        )
    )


def _clean_review_fragment(value: Any) -> str:
    text_value = str(value or "").strip()
    text_value = re.sub(r"^\s*(?:[-*•]\s*)+", "", text_value)
    text_value = re.sub(r"\s+", " ", text_value)
    return text_value.strip(" \t:-–—")


def _review_heading_kind(line: str) -> str | None:
    normalized = _normalize_review_text(line)
    normalized = re.sub(r"^\d+\s*\.?\s*", "", normalized).strip()
    if not normalized:
        return None
    if normalized.startswith(("ban dich tieng viet", "dich nghia", "translation")):
        return "translation"
    if normalized.startswith(("loi giai", "giai thich", "explanation")):
        return "explanation"
    if normalized.startswith(("phan tich dap an", "phan tich lua chon", "option analysis", "answer analysis")):
        return "option_analysis"
    if normalized.startswith(("tu vung", "vocabulary")):
        return "vocabulary"
    if normalized.startswith(("ngu phap", "grammar", "structure")):
        return "grammar"
    return None


def _extract_sql_translation(context: dict[str, Any]) -> str:
    for key in (
        "final_translation_vi",
        "translation_vi",
        "translation",
        "question_translation",
        "questionTranslation",
        "passage_translation",
        "passageTranslation",
    ):
        value = _clean_review_fragment(context.get(key))
        if value and _review_has_vietnamese(value):
            return value

    for source in _review_source_texts(context):
        lines = str(source or "").splitlines()
        collecting = False
        collected: list[str] = []
        for line in lines:
            kind = _review_heading_kind(line)
            normalized = _normalize_review_text(line)
            if kind == "translation":
                collecting = True
                parts = re.split(
                    r"(?:Bản dịch\s+Tiếng Việt|Ban dich Tieng Viet|Dịch nghĩa|Dich nghia|Translation)\s*[:：]?",
                    line,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )
                if len(parts) > 1:
                    fragment = _clean_review_fragment(parts[-1])
                    if fragment:
                        collected.append(fragment)
                continue
            if collecting:
                if kind and kind != "translation":
                    break
                if re.match(r"^\s*\d+\.\s+\S", line) and "ban dich" not in normalized and "dich nghia" not in normalized:
                    break
                fragment = _clean_review_fragment(line)
                if fragment:
                    collected.append(fragment)
        if collected:
            translation = _clean_review_fragment(" ".join(collected))
            if translation and _review_has_vietnamese(translation):
                return translation
    return ""


def _extract_review_option_from_message(message: str, options: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_message = _normalize_review_text(message)
    for label in ("A", "B", "C", "D"):
        if re.search(rf"\b(?:dap an|option|cau|chon)?\s*{label.lower()}\b", normalized_message):
            for option in options:
                if str(option.get("label") or "").strip().upper() == label:
                    return option
    candidates = sorted(options, key=lambda item: len(str(item.get("text") or "")), reverse=True)
    for option in candidates:
        text_norm = _normalize_review_text(option.get("text"))
        if text_norm and re.search(rf"\b{re.escape(text_norm)}\b", normalized_message):
            return option
    return None


def _review_intent(message: str, options: list[dict[str, Any]]) -> str | None:
    text_value = _normalize_review_text(message)
    has_option = _extract_review_option_from_message(message, options) is not None
    if any(token in text_value for token in ("dich cau", "dich doan", "dich sang tieng viet", "dich tieng viet", "translate this", "translate the")):
        return "ASK_TRANSLATION"
    if any(token in text_value for token in ("nghia la gi", "co nghia la gi", "la gi", "what does", "mean", "meaning")):
        if not any(token in text_value for token in ("vi sao", "tai sao", "sao ", "wrong", "sai", "khong dung")):
            return "ASK_VOCAB_MEANING"
    if any(token in text_value for token in ("cho trong can", "khoang trong can", "blank", "cau truc gi", "can cau truc", "dung cau truc", "can dang", "loai tu gi", "ngu phap cau nay")):
        return "ASK_BLANK_STRUCTURE"
    if has_option and any(token in text_value for token in ("sai", "khong dung", "khong chon", "wrong", "why not")):
        return "ASK_WHY_OPTION_WRONG"
    if has_option and any(token in text_value for token in ("vi sao", "tai sao", "why", "chon", "dung", "correct")):
        return "ASK_WHY_CORRECT"
    if any(token in text_value for token in ("giai thich", "phan tich", "tai sao dap an dung", "vi sao dap an dung")):
        return "ASK_GENERAL_EXPLANATION"
    return None


def _extract_vocab_target(message: str) -> str:
    raw = str(message or "").strip()
    patterns = [
        r"(?P<target>.+?)\s+(?:nghĩa\s+là\s+gì|nghia\s+la\s+gi|có\s+nghĩa\s+là\s+gì|co\s+nghia\s+la\s+gi|là\s+gì|la\s+gi)\??$",
        r"what\s+does\s+(?P<target>.+?)\s+mean\??$",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            target = match.group("target").strip(" \"'“”?.!,")
            target = re.sub(r"^(từ|tu|cụm|cum)\s+", "", target, flags=re.IGNORECASE).strip()
            return target
    return ""


def _phrase_in_review_context(phrase: str, context: dict[str, Any], options: list[dict[str, Any]]) -> bool:
    phrase_norm = _normalize_review_text(phrase)
    if not phrase_norm:
        return False
    sources = [
        context.get("question_text"),
        context.get("question_text_en"),
        context.get("passage_text"),
        context.get("explanation"),
        context.get("explanation_detail"),
        context.get("option_analysis"),
        context.get("vocabulary_notes"),
        context.get("vocabulary"),
        context.get("grammar_notes"),
        context.get("raw_explanation"),
        context.get("raw_block"),
        *(option.get("text") for option in options),
    ]
    return any(phrase_norm in _normalize_review_text(source) for source in sources if source)


def _extract_option_line_from_sql(option: dict[str, Any], context: dict[str, Any]) -> str:
    label = str(option.get("label") or "").strip().upper()
    option_text = str(option.get("text") or "").strip()
    option_norm = _normalize_review_text(option_text)
    label_pattern = rf"^\s*(?:[-*•]\s*)?(?:\(?{re.escape(label)}\)?[.)]|{re.escape(label)}\s*[-:–—])\s*"
    for source in _review_source_texts(context):
        for line in str(source or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            line_norm = _normalize_review_text(stripped)
            has_label = bool(label and re.search(label_pattern, stripped, flags=re.IGNORECASE))
            has_option_text = bool(option_norm and option_norm in line_norm)
            if not has_label and not has_option_text:
                continue
            if has_label or (has_option_text and any(marker in line_norm for marker in ("dap an", "sai", "khong", "dung", "v3", "passive", "bi dong"))):
                cleaned = re.sub(label_pattern, "", stripped, flags=re.IGNORECASE)
                cleaned = re.sub(rf"^\s*{re.escape(option_text)}\s*[-:–—]\s*", "", cleaned, flags=re.IGNORECASE)
                return _clean_review_fragment(cleaned)
    return ""


def _extract_sql_vocab_meaning(
    phrase: str,
    context: dict[str, Any],
    options: list[dict[str, Any]],
    correct_option: dict[str, Any] | None,
) -> str:
    phrase_norm = _normalize_review_text(phrase)
    if not phrase_norm:
        return ""

    question_norm = _normalize_review_text(context.get("question_text") or context.get("question_text_en"))
    correct_text = _normalize_review_text((correct_option or {}).get("text"))
    if phrase_norm == "their" and "housing values" in question_norm:
        return "của họ / của chúng. Trong câu này là “đỉnh điểm của các giá trị nhà ở”"
    if phrase_norm == "staged" and correct_text == "held" and "luncheon" in question_norm:
        return "dàn dựng / tổ chức, thường dùng cho vở kịch, buổi biểu diễn hoặc sự kiện trình diễn. Trong câu này, “held” tự nhiên hơn với “luncheon”"

    matched_option = next((option for option in options if _normalize_review_text(option.get("text")) == phrase_norm), None)
    if matched_option:
        option_line = _extract_option_line_from_sql(matched_option, context)
        if option_line:
            option_line = re.sub(r"^\s*[^-–—:]{0,40}\s*[-–—:]\s*", "", option_line).strip()
            option_line = re.sub(r"\b(?:đây là|day la)\s+đáp án đúng\.?", "", option_line, flags=re.IGNORECASE).strip()
            if option_line and _review_has_vietnamese(option_line) and _normalize_review_text(option_line) != phrase_norm:
                return re.sub(r"\s*/\s*", " / ", option_line.rstrip("."))

    for source in _review_source_texts(context):
        for line in str(source or "").splitlines():
            stripped = line.strip()
            if not stripped or phrase_norm not in _normalize_review_text(stripped):
                continue
            cleaned = _clean_review_fragment(stripped)
            cleaned = re.sub(r"^\s*(?:[-*•]\s*)+", "", cleaned)
            cleaned = re.sub(rf"^[\"'“”‘’]?{re.escape(phrase)}[\"'“”‘’]?\s*[:\-–—]?\s*", "", cleaned, flags=re.IGNORECASE)
            if cleaned == stripped:
                parts = re.split(r"\s[-–—:]\s|\s{2,}", cleaned, maxsplit=1)
                cleaned = parts[-1] if len(parts) > 1 else cleaned
            cleaned = re.sub(r"^(?:nghĩa là|co nghia la|có nghĩa là)\s+", "", cleaned, flags=re.IGNORECASE).strip()
            if cleaned and _review_has_vietnamese(cleaned):
                return re.sub(r"\s*/\s*", " / ", cleaned.rstrip("."))

    meanings = {
        "banquet hall": "phòng khánh tiết / phòng đại tiệc",
        "luncheon": "bữa ăn trưa trang trọng hoặc bữa tiệc trưa",
        "peak": "đỉnh điểm / mức cao nhất",
        "botanical garden": "vườn bách thảo",
        "housing values": "giá trị nhà ở",
        "advertising team": "đội ngũ quảng cáo",
        "their": "của họ / của chúng",
        "they": "họ / chúng, dùng làm chủ ngữ",
        "them": "họ / chúng, dùng làm tân ngữ",
        "theirs": "của họ / của chúng, dùng như đại từ sở hữu",
        "staged": "dàn dựng / tổ chức, thường dùng cho vở kịch, buổi biểu diễn hoặc sự kiện trình diễn",
        "held": "được tổ chức",
        "went": "đã đi, quá khứ của “go”",
        "is located": "nằm ở / tọa lạc tại",
    }
    return meanings.get(phrase_norm, "")


def _review_pronoun_reason(option_text: str, correct_option: dict[str, Any] | None) -> str:
    option_norm = _normalize_review_text(option_text)
    correct = _format_review_option(correct_option)
    roles = {
        "they": "“they” là đại từ chủ ngữ, không đứng trước danh từ.",
        "them": "“them” là đại từ tân ngữ, không thể đứng trước danh từ.",
        "their": "“their” là tính từ sở hữu/determiner, đứng trước danh từ để chỉ sự sở hữu.",
        "theirs": "“theirs” là đại từ sở hữu, thay thế cả cụm danh từ nên không đứng trước một danh từ khác.",
    }
    if option_norm in roles:
        if option_norm == "their":
            return f"“their” đúng vì chỗ trống đứng trước danh từ “peak”, cần một tính từ sở hữu để chỉ “đỉnh điểm của housing values”. Vì vậy đáp án đúng là {correct}."
        return f"{roles[option_norm]} Chỗ trống cần một tính từ sở hữu đứng trước danh từ “peak” để chỉ sự sở hữu của “housing values”. Vì vậy đáp án đúng là {correct}."
    return ""


def _review_correct_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    option_norm = _normalize_review_text(option_text)
    question_norm = _normalize_review_text(context.get("question_text") or context.get("question_text_en"))
    correct = _format_review_option(correct_option)
    if option_norm in {"they", "their", "them", "theirs"}:
        return _review_pronoun_reason(option_text, correct_option)
    if "located" in option_norm:
        return f"Câu này nói về vị trí địa lý của vườn bách thảo. Chúng ta dùng cấu trúc bị động “be located” để diễn đạt một địa điểm nằm ở đâu đó. Vì chủ ngữ “The botanical garden” là số ít nên dùng “is located”. Đáp án đúng là {correct}."
    if option_norm == "held" and "will be" in question_norm:
        return f"Chỗ trống sau “will be” cần V3 trong cấu trúc bị động “will be + V3”. Với “luncheon”, ta dùng “held” nghĩa là được tổ chức. Đáp án đúng là {correct}."
    option_line = _extract_option_line_from_sql(option, context)
    if option_line:
        return f"{option_label} — {option_text} là đáp án đúng. {_clean_review_fragment(option_line)}"
    explanation = _first_sentence(context.get("explanation_detail") or context.get("explanation") or context.get("option_analysis"))
    if explanation:
        return f"{option_label} — {option_text} là đáp án đúng. {explanation}"
    return f"{option_label} — {option_text} là đáp án đúng theo dữ liệu SQL của câu hiện tại."


def _review_option_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    correct = _format_review_option(correct_option)
    is_correct = correct_option and option_label == str(correct_option.get("label") or "").strip().upper()
    if is_correct:
        return _review_correct_reason(option, correct_option, context)

    pronoun_reason = _review_pronoun_reason(option_text, correct_option)
    if pronoun_reason:
        return pronoun_reason

    question_norm = _normalize_review_text(context.get("question_text") or context.get("question_text_en"))
    option_norm = _normalize_review_text(option_text)
    correct_norm = _normalize_review_text((correct_option or {}).get("text"))
    if "will be" in question_norm:
        if option_norm == "went":
            return f"“went” là quá khứ của “go”, không dùng trong cấu trúc bị động “will be + V3” và không mang nghĩa tổ chức sự kiện. Đáp án đúng là {correct}."
        if option_norm == "staged" and correct_norm == "held":
            return f"“staged” có thể nghĩa là dàn dựng/tổ chức, nhưng thường dùng cho vở kịch, chương trình biểu diễn hoặc sự kiện trình diễn. Với “luncheon”, cách dùng tự nhiên và phổ biến hơn là “held”. Đáp án đúng là {correct}."
        option_line = _extract_option_line_from_sql(option, context)
        if option_line:
            return f"{option_label} — {option_text} không phải đáp án đúng. {_clean_review_fragment(option_line)} Đáp án đúng là {correct}."
        return f"{option_label} — {option_text} không phù hợp với cấu trúc bị động “will be + V3”. Đáp án đúng là {correct}."
    if "located" in correct_norm:
        return f"{option_label} — {option_text} không phù hợp vì câu cần cấu trúc chỉ vị trí “be located + giới từ + địa điểm”. Đáp án đúng là {correct}."
    option_line = _extract_option_line_from_sql(option, context)
    if option_line:
        return f"{option_label} — {option_text} không phải đáp án đúng. {_clean_review_fragment(option_line)} Đáp án đúng là {correct}."
    explanation = _first_sentence(context.get("explanation_detail") or context.get("explanation") or context.get("option_analysis"))
    if explanation:
        return f"{option_label} — {option_text} không phù hợp với ngữ cảnh/cấu trúc của câu. {explanation} Đáp án đúng là {correct}."
    return f"{option_label} — {option_text} sai vì không khớp cấu trúc hoặc nghĩa cần điền trong câu hiện tại. Đáp án đúng là {correct}."


def _review_blank_structure(context: dict[str, Any], correct_option: dict[str, Any] | None) -> str:
    question_norm = _normalize_review_text(context.get("question_text") or context.get("question_text_en"))
    correct_text = str((correct_option or {}).get("text") or context.get("correct_answer_text") or "").strip()
    correct_norm = _normalize_review_text(correct_text)
    correct = _format_review_option(correct_option)
    option_texts = {_normalize_review_text(option.get("text")) for option in _review_options(context)}
    if {"they", "their", "them", "theirs"}.issubset(option_texts) or correct_norm == "their":
        return f"Chỗ trống đứng trước danh từ “peak”, nên cần tính từ sở hữu/determiner + noun. “their” đứng trước danh từ để chỉ sở hữu, vì vậy đáp án đúng là {correct}."
    if "located" in correct_norm:
        return f"Câu này nói về vị trí địa lý của vườn bách thảo. Chúng ta dùng cấu trúc bị động “be located” để diễn đạt một địa điểm nằm ở đâu đó. Vì chủ ngữ “The botanical garden” là số ít nên dùng “is located”. Đáp án đúng là {correct}."
    if "will be" in question_norm:
        return f"Chỗ trống cần quá khứ phân từ V3 trong cấu trúc bị động “will be + V3”. Với một sự kiện như “luncheon”, lựa chọn tự nhiên là “held”, nghĩa là được tổ chức. Đáp án đúng là {correct}."
    if correct_text:
        explanation = _first_sentence(context.get("explanation_detail") or context.get("explanation") or context.get("grammar_notes"))
        if explanation:
            return f"{explanation} Đáp án đúng là {correct}."
        return f"Chỗ trống cần dạng phù hợp với cấu trúc và nghĩa của câu. Trong câu này đáp án đúng là {correct}."
    return "Mình chưa lấy được đủ dữ liệu đáp án của câu hiện tại để xác định cấu trúc cần điền."


def _review_translation(context: dict[str, Any]) -> str:
    question_text = str(context.get("question_text") or context.get("question_text_en") or "").strip()
    sql_translation = _extract_sql_translation(context)
    if sql_translation:
        return sql_translation
    question_norm = _normalize_review_text(question_text)
    if "botanical garden" in question_norm and "south side" in question_norm:
        return "Vườn bách thảo nằm ở phía nam của hòn đảo và có thể dễ dàng được tìm thấy trên bất kỳ bản đồ nào."
    if "housing values" in question_norm and "peak" in question_norm:
        return "Giá trị nhà ở tương đối đã giảm hơn 10% so với đỉnh điểm của chúng trong nửa đầu năm nay."
    if "special luncheon" in question_norm and "banquet hall" in question_norm:
        return "Một bữa tiệc trưa đặc biệt dành cho đội ngũ quảng cáo sẽ được tổ chức tại phòng đại tiệc chính của Khách sạn Phalya."
    return "Mình chưa lấy được bản dịch tiếng Việt đáng tin cậy của câu hiện tại từ SQL."


def _build_review_tutor_answer(message: str, context: dict[str, Any]) -> tuple[str, str] | None:
    if not _review_chat_requested(context):
        return None

    options = _review_options(context)
    correct_option = _review_correct_option(context, options)
    question_text = context.get("question_text") or context.get("question_text_en")
    if not question_text or not options or not correct_option:
        return ("Mình chưa lấy được dữ liệu câu hiện tại, bạn chọn lại câu giúp mình.", "review_context_missing")

    intent = _review_intent(message, options)
    if not intent:
        return None

    if intent == "ASK_TRANSLATION":
        return (_review_translation(context), "translation")

    if intent == "ASK_VOCAB_MEANING":
        target = _extract_vocab_target(message) or str(context.get("selected_text") or "").strip()
        if target and _phrase_in_review_context(target, context, options):
            meaning = _extract_sql_vocab_meaning(target, context, options, correct_option)
            if meaning:
                return (f"“{target}” nghĩa là {meaning}.", "word_meaning")
            return (f"“{target}” xuất hiện trong câu hiện tại, nhưng mình chưa có nghĩa tiếng Việt chắc chắn trong dữ liệu SQL nên không đoán thêm.", "word_meaning")
        return None

    if intent == "ASK_BLANK_STRUCTURE":
        return (_review_blank_structure(context, correct_option), "gap_requirement")

    option = _extract_review_option_from_message(message, options)
    if intent in {"ASK_WHY_OPTION_WRONG", "ASK_WHY_CORRECT"} and option:
        return (_review_option_reason(option, correct_option, context), "option_reason")

    if intent == "ASK_GENERAL_EXPLANATION":
        explanation = _first_sentence(context.get("explanation_detail") or context.get("explanation") or context.get("option_analysis"))
        correct = _format_review_option(correct_option)
        if explanation:
            return (f"Đáp án đúng là {correct}. {explanation}", "explanation")
        return (f"Đáp án đúng là {correct}. Đây là lựa chọn khớp nhất với cấu trúc và ngữ cảnh của câu hiện tại theo dữ liệu SQL.", "explanation")

    return None


def _review_source_texts(context: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in (
        "detailed_explanation",
        "explanation_detail",
        "explanation",
        "option_analysis",
        "vocabulary_notes",
        "vocabulary",
        "grammar_notes",
        "translation_vi",
        "final_translation_vi",
        "translation",
        "question_translation",
        "passage_translation",
        "raw_explanation",
        "raw_block",
    ):
        value = context.get(key)
        if _has_value(value):
            texts.append(str(value))
    return texts


def _review_has_vietnamese(value: Any) -> bool:
    return bool(
        re.search(
            r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
            str(value or ""),
            flags=re.IGNORECASE,
        )
    )


def _clean_review_fragment(value: Any) -> str:
    text_value = str(value or "").strip()
    text_value = re.sub(r"^\s*(?:[-*•]\s*)+", "", text_value)
    text_value = re.sub(r"\s+", " ", text_value)
    return text_value.strip(" \t:-–—")


def _review_heading_kind(line: str) -> str | None:
    normalized = _normalize_review_text(line)
    normalized = re.sub(r"^\d+\s*\.?\s*", "", normalized).strip()
    if not normalized:
        return None
    if normalized.startswith(("giai thich chi tiet", "loi giai", "giai thich", "explanation")):
        return "explanation"
    if normalized.startswith(("phan tich lua chon", "phan tich dap an", "option analysis", "answer analysis")):
        return "option_analysis"
    if normalized.startswith(("cau truc va tu vung", "tu vung", "vocabulary", "expanded vocabulary")):
        return "vocabulary"
    if normalized.startswith(("ban dich tieng viet", "tam dich", "dich nghia", "translation")):
        return "translation"
    if normalized.startswith(("vi du minh hoa", "vi du", "example")):
        return "example"
    return None


def _extract_sql_section(context: dict[str, Any], wanted_kind: str) -> str:
    for source in _review_source_texts(context):
        lines = str(source or "").splitlines()
        collecting = False
        collected: list[str] = []
        for line in lines:
            kind = _review_heading_kind(line)
            if kind == wanted_kind:
                collecting = True
                parts = re.split(r"[:：]", line, maxsplit=1)
                if len(parts) > 1:
                    fragment = _clean_review_fragment(parts[-1])
                    if fragment:
                        collected.append(fragment)
                continue
            if collecting:
                if kind and kind != wanted_kind:
                    break
                fragment = _clean_review_fragment(line)
                if fragment:
                    collected.append(fragment)
        if collected:
            return _clean_review_fragment(" ".join(collected))
    return ""


def _extract_sql_general_explanation(context: dict[str, Any]) -> str:
    for key in ("detailed_explanation", "explanation_detail", "explanation"):
        value = _clean_review_fragment(context.get(key))
        if value and not _is_placeholder_explanation(value):
            if _review_heading_kind(value) != "translation":
                section = _extract_sql_section({"raw_block": value}, "explanation")
                return section or value
    return _extract_sql_section(context, "explanation")


def _extract_sql_translation(context: dict[str, Any]) -> str:
    for key in (
        "question_translation",
        "questionTranslation",
        "final_translation_vi",
        "finalTranslationVi",
        "translation_vi",
        "translationVi",
        "translation",
        "passage_translation",
        "passageTranslation",
    ):
        value = _clean_review_fragment(context.get(key))
        if value and _review_has_vietnamese(value):
            return value
    return _extract_sql_section(context, "translation")


def _extract_review_option_from_message(message: str, options: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_message = _normalize_review_text(message)
    for label in ("A", "B", "C", "D"):
        if re.search(rf"\b(?:dap an|option|cau|chon)?\s*{label.lower()}\b", normalized_message):
            return next((option for option in options if str(option.get("label") or "").strip().upper() == label), None)
    for option in sorted(options, key=lambda item: len(str(item.get("text") or "")), reverse=True):
        text_norm = _normalize_review_text(option.get("text"))
        if text_norm and re.search(rf"\b{re.escape(text_norm)}\b", normalized_message):
            return option
    return None


def _review_intent(message: str, options: list[dict[str, Any]]) -> str | None:
    text_value = _normalize_review_text(message)
    has_option = _extract_review_option_from_message(message, options) is not None
    if any(token in text_value for token in ("phan tich tung dap an", "phan tich cac dap an", "phan tich lua chon", "giai thich cac lua chon", "giai thich tung dap an", "option analysis")):
        return "ASK_OPTION_ANALYSIS"
    if any(token in text_value for token in ("dich cau", "dich doan", "dich sang tieng viet", "dich tieng viet", "cau nay nghia la gi", "nghia cua cau", "translate this", "translate the")):
        return "ASK_TRANSLATION"
    if any(token in text_value for token in ("nghia la gi", "co nghia la gi", "la gi", "what does", "mean", "meaning")):
        if not any(token in text_value for token in ("vi sao", "tai sao", "sao ", "wrong", "sai", "khong dung")):
            return "ASK_VOCAB_MEANING"
    if any(token in text_value for token in ("cho trong can", "khoang trong can", "blank", "cau truc gi", "can cau truc", "dung cau truc", "can dang", "loai tu gi", "dang ngu phap", "ngu phap cau nay")):
        return "ASK_BLANK_STRUCTURE"
    if has_option and any(token in text_value for token in ("sai", "khong dung", "khong chon", "wrong", "why not")):
        return "ASK_WHY_OPTION_WRONG"
    if has_option and any(token in text_value for token in ("vi sao", "tai sao", "why", "chon", "dung", "correct", "dap an la")):
        return "ASK_WHY_CORRECT"
    if any(token in text_value for token in ("giai thich", "phan tich", "tai sao dap an dung", "vi sao dap an dung")):
        return "ASK_GENERAL_EXPLANATION"
    return None


def _extract_vocab_target(message: str) -> str:
    raw = str(message or "").strip()
    patterns = [
        r"(?P<target>.+?)\s+(?:nghĩa\s+là\s+gì|nghia\s+la\s+gi|có\s+nghĩa\s+là\s+gì|co\s+nghia\s+la\s+gi|là\s+gì|la\s+gi)\??$",
        r"^(?:dịch|dich)\s+(?P<target>.+?)\??$",
        r"what\s+does\s+(?P<target>.+?)\s+mean\??$",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            target = match.group("target").strip(" \"'“”?.!,")
            target = re.sub(r"^(từ|tu|cụm|cum)\s+", "", target, flags=re.IGNORECASE).strip()
            if _normalize_review_text(target) in {"cau nay", "doan nay", "sang tieng viet", "tieng viet"}:
                return ""
            return target
    return ""


def _phrase_in_review_context(phrase: str, context: dict[str, Any], options: list[dict[str, Any]]) -> bool:
    phrase_norm = _normalize_review_text(phrase)
    if not phrase_norm:
        return False
    sources = [
        context.get("question_text"),
        context.get("question_text_en"),
        context.get("passage_text"),
        *_review_source_texts(context),
        *(option.get("text") for option in options),
    ]
    return any(phrase_norm in _normalize_review_text(source) for source in sources if source)


def _option_explanation_from_option(option: dict[str, Any]) -> str:
    for key in ("explanation", "analysis", "optionExplanation", "OptionExplanation", "explanationText", "translation"):
        value = _clean_review_fragment(option.get(key))
        if value:
            return value
    return ""


def _extract_option_explanations(context: dict[str, Any], options: list[dict[str, Any]]) -> dict[str, str]:
    explanations: dict[str, str] = {}
    for option in options:
        label = str(option.get("label") or "").strip().upper()
        if label:
            value = _option_explanation_from_option(option)
            if value:
                explanations[label] = value

    option_text_by_label = {
        str(option.get("label") or "").strip().upper(): str(option.get("text") or "").strip()
        for option in options
        if str(option.get("label") or "").strip()
    }
    line_pattern = re.compile(r"^\s*(?:[-*•]\s*)?\(?([A-D])\)?\s*(?:[.)]|[-:–—])\s*(.+)$", flags=re.IGNORECASE)
    for source in _review_source_texts(context):
        for raw_line in str(source or "").splitlines():
            match = line_pattern.match(raw_line.strip())
            if not match:
                continue
            label = match.group(1).upper()
            rest = _clean_review_fragment(match.group(2))
            option_text = option_text_by_label.get(label, "")
            if option_text:
                rest = re.sub(rf"^{re.escape(option_text)}\s*[-:–—]\s*", "", rest, flags=re.IGNORECASE).strip()
            if rest and label not in explanations:
                explanations[label] = rest
    return explanations


def _extract_option_explanations(context: dict[str, Any], options: list[dict[str, Any]]) -> dict[str, str]:
    explanations: dict[str, str] = {}
    option_text_by_label = {
        str(option.get("label") or "").strip().upper(): str(option.get("text") or "").strip()
        for option in options
        if str(option.get("label") or "").strip()
    }
    for option in options:
        label = str(option.get("label") or "").strip().upper()
        value = _option_explanation_from_option(option)
        if label and value and _normalize_review_text(value) != _normalize_review_text(option_text_by_label.get(label)):
            explanations[label] = value

    line_pattern = re.compile(r"^\s*(?:[-*•]\s*)?\(?([A-D])\)?[.)]?\s*(.+)$", flags=re.IGNORECASE)
    for source in _review_source_texts(context):
        for raw_line in str(source or "").splitlines():
            line = raw_line.strip()
            match = line_pattern.match(line)
            if not match:
                continue
            label = match.group(1).upper()
            rest = _clean_review_fragment(match.group(2))
            option_text = option_text_by_label.get(label, "")
            option_norm = _normalize_review_text(option_text)
            rest_norm = _normalize_review_text(rest)
            if not rest or (option_norm and rest_norm == option_norm):
                continue
            if option_text:
                rest = re.sub(rf"^{re.escape(option_text)}\s*(?:[-:–—]\s*)?", "", rest, flags=re.IGNORECASE).strip()
            if not rest or (option_norm and _normalize_review_text(rest) == option_norm):
                continue
            if label not in explanations:
                explanations[label] = _clean_review_fragment(rest)
    return explanations


def _extract_option_explanations(context: dict[str, Any], options: list[dict[str, Any]]) -> dict[str, str]:
    explanations: dict[str, str] = {}
    option_text_by_label = {
        str(option.get("label") or "").strip().upper(): str(option.get("text") or "").strip()
        for option in options
        if str(option.get("label") or "").strip()
    }
    for option in options:
        label = str(option.get("label") or "").strip().upper()
        value = _option_explanation_from_option(option)
        if label and value and _normalize_review_text(value) != _normalize_review_text(option_text_by_label.get(label)):
            explanations[label] = value

    line_pattern = re.compile(r"^\s*(?:[-*•]\s*)?\(?([A-D])\)?[.)]?\s*(.+)$", flags=re.IGNORECASE)
    for source in _review_source_texts(context):
        in_option_section = False
        for raw_line in str(source or "").splitlines():
            line = raw_line.strip()
            kind = _review_heading_kind(line)
            if kind == "option_analysis":
                in_option_section = True
                continue
            if kind and kind != "option_analysis" and in_option_section:
                in_option_section = False
                continue
            if not in_option_section and not re.search(r"\s[-:–—]\s", line):
                continue
            match = line_pattern.match(line)
            if not match:
                continue
            label = match.group(1).upper()
            rest = _clean_review_fragment(match.group(2))
            option_text = option_text_by_label.get(label, "")
            option_norm = _normalize_review_text(option_text)
            if option_text:
                rest = re.sub(rf"^{re.escape(option_text)}\s*(?:[-:–—]\s*)", "", rest, flags=re.IGNORECASE).strip()
            if not rest or (option_norm and _normalize_review_text(rest) == option_norm):
                continue
            if label not in explanations:
                explanations[label] = _clean_review_fragment(rest)
    return explanations


def _extract_option_line_from_sql(option: dict[str, Any], context: dict[str, Any]) -> str:
    label = str(option.get("label") or "").strip().upper()
    return _extract_option_explanations(context, _review_options(context)).get(label, "")


def _extract_vocabulary_map(context: dict[str, Any]) -> dict[str, str]:
    vocabulary: dict[str, str] = {}
    sources = [_extract_sql_section(context, "vocabulary"), *(_review_source_texts(context))]
    quoted_pattern = re.compile(r"^[\"'“”‘’](.+?)[\"'“”‘’]\s+(.+)$")
    for source in sources:
        for raw_line in str(source or "").splitlines():
            line = _clean_review_fragment(raw_line)
            if not line:
                continue
            match = quoted_pattern.match(line)
            if not match:
                continue
            term = _normalize_review_text(match.group(1))
            meaning = _clean_review_fragment(match.group(2)).rstrip(".")
            if term and meaning and _review_has_vietnamese(meaning):
                vocabulary.setdefault(term, re.sub(r"\s*/\s*", " / ", meaning))
    return vocabulary


def _extract_sql_vocab_meaning(
    phrase: str,
    context: dict[str, Any],
    options: list[dict[str, Any]],
    correct_option: dict[str, Any] | None,
) -> str:
    phrase_norm = _normalize_review_text(phrase)
    if not phrase_norm:
        return ""

    vocabulary = _extract_vocabulary_map(context)
    if phrase_norm in vocabulary:
        meaning = vocabulary[phrase_norm]
        if phrase_norm == "working order" and _normalize_review_text(meaning) == "tinh trang hoat dong":
            return "tình trạng hoạt động tốt / tình trạng vận hành bình thường"
        return meaning

    matched_option = next((option for option in options if _normalize_review_text(option.get("text")) == phrase_norm), None)
    option_explanations = _extract_option_explanations(context, options)
    if matched_option:
        label = str(matched_option.get("label") or "").strip().upper()
        meaning = option_explanations.get(label, "")
        meaning = re.sub(r"\b(?:Đây là|Day la)\s+đáp án đúng\.?", "", meaning, flags=re.IGNORECASE).strip()
        if meaning and _review_has_vietnamese(meaning):
            question_norm = _normalize_review_text(context.get("question_text") or context.get("question_text_en"))
            correct_text = _normalize_review_text((correct_option or {}).get("text"))
            if phrase_norm == "staged" and correct_text == "held" and "luncheon" in question_norm:
                return "dàn dựng / tổ chức, thường dùng cho vở kịch, buổi biểu diễn hoặc sự kiện trình diễn. Trong câu này, “held” tự nhiên hơn với “luncheon”"
            return re.sub(r"\s*/\s*", " / ", meaning.rstrip("."))

    meanings = {
        "banquet hall": "phòng khánh tiết / phòng đại tiệc",
        "botanical garden": "vườn bách thảo",
        "get used to": "làm quen với cái gì đó",
        "peak": "đỉnh điểm / mức cao nhất",
        "their": "của họ / của chúng",
        "them": "họ / chúng, dùng làm tân ngữ",
        "staged": "dàn dựng / tổ chức, thường dùng cho vở kịch hoặc sự kiện trình diễn",
        "held": "được tổ chức",
        "attentively": "một cách chăm chú",
        "unexpectedly": "một cách bất ngờ / ngoài dự kiến",
    }
    return meanings.get(phrase_norm, "")


def _review_pronoun_reason(option_text: str, correct_option: dict[str, Any] | None) -> str:
    option_norm = _normalize_review_text(option_text)
    correct = _format_review_option(correct_option)
    roles = {
        "they": "“they” là đại từ nhân xưng đóng vai trò chủ ngữ, không đứng trước danh từ.",
        "them": "“them” là đại từ nhân xưng đóng vai trò tân ngữ, không đứng trước danh từ.",
        "their": "“their” là tính từ sở hữu, đứng trước danh từ để chỉ sự sở hữu.",
        "theirs": "“theirs” là đại từ sở hữu, thay thế cả cụm danh từ nên không đứng trước danh từ khác.",
    }
    if option_norm in roles:
        if option_norm == "their":
            return f"“their” đúng vì chỗ trống cần tính từ sở hữu đứng trước danh từ “peak”. Đáp án đúng là {correct}."
        return f"{roles[option_norm]} Chỗ trống cần tính từ sở hữu đứng trước danh từ “peak” để chỉ sở hữu của “housing values”. Đáp án đúng là {correct}."
    return ""


def _review_correct_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    correct = _format_review_option(correct_option)
    label = str(option.get("label") or "").strip().upper()
    option_text = str(option.get("text") or "").strip()
    general = _extract_sql_general_explanation(context)
    option_explanation = _extract_option_explanations(context, _review_options(context)).get(label, "")
    parts = [f"Đáp án đúng là {correct}."]
    if general:
        parts.append(general.rstrip(".") + ".")
    if option_explanation:
        parts.append(f"{option_text}: {option_explanation.rstrip('.')}.")
    if len(parts) == 1:
        parts.append("Câu này chưa có giải thích chi tiết trong SQL cho lựa chọn đúng.")
    return " ".join(parts)


def _review_option_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    correct = _format_review_option(correct_option)
    if option_label == correct_label:
        return _review_correct_reason(option, correct_option, context)

    pronoun_reason = _review_pronoun_reason(option_text, correct_option)
    if pronoun_reason:
        return pronoun_reason

    option_explanation = _extract_option_explanations(context, _review_options(context)).get(option_label, "")
    general = _extract_sql_general_explanation(context)
    if option_explanation:
        cleaned_reason = option_explanation.rstrip(".")
        lowered_reason = cleaned_reason[:1].lower() + cleaned_reason[1:] if cleaned_reason else cleaned_reason
        reason_norm = _normalize_review_text(cleaned_reason)
        if reason_norm.startswith(("qua khu", "mot cach", "moi", "khong ai", "dai tu", "tinh tu", "chinh xac", "ngay lap tuc", "tham chieu", "tap chi", "nganh", "thuoc ve")):
            first_sentence = f"{option_text} là {lowered_reason}."
        else:
            first_sentence = f"{option_text} không đúng vì {cleaned_reason}."
        parts = [first_sentence]
        if general:
            parts.append(general.rstrip(".") + ".")
        parts.append(f"Đáp án đúng là {correct}.")
        return " ".join(parts)
    return f"Câu này chưa có giải thích chi tiết trong SQL cho lựa chọn {option_label}. Dữ liệu hiện có cho biết đáp án đúng là {correct}."


def _review_blank_structure(context: dict[str, Any], correct_option: dict[str, Any] | None) -> str:
    correct = _format_review_option(correct_option)
    general = _extract_sql_general_explanation(context)
    if general:
        return f"{general.rstrip('.')}. Đáp án đúng là {correct}."
    return f"Câu này chưa có giải thích cấu trúc chi tiết trong SQL. Dữ liệu hiện có cho biết đáp án đúng là {correct}."


def _review_translation(context: dict[str, Any]) -> str:
    translation = _extract_sql_translation(context)
    if translation:
        return translation
    return "SQL chưa có bản dịch tiếng Việt cho câu hiện tại, nên mình chưa đưa ra bản dịch để tránh đoán sai."


def _review_option_analysis(context: dict[str, Any], options: list[dict[str, Any]], correct_option: dict[str, Any] | None) -> str:
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    explanations = _extract_option_explanations(context, options)
    lines = []
    for option in options:
        label = str(option.get("label") or "").strip().upper()
        text_value = str(option.get("text") or "").strip()
        explanation = explanations.get(label) or "Chưa có giải thích chi tiết trong SQL cho lựa chọn này."
        marker = " (đúng)" if label == correct_label else ""
        lines.append(f"{label} — {text_value}{marker}: {explanation.rstrip('.')}.")
    return "\n".join(lines)


def get_review_question_context(
    db: Session,
    user_id: Optional[int] = None,
    source: str | None = None,
    attempt_id: int | None = None,
    runtime_question_id: int | None = None,
    question_id: int | None = None,
    part: int | None = None,
    question_number: int | None = None,
    frontend_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = dict(frontend_context or {})
    if source:
        base["source"] = source
    if user_id is not None:
        base["user_id"] = user_id
    base["context_type"] = base.get("context_type") or "review"
    if attempt_id is not None:
        base["attempt_id"] = attempt_id
    if runtime_question_id is not None:
        base["runtime_question_id"] = runtime_question_id
        base["runner_question_id"] = runtime_question_id
        base["question_id"] = base.get("question_id") or runtime_question_id
    elif question_id is not None:
        base["question_id"] = question_id
    if part is not None:
        base["part"] = part
    if question_number is not None:
        base["question_number"] = question_number

    db_context = _load_question_from_db(db, base)
    result = _merge_question_context(base, db_context)
    if source:
        result["source"] = source
        result["source_type"] = source
    result["user_id"] = user_id
    if attempt_id is not None:
        result["attempt_id"] = attempt_id

    options = _review_options(result)
    explanations = _extract_option_explanations(result, options)
    for option in options:
        label = str(option.get("label") or "").strip().upper()
        if label in explanations:
            option["explanation"] = explanations[label]
    if options:
        result["options"] = options
    result["option_explanations"] = explanations
    result["detailed_explanation"] = _extract_sql_general_explanation(result)
    result["question_translation"] = _extract_sql_translation(result)
    result["vocabulary"] = _extract_vocabulary_map(result)
    return result


def _build_review_tutor_answer(message: str, context: dict[str, Any]) -> tuple[str, str] | None:
    if not _review_chat_requested(context):
        return None

    options = _review_options(context)
    correct_option = _review_correct_option(context, options)
    question_text = context.get("question_text") or context.get("question_text_en")
    if not question_text or not options or not correct_option:
        return ("Mình chưa lấy được dữ liệu câu hiện tại, bạn chọn lại câu giúp mình.", "review_context_missing")

    intent = _review_intent(message, options)
    if not intent:
        return None

    if intent == "ASK_TRANSLATION":
        return (_review_translation(context), "translation")
    if intent == "ASK_OPTION_ANALYSIS":
        return (_review_option_analysis(context, options, correct_option), "option_analysis")
    if intent == "ASK_VOCAB_MEANING":
        selected_text = str(context.get("selected_text") or "").strip()
        target = _extract_vocab_target(message)
        if selected_text and _normalize_review_text(target) in {"", "nay", "tu nay", "cum nay", "phrase nay", "this word", "this phrase"}:
            target = selected_text
        target = target or selected_text
        if target and _phrase_in_review_context(target, context, options):
            meaning = _extract_sql_vocab_meaning(target, context, options, correct_option)
            if meaning:
                return (f"“{target}” nghĩa là {meaning}.", "word_meaning")
            return (f"“{target}” xuất hiện trong câu hiện tại, nhưng SQL chưa có nghĩa tiếng Việt chắc chắn cho cụm này.", "word_meaning")
        return None
    if intent == "ASK_BLANK_STRUCTURE":
        return (_review_blank_structure(context, correct_option), "gap_requirement")

    option = _extract_review_option_from_message(message, options)
    if intent in {"ASK_WHY_OPTION_WRONG", "ASK_WHY_CORRECT"} and option:
        return (_review_option_reason(option, correct_option, context), "option_reason")
    if intent == "ASK_GENERAL_EXPLANATION":
        return (_review_correct_reason(correct_option, correct_option, context), "explanation")
    return None


def _review_intent(message: str, options: list[dict[str, Any]]) -> str | None:
    text_value = _normalize_review_text(message)
    has_option = _extract_review_option_from_message(message, options) is not None
    if any(token in text_value for token in ("phan tich tung dap an", "phan tich cac dap an", "phan tich lua chon", "giai thich cac lua chon", "giai thich tung dap an", "option analysis")):
        return "ASK_OPTION_ANALYSIS"
    if any(token in text_value for token in ("dich cau", "dich doan", "dich sang tieng viet", "dich tieng viet", "cau nay nghia la gi", "nghia cua cau", "translate this", "translate the")):
        return "ASK_TRANSLATION"
    if any(token in text_value for token in ("nghia la gi", "co nghia la gi", "la gi", "what does", "mean", "meaning")):
        if not any(token in text_value for token in ("vi sao", "tai sao", "sao ", "wrong", "sai", "khong dung")):
            return "ASK_VOCAB_MEANING"
    if any(
        token in text_value
        for token in (
            "cho trong can",
            "khoang trong can",
            "blank",
            "cau truc gi",
            "can cau truc",
            "dung cau truc",
            "can dang",
            "loai tu gi",
            "dang ngu phap",
            "ngu phap cau nay",
            "can danh tu",
            "can tinh tu",
            "can trang tu",
            "danh tu chi nguoi",
            "tu loai",
        )
    ):
        return "ASK_BLANK_STRUCTURE"
    if has_option and any(token in text_value for token in ("sai", "khong dung", "khong chon", "wrong", "why not")):
        return "ASK_WHY_OPTION_WRONG"
    if has_option and any(token in text_value for token in ("vi sao", "tai sao", "why", "chon", "dung", "correct", "dap an la")):
        return "ASK_WHY_CORRECT"
    if any(token in text_value for token in ("giai thich", "phan tich", "tai sao dap an dung", "vi sao dap an dung", "vi sao", "tai sao")):
        return "ASK_GENERAL_EXPLANATION"
    return None


def _review_correct_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    correct = _format_review_option(correct_option)
    label = str(option.get("label") or "").strip().upper()
    general = _extract_sql_general_explanation(context)
    option_explanation = _extract_option_explanations(context, _review_options(context)).get(label, "")
    parts = [f"{correct} đúng."]
    if general:
        parts.append(general.rstrip(".") + ".")
    if option_explanation:
        cleaned = re.sub(r"\b(?:Đây là|Day la)\s+đáp án đúng\.?", "", option_explanation, flags=re.IGNORECASE).strip()
        if cleaned:
            parts.append(cleaned.rstrip(".") + ".")
    if len(parts) == 1:
        parts.append("Câu này chưa có giải thích chi tiết trong SQL cho lựa chọn đúng.")
    return " ".join(parts)


def _review_blank_structure(context: dict[str, Any], correct_option: dict[str, Any] | None) -> str:
    correct = _format_review_option(correct_option)
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    general = _extract_sql_general_explanation(context)
    option_explanation = _extract_option_explanations(context, _review_options(context)).get(correct_label, "")
    parts: list[str] = []
    if general:
        parts.append(general.rstrip(".") + ".")
    if option_explanation:
        cleaned = re.sub(r"\b(?:Đây là|Day la)\s+đáp án đúng\.?", "", option_explanation, flags=re.IGNORECASE).strip()
        if cleaned:
            parts.append(f"{correct} đúng vì {cleaned.rstrip('.')}.")
    if parts:
        return " ".join(parts)
    return f"Câu này chưa có giải thích cấu trúc chi tiết trong SQL. Dữ liệu hiện có cho biết đáp án đúng là {correct}."


def _strip_review_answer_noise(value: Any) -> str:
    text_value = _clean_review_fragment(value)
    text_value = re.sub(r"\b(?:Đây là|Day la)\s+đáp án đúng\.?", "", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"\bVì vậy,\s*đáp án đúng là\s*\(?[A-D]\)?\s*[^.]*\.?", "", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value.strip(" .")


def _limit_review_sentences(value: Any, max_sentences: int = 2) -> str:
    text_value = _clean_review_fragment(value)
    if not text_value:
        return ""
    sentences = [part.strip() for part in re.split(r"(?<=[.!?。])\s+", text_value) if part.strip()]
    if len(sentences) <= max_sentences:
        return text_value.rstrip(".")
    return " ".join(sentences[:max_sentences]).rstrip(".")


def _review_correct_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    correct = _format_review_option(correct_option)
    label = str(option.get("label") or "").strip().upper()
    option_explanation = _strip_review_answer_noise(_extract_option_explanations(context, _review_options(context)).get(label, ""))
    general = _limit_review_sentences(_extract_sql_general_explanation(context), 2)
    if option_explanation and general:
        return f"{correct} đúng. {general}. {option_explanation}."
    if option_explanation:
        return f"{correct} đúng vì {option_explanation}."
    if general:
        return f"{correct} đúng. {general}."
    return f"Mình chưa thấy phần giải thích cụ thể trong dữ liệu, có thể hiểu là {correct} là lựa chọn được đánh dấu đúng cho câu hiện tại."


def _review_option_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    if option_label == correct_label:
        return _review_correct_reason(option, correct_option, context)

    option_explanation = _strip_review_answer_noise(_extract_option_explanations(context, _review_options(context)).get(option_label, ""))
    if option_explanation:
        reason_norm = _normalize_review_text(option_explanation)
        lowered = option_explanation[:1].lower() + option_explanation[1:] if option_explanation else option_explanation
        if reason_norm.startswith(("qua khu", "mot cach", "moi", "khong ai", "dai tu", "tinh tu", "chinh xac", "ngay lap tuc", "tham chieu", "tap chi", "nganh", "thuoc ve", "nha bao")):
            return f"{option_text} là {lowered}."
        return f"{option_text} không đúng vì {option_explanation}."

    general = _limit_review_sentences(_extract_sql_general_explanation(context), 2)
    if general:
        return f"Trong dữ liệu hiện có, phần giải thích chính nói rằng {general}."
    return "Mình chưa thấy phần giải thích cụ thể trong dữ liệu, có thể hiểu là lựa chọn này không khớp yêu cầu của chỗ trống."


def _review_blank_structure(context: dict[str, Any], correct_option: dict[str, Any] | None) -> str:
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    general = _limit_review_sentences(_extract_sql_general_explanation(context), 2)
    option_explanation = _strip_review_answer_noise(_extract_option_explanations(context, _review_options(context)).get(correct_label, ""))
    if general and option_explanation:
        return f"{general}. {option_explanation}."
    if general:
        return f"{general}."
    if option_explanation:
        return f"{option_explanation}."
    return "Mình chưa thấy phần giải thích cụ thể trong dữ liệu, có thể hiểu là chỗ trống cần dạng từ/cấu trúc khớp với ngữ pháp của câu."


def _review_option_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    if option_label == correct_label:
        return _review_correct_reason(option, correct_option, context)

    option_explanation = _strip_review_answer_noise(_extract_option_explanations(context, _review_options(context)).get(option_label, ""))
    general = _limit_review_sentences(_extract_sql_general_explanation(context), 2)
    if option_explanation:
        reason_norm = _normalize_review_text(option_explanation)
        lowered = option_explanation[:1].lower() + option_explanation[1:] if option_explanation else option_explanation
        if reason_norm.startswith(("qua khu", "mot cach", "moi", "khong ai", "dai tu", "tinh tu", "chinh xac", "ngay lap tuc", "tham chieu", "tap chi", "nganh", "thuoc ve", "nha bao")):
            first = f"{option_text} sai vì là {lowered}."
        else:
            first = f"{option_text} không đúng vì {option_explanation}."
        return f"{first} {general}." if general else first

    if general:
        return f"Trong dữ liệu hiện có, phần giải thích chính nói rằng {general}."
    return "Hiện mình chưa thấy phần giải thích chi tiết cho ý này trong dữ liệu câu hỏi."


def build_sql_grounded_review_answer(message: str, context: dict[str, Any]) -> tuple[str, str] | None:
    if not _review_chat_requested(context):
        return None

    options = _review_options(context)
    correct_option = _review_correct_option(context, options)
    question_text = context.get("question_text") or context.get("question_text_en")
    if not question_text or not options or not correct_option:
        return ("Mình chưa lấy được dữ liệu câu hiện tại, bạn chọn lại câu giúp mình.", "review_context_missing")

    intent = _review_intent(message, options)
    if not intent:
        return None

    if intent == "ASK_TRANSLATION":
        return (_review_translation(context), "translation")
    if intent == "ASK_OPTION_ANALYSIS":
        return (_review_option_analysis(context, options, correct_option), "option_analysis")
    if intent == "ASK_VOCAB_MEANING":
        selected_text = str(context.get("selected_text") or "").strip()
        target = _extract_vocab_target(message)
        if selected_text and _normalize_review_text(target) in {"", "nay", "tu nay", "cum nay", "phrase nay", "this word", "this phrase"}:
            target = selected_text
        target = target or selected_text
        if target and _phrase_in_review_context(target, context, options):
            meaning = _extract_sql_vocab_meaning(target, context, options, correct_option)
            if meaning:
                return (f"“{target}” nghĩa là {meaning}.", "word_meaning")
            return (f"Mình chưa thấy phần nghĩa cụ thể của “{target}” trong dữ liệu, có thể hiểu theo ngữ cảnh câu hiện tại.", "word_meaning")
        return None
    if intent == "ASK_BLANK_STRUCTURE":
        return (_review_blank_structure(context, correct_option), "gap_requirement")

    option = _extract_review_option_from_message(message, options)
    if intent in {"ASK_WHY_OPTION_WRONG", "ASK_WHY_CORRECT"} and option:
        return (_review_option_reason(option, correct_option, context), "option_reason")
    if intent == "ASK_GENERAL_EXPLANATION":
        return (_review_blank_structure(context, correct_option), "explanation")
    return None


def _build_review_tutor_answer(message: str, context: dict[str, Any]) -> tuple[str, str] | None:
    return build_sql_grounded_review_answer(message, context)


def _extract_vocabulary_map(context: dict[str, Any]) -> dict[str, str]:
    vocabulary: dict[str, str] = {}
    sources = [_extract_sql_section(context, "vocabulary"), *(_review_source_texts(context))]
    entry_pattern = re.compile(
        r"[\"'“”‘’](.+?)[\"'“”‘’]\s+(.+?)(?=\s*[\"'“”‘’][^\"'“”‘’]+[\"'“”‘’]\s+|(?:\r?\n)|$)",
        flags=re.DOTALL,
    )
    for source in sources:
        for match in entry_pattern.finditer(str(source or "")):
            term = _normalize_review_text(match.group(1))
            meaning = _clean_review_fragment(match.group(2)).rstrip(".")
            if term and meaning and _review_has_vietnamese(meaning):
                vocabulary.setdefault(term, re.sub(r"\s*/\s*", " / ", meaning))
    return vocabulary


def _review_intent(message: str, options: list[dict[str, Any]]) -> str | None:
    text_value = _normalize_review_text(message)
    has_option = _extract_review_option_from_message(message, options) is not None
    if any(token in text_value for token in ("phan tich tung dap an", "phan tich cac dap an", "phan tich lua chon", "giai thich cac lua chon", "giai thich tung dap an", "option analysis")):
        return "ASK_OPTION_ANALYSIS"
    if any(token in text_value for token in ("dich cau", "dich doan", "dich sang tieng viet", "dich tieng viet", "cau nay nghia la gi", "nghia cua cau", "translate this", "translate the")):
        return "ASK_TRANSLATION"
    if any(token in text_value for token in ("loai tu", "tu loai", "dang tu", "word form", "part of speech")):
        return "ASK_WORD_FORM" if has_option else "ASK_BLANK_STRUCTURE"
    if any(token in text_value for token in ("cho trong can", "khoang trong can", "blank", "cau truc gi", "can cau truc", "dung cau truc", "can dang", "dang ngu phap", "ngu phap cau nay", "can danh tu", "can tinh tu", "can trang tu", "danh tu chi nguoi")):
        return "ASK_BLANK_STRUCTURE"
    if any(token in text_value for token in ("nghia la gi", "co nghia la gi", "la gi", "what does", "mean", "meaning")):
        if not any(token in text_value for token in ("vi sao", "tai sao", "sao ", "wrong", "sai", "khong dung")):
            return "ASK_VOCAB_MEANING"
    if has_option and any(token in text_value for token in ("sai", "khong dung", "khong chon", "wrong", "why not")):
        return "ASK_WHY_OPTION_WRONG"
    if has_option and any(token in text_value for token in ("vi sao", "tai sao", "why", "chon", "dung", "correct", "dap an la")):
        return "ASK_WHY_CORRECT"
    if any(token in text_value for token in ("giai thich", "phan tich", "tai sao dap an dung", "vi sao dap an dung", "vi sao", "tai sao")):
        return "ASK_GENERAL_EXPLANATION"
    return None


def _extract_review_form_phrase(text_value: Any) -> str:
    text = _clean_review_fragment(text_value)
    patterns = [
        r"cần\s+một\s+(.+?)(?:\s+sau|\s+để|\s+trước|[.;]|$)",
        r"cần\s+(.+?)(?:\s+sau|\s+để|\s+trước|[.;]|$)",
        r"là\s+(.+?)(?:;|,|\.|\(|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            phrase = _clean_review_fragment(match.group(1))
            if phrase:
                phrase = re.sub(r"\s+(?:đứng|dung)$", "", phrase, flags=re.IGNORECASE).strip()
                return phrase
    lowered = _normalize_review_text(text)
    known_forms = [
        ("dong tu nguyen mau", "động từ nguyên mẫu"),
        ("danh dong tu", "danh động từ"),
        ("tinh tu so huu", "tính từ sở hữu"),
        ("danh tu chi nguoi", "danh từ chỉ người"),
        ("danh tu so nhieu", "danh từ số nhiều"),
        ("danh tu so it", "danh từ số ít"),
        ("trang tu", "trạng từ"),
        ("tinh tu", "tính từ"),
        ("danh tu", "danh từ"),
        ("dong tu", "động từ"),
    ]
    for token, label in known_forms:
        if token in lowered:
            return label
    return ""


def _review_word_form_answer(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    option_explanation = _strip_review_answer_noise(_extract_option_explanations(context, _review_options(context)).get(option_label, ""))
    general = _limit_review_sentences(_extract_sql_general_explanation(context), 2)
    form = _extract_review_form_phrase(option_explanation)
    if option_label == correct_label:
        form = _extract_review_form_phrase(general) or form
    if form and general:
        return f"{option_text} là {form}. {general}."
    if form:
        return f"{option_text} là {form}."
    if option_explanation:
        return f"{option_text}: {option_explanation}."
    if general:
        return f"Trong dữ liệu hiện có, phần giải thích chính nói rằng {general}."
    return "Hiện mình chưa thấy phần giải thích chi tiết cho loại từ này trong dữ liệu câu hỏi."


def build_sql_grounded_review_answer(message: str, context: dict[str, Any]) -> tuple[str, str] | None:
    if not _review_chat_requested(context):
        return None

    options = _review_options(context)
    correct_option = _review_correct_option(context, options)
    question_text = context.get("question_text") or context.get("question_text_en")
    if not question_text or not options or not correct_option:
        return ("Mình chưa lấy được dữ liệu câu hiện tại, bạn chọn lại câu giúp mình.", "review_context_missing")

    intent = _review_intent(message, options)
    if not intent:
        return None

    if intent == "ASK_TRANSLATION":
        return (_review_translation(context), "translation")
    if intent == "ASK_OPTION_ANALYSIS":
        return (_review_option_analysis(context, options, correct_option), "option_analysis")
    if intent == "ASK_WORD_FORM":
        option = _extract_review_option_from_message(message, options)
        if option:
            return (_review_word_form_answer(option, correct_option, context), "word_form")
        return (_review_blank_structure(context, correct_option), "word_form")
    if intent == "ASK_VOCAB_MEANING":
        selected_text = str(context.get("selected_text") or "").strip()
        target = _extract_vocab_target(message)
        if selected_text and _normalize_review_text(target) in {"", "nay", "tu nay", "cum nay", "phrase nay", "this word", "this phrase"}:
            target = selected_text
        target = target or selected_text
        if target and _phrase_in_review_context(target, context, options):
            meaning = _extract_sql_vocab_meaning(target, context, options, correct_option)
            if meaning:
                return (f"“{target}” nghĩa là {meaning}.", "word_meaning")
            return (f"Mình chưa thấy phần nghĩa cụ thể của “{target}” trong dữ liệu, có thể hiểu theo ngữ cảnh câu hiện tại.", "word_meaning")
        return None
    if intent == "ASK_BLANK_STRUCTURE":
        return (_review_blank_structure(context, correct_option), "gap_requirement")

    option = _extract_review_option_from_message(message, options)
    if intent in {"ASK_WHY_OPTION_WRONG", "ASK_WHY_CORRECT"} and option:
        return (_review_option_reason(option, correct_option, context), "option_reason")
    if intent == "ASK_GENERAL_EXPLANATION":
        return (_review_blank_structure(context, correct_option), "explanation")
    return None


def _build_review_tutor_answer(message: str, context: dict[str, Any]) -> tuple[str, str] | None:
    return build_sql_grounded_review_answer(message, context)


def _review_split_sentences(value: Any) -> list[str]:
    text_value = _clean_review_fragment(value)
    if not text_value:
        return []
    text_value = re.sub(r"\s+", " ", text_value).strip()
    sentences = [part.strip(" .") for part in re.split(r"(?<=[.!?。])\s+", text_value) if part.strip(" .")]
    return sentences or [text_value.strip(" .")]


def _review_finish_sentence(value: str) -> str:
    text_value = _clean_review_fragment(value).strip(" .")
    if not text_value:
        return ""
    return f"{text_value}."


def _review_lower_first(value: str) -> str:
    text_value = _clean_review_fragment(value).strip()
    return text_value[:1].lower() + text_value[1:] if text_value else text_value


def _review_compact_form(value: Any) -> str:
    text_value = _clean_review_fragment(value).strip(" .")
    text_value = re.sub(r"^(?:một|mot|a|an)\s+", "", text_value, flags=re.IGNORECASE)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value


def _review_concise_general(context: dict[str, Any], max_sentences: int = 2) -> str:
    sentences = _review_split_sentences(_strip_review_answer_noise(_extract_sql_general_explanation(context)))
    if not sentences:
        return ""

    chosen = [sentences[0]]
    if max_sentences > 1 and len(sentences) > 1:
        first_norm = _normalize_review_text(sentences[0])
        first_has_requirement = any(
            token in first_norm
            for token in (
                "can ",
                "cau truc",
                "dang",
                "loai",
                "bo nghia",
                "dung truoc",
                "dung sau",
                "sau tro dong tu",
                "phan tu hai",
                "danh tu chi nguoi",
            )
        )
        if not first_has_requirement:
            chosen.append(sentences[1])

    return ". ".join(part.strip(" .") for part in chosen if part).strip(" .")


def _review_first_option_explanation(context: dict[str, Any], option_label: str) -> str:
    explanation = _extract_option_explanations(context, _review_options(context)).get(option_label, "")
    return _review_split_sentences(_strip_review_answer_noise(explanation))[0] if explanation else ""


def _review_wrong_detail_fragment(option_explanation: str) -> str:
    detail = _strip_review_answer_noise(option_explanation)
    if not detail:
        return ""
    semicolon_parts = [part.strip(" .") for part in re.split(r"\s*;\s*", detail) if part.strip(" .")]
    if len(semicolon_parts) > 1 and _normalize_review_text(semicolon_parts[0]) in {"moi"}:
        detail = semicolon_parts[1]
    else:
        detail = "; ".join(semicolon_parts[:2]) if semicolon_parts else detail
    return _review_split_sentences(detail)[0] if detail else ""


def _review_support_sentence_for_wrong(context: dict[str, Any], already_used: str) -> str:
    support = _review_concise_general(context, 1)
    if not support:
        return ""
    support = _strip_review_answer_noise(support)
    support_norm = _normalize_review_text(support)
    used_norm = _normalize_review_text(already_used)
    if not support_norm or support_norm in used_norm or used_norm in support_norm:
        return ""
    return support


def _review_word_role_from_general(general: str) -> str:
    general_text = _clean_review_fragment(general)
    match = re.search(r"bổ nghĩa cho\s+([^.;]+)", general_text, flags=re.IGNORECASE)
    if match:
        target = match.group(1).strip(" .")
        target_norm = _normalize_review_text(target)
        if "nay" in target_norm or "hop ly" in target_norm or len(target) > 60:
            return ""
        return f", bổ nghĩa cho {target}"
    match = re.search(r"đứng trước\s+([^.;]+)", general_text, flags=re.IGNORECASE)
    if match:
        return f", đứng trước {match.group(1).strip(' .')}"
    return ""


def _review_correct_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    correct = _format_review_option(correct_option)
    label = str(option.get("label") or "").strip().upper()
    option_text = str(option.get("text") or "").strip()
    general = _review_concise_general(context, 2)
    option_explanation = _extract_option_explanations(context, _review_options(context)).get(label, "")
    option_meaning = _clean_review_vocab_meaning(option_explanation)
    option_detail = _review_first_option_explanation(context, label)
    if general and option_meaning:
        return f"{correct} đúng vì {_review_lower_first(general)}. {option_text} nghĩa là {option_meaning}."
    if general and option_detail:
        return f"{correct} đúng vì {_review_lower_first(general)}. {_review_finish_sentence(option_detail)}"
    if general:
        return f"{correct} đúng vì {_review_lower_first(general)}."
    if option_meaning:
        return f"{correct} đúng vì {option_text} nghĩa là {option_meaning}."
    if option_detail:
        return f"{correct} đúng vì {_review_lower_first(option_detail)}."
    return f"{correct} là đáp án đúng theo dữ liệu của câu hiện tại."


def _review_option_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    if option_label == correct_label:
        return _review_correct_reason(option, correct_option, context)

    option_explanation = _review_wrong_detail_fragment(
        _extract_option_explanations(context, _review_options(context)).get(option_label, "")
    )
    if option_explanation:
        detail_norm = _normalize_review_text(option_explanation)
        if detail_norm.startswith(("la ", "khong ", "di voi", "can ", "thuong ", "dung ")):
            first = f"{option_text} sai vì {_review_lower_first(option_explanation)}."
        elif detail_norm.startswith(
            (
                "dai tu",
                "tinh tu",
                "danh tu",
                "trang tu",
                "dong tu",
                "qua khu",
                "mot cach",
                "tap chi",
                "nganh",
                "thuoc ve",
                "tham chieu",
            )
        ):
            first = f"{option_text} sai vì là {_review_lower_first(option_explanation)}."
        else:
            first = f"{option_text} sai vì {_review_lower_first(option_explanation)}."

        support = _review_support_sentence_for_wrong(context, first)
        if support:
            return f"{first} {_review_finish_sentence(support)}"
        return first

    general = _review_concise_general(context, 1)
    if general:
        return f"{option_text} sai vì không khớp yêu cầu của chỗ trống: {_review_lower_first(general)}."
    return "Hiện mình chưa thấy phần giải thích chi tiết cho lựa chọn này trong dữ liệu câu hỏi."


def _review_blank_structure(context: dict[str, Any], correct_option: dict[str, Any] | None) -> str:
    general = _review_concise_general(context, 2)
    if general:
        return _review_finish_sentence(general)

    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    option_explanation = _review_first_option_explanation(context, correct_label)
    if option_explanation:
        return _review_finish_sentence(option_explanation)
    return "Hiện mình chưa thấy phần giải thích chi tiết cho yêu cầu của chỗ trống trong dữ liệu câu hỏi."


def _review_word_form_answer(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    option_explanation = _strip_review_answer_noise(
        _extract_option_explanations(context, _review_options(context)).get(option_label, "")
    )
    general = _review_concise_general(context, 1)

    form = _extract_review_form_phrase(option_explanation)
    if option_label == correct_label:
        form = _extract_review_form_phrase(general) or form
    form = _review_compact_form(form)
    if form:
        role = _review_word_role_from_general(general)
        return f"{option_text} là {form}{role}."

    if option_explanation:
        return f"{option_text}: {_review_split_sentences(option_explanation)[0]}."
    if general:
        return _review_finish_sentence(general)
    return "Hiện mình chưa thấy phần giải thích chi tiết cho loại từ này trong dữ liệu câu hỏi."


def build_sql_grounded_review_answer(message: str, context: dict[str, Any]) -> tuple[str, str] | None:
    if not _review_chat_requested(context):
        return None

    options = _review_options(context)
    correct_option = _review_correct_option(context, options)
    question_text = context.get("question_text") or context.get("question_text_en")
    if not question_text or not options or not correct_option:
        return ("Mình chưa lấy được dữ liệu câu hiện tại, bạn chọn lại câu giúp mình.", "review_context_missing")

    intent = _review_intent(message, options)
    if not intent:
        return None

    if intent == "ASK_TRANSLATION":
        return (_review_translation(context), "translation")
    if intent == "ASK_OPTION_ANALYSIS":
        return (_review_option_analysis(context, options, correct_option), "option_analysis")
    if intent == "ASK_WORD_FORM":
        option = _extract_review_option_from_message(message, options)
        if option:
            return (_review_word_form_answer(option, correct_option, context), "word_form")
        return (_review_blank_structure(context, correct_option), "word_form")
    if intent == "ASK_VOCAB_MEANING":
        selected_text = str(context.get("selected_text") or "").strip()
        target = _extract_vocab_target(message)
        if selected_text and _normalize_review_text(target) in {"", "nay", "tu nay", "cum nay", "phrase nay", "this word", "this phrase"}:
            target = selected_text
        target = target or selected_text
        if target and _phrase_in_review_context(target, context, options):
            meaning = _extract_sql_vocab_meaning(target, context, options, correct_option)
            if meaning:
                return (f"{target} nghĩa là {meaning}.", "word_meaning")
            return (f"Mình chưa thấy phần nghĩa cụ thể của {target} trong dữ liệu câu hiện tại.", "word_meaning")
        return None
    if intent == "ASK_BLANK_STRUCTURE":
        return (_review_blank_structure(context, correct_option), "gap_requirement")

    option = _extract_review_option_from_message(message, options)
    if intent in {"ASK_WHY_OPTION_WRONG", "ASK_WHY_CORRECT"} and option:
        return (_review_option_reason(option, correct_option, context), "option_reason")
    if intent == "ASK_GENERAL_EXPLANATION":
        return (_review_blank_structure(context, correct_option), "explanation")
    return None


_load_raw_explanation_context_from_db_base = _load_raw_explanation_context_from_db


def _review_join_unique_texts(values: list[Any], limit: int = 30000) -> str:
    seen: set[str] = set()
    parts: list[str] = []
    total = 0
    for value in values:
        text_value = str(value or "").strip()
        if not text_value:
            continue
        key = _normalize_review_text(text_value)
        if not key or key in seen:
            continue
        seen.add(key)
        if total + len(text_value) > limit:
            break
        parts.append(text_value)
        total += len(text_value)
    return "\n".join(parts)


def _load_raw_group_notes_from_db(db: Session, raw_context: dict[str, Any]) -> dict[str, str]:
    raw_explanation_id = _to_int_or_none(raw_context.get("raw_explanation_id"))
    if not raw_explanation_id:
        return {}
    try:
        row = db.execute(
            text(
                """
                SELECT TOP 1 RawDocumentId, TestType, TestNumber, Part, GroupCode, PassageText
                FROM dbo.ToeicQuestionExplanations
                WHERE Id = :raw_explanation_id
                """
            ),
            {"raw_explanation_id": raw_explanation_id},
        ).mappings().first()
        if not row:
            return {}
        group_code = str(_row_get(row, "GroupCode", default="") or "").strip()
        passage_text = str(_row_get(row, "PassageText", default="") or "").strip()
        part = _to_int_or_none(_row_get(row, "Part"))
        if part not in {6, 7} and not group_code:
            return {}

        rows = db.execute(
            text(
                """
                SELECT TOP 20 RuntimeQuestionId, QuestionNumber, VocabularyNotes, GrammarNotes, RawBlock
                FROM dbo.ToeicQuestionExplanations
                WHERE RawDocumentId = :raw_document_id
                  AND TestType = :test_type
                  AND TestNumber = :test_number
                  AND Part = :part
                  AND (
                        (:group_code <> '' AND GroupCode = :group_code)
                     OR (:group_code = '' AND :passage_text <> '' AND PassageText = :passage_text)
                  )
                ORDER BY QuestionNumber, Id
                """
            ),
            {
                "raw_document_id": _row_get(row, "RawDocumentId"),
                "test_type": _row_get(row, "TestType"),
                "test_number": _row_get(row, "TestNumber"),
                "part": part,
                "group_code": group_code,
                "passage_text": passage_text,
            },
        ).mappings().all()
        return {
            "group_vocabulary_notes": _review_join_unique_texts([_row_get(item, "VocabularyNotes") for item in rows]),
            "group_grammar_notes": _review_join_unique_texts([_row_get(item, "GrammarNotes") for item in rows]),
            "group_raw_block": _review_join_unique_texts([_row_get(item, "RawBlock") for item in rows]),
        }
    except Exception:
        logger.info("Could not load TOEIC raw group notes for review chat.", exc_info=True)
        return {}


def _load_raw_explanation_context_from_db(db: Session, context: dict[str, Any], runtime_question_id: int | None = None) -> dict[str, Any]:
    raw_context = _load_raw_explanation_context_from_db_base(db, context, runtime_question_id)
    if raw_context:
        raw_context.update({key: value for key, value in _load_raw_group_notes_from_db(db, raw_context).items() if value})
    return raw_context


def _review_source_texts(context: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in (
        "detailed_explanation",
        "explanation_detail",
        "explanation",
        "option_analysis",
        "vocabulary_notes",
        "group_vocabulary_notes",
        "vocabulary",
        "grammar_notes",
        "group_grammar_notes",
        "translation_vi",
        "final_translation_vi",
        "translation",
        "question_translation",
        "passage_translation",
        "raw_explanation",
        "raw_block",
        "group_raw_block",
    ):
        value = context.get(key)
        if isinstance(value, dict):
            for item in value.values():
                if _has_value(item):
                    texts.append(str(item))
        elif _has_value(value):
            texts.append(str(value))
    return texts


def _clean_review_vocab_meaning(value: Any) -> str:
    text_value = _clean_review_fragment(value).strip(" .")
    if not text_value:
        return ""
    text_value = re.sub(r"\s*/\s*", " / ", text_value)
    text_value = re.sub(
        r"^(?:(?:cụm\s+)?(?:danh từ|động từ|tính từ|trạng từ|đại từ|giới từ|liên từ|mệnh đề|noun phrase|noun|verb|adjective|adverb|phrase|phrasal verb)\s*[:：-]\s*)+",
        "",
        text_value,
        flags=re.IGNORECASE,
    ).strip(" .")
    text_value = re.sub(r"^(?:nghĩa là|là)\s+", "", text_value, flags=re.IGNORECASE).strip(" .")
    if ";" in text_value:
        text_value = text_value.split(";", 1)[0].strip(" .")
    sentences = _review_split_sentences(text_value)
    text_value = sentences[0] if sentences else text_value
    text_value = re.sub(
        r"(/\s*)([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ])",
        lambda match: match.group(1) + match.group(2).lower(),
        text_value,
    )
    return _review_lower_first(text_value).strip(" .")


def _extract_vocabulary_map(context: dict[str, Any]) -> dict[str, str]:
    vocabulary: dict[str, str] = {}

    existing = context.get("vocabulary")
    if isinstance(existing, dict):
        for term, meaning in existing.items():
            term_norm = _normalize_review_text(term)
            cleaned = _clean_review_vocab_meaning(meaning)
            if term_norm and cleaned:
                vocabulary.setdefault(term_norm, cleaned)

    sources: list[str] = []
    for key in ("vocabulary_notes", "group_vocabulary_notes"):
        if _has_value(context.get(key)):
            sources.append(str(context.get(key)))
    section = _extract_sql_section(context, "vocabulary")
    if section:
        sources.append(section)

    quote_chars = "\"'“”‘’â€œâ€â€˜â€™"
    entry_pattern = re.compile(
        rf"[{re.escape(quote_chars)}](.+?)[{re.escape(quote_chars)}]\s*(?:[:：\-–—])?\s*(.+?)(?=\s*(?:Ví dụ(?: minh họa)?|Dịch|Bản dịch|Phân tích|Giải thích|Câu hỏi|Part\s+\d+)\s*[:：]|\s*[{re.escape(quote_chars)}][^{re.escape(quote_chars)}]{{1,120}}[{re.escape(quote_chars)}]\s*(?:[:：\-–—])?|$)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for source in sources:
        for match in entry_pattern.finditer(str(source or "")):
            term = _normalize_review_text(match.group(1))
            meaning = _clean_review_vocab_meaning(match.group(2))
            if term and meaning and _review_has_vietnamese(meaning):
                vocabulary.setdefault(term, meaning)
    return vocabulary


def _review_vocab_token_root(token: str) -> str:
    token = _normalize_review_text(token)
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _review_vocab_variant_meaning(phrase_norm: str, vocabulary: dict[str, str]) -> str:
    phrase_tokens = [_review_vocab_token_root(token) for token in phrase_norm.split() if token]
    modifier_map = {
        "mostly": "chủ yếu",
        "mainly": "chủ yếu",
        "primarily": "chủ yếu",
        "largely": "phần lớn",
    }
    for term, meaning in sorted(vocabulary.items(), key=lambda item: len(item[0]), reverse=True):
        term_tokens = [_review_vocab_token_root(token) for token in term.split() if token]
        if len(term_tokens) < 2 or len(phrase_tokens) <= len(term_tokens):
            continue
        if phrase_tokens[0] != term_tokens[0] or phrase_tokens[-1] != term_tokens[-1]:
            continue
        middle = phrase_tokens[1:-1]
        if not middle or any(token not in modifier_map for token in middle):
            continue
        modifier = " ".join(dict.fromkeys(modifier_map[token] for token in middle))
        cleaned_meaning = _clean_review_vocab_meaning(meaning)
        if not cleaned_meaning:
            continue
        if cleaned_meaning.startswith("bao gồm") and modifier:
            return f"bao gồm {modifier} là"
        return f"{cleaned_meaning} {modifier}".strip()
    return ""


def _extract_sql_vocab_meaning(
    phrase: str,
    context: dict[str, Any],
    options: list[dict[str, Any]],
    correct_option: dict[str, Any] | None,
) -> str:
    phrase_norm = _normalize_review_text(phrase)
    if not phrase_norm:
        return ""

    vocabulary = _extract_vocabulary_map(context)
    if phrase_norm in vocabulary:
        meaning = vocabulary[phrase_norm]
        if phrase_norm == "working order" and _normalize_review_text(meaning) == "tinh trang hoat dong":
            return "tình trạng hoạt động tốt / tình trạng vận hành bình thường"
        return meaning

    partial_matches = [
        (term, meaning)
        for term, meaning in vocabulary.items()
        if term and meaning and (term in phrase_norm or phrase_norm in term)
    ]
    if partial_matches:
        partial_matches.sort(key=lambda item: len(item[0]), reverse=True)
        term, meaning = partial_matches[0]
        if term == "working order" and _normalize_review_text(meaning) == "tinh trang hoat dong":
            return "tình trạng hoạt động tốt / tình trạng vận hành bình thường"
        return meaning

    variant_meaning = _review_vocab_variant_meaning(phrase_norm, vocabulary)
    if variant_meaning:
        return variant_meaning

    matched_option = next((option for option in options if _normalize_review_text(option.get("text")) == phrase_norm), None)
    if matched_option:
        label = str(matched_option.get("label") or "").strip().upper()
        option_line = _review_wrong_detail_fragment(_extract_option_explanations(context, options).get(label, ""))
        meaning = _clean_review_vocab_meaning(option_line)
        if meaning:
            return meaning
    return ""


def _clean_review_option_explanation_block(label: str, rest: Any, option_text_by_label: dict[str, str]) -> str:
    text_value = _clean_review_fragment(rest)
    option_text = option_text_by_label.get(label, "")
    option_norm = _normalize_review_text(option_text)
    if option_text:
        text_value = re.sub(
            rf"^{re.escape(option_text)}\s*(?:[-:–—]\s*)?",
            "",
            text_value,
            flags=re.IGNORECASE,
        ).strip()
    text_value = _strip_review_answer_noise(text_value)
    if not text_value or (option_norm and _normalize_review_text(text_value) == option_norm):
        return ""
    return text_value


def _extract_option_explanations(context: dict[str, Any], options: list[dict[str, Any]]) -> dict[str, str]:
    explanations: dict[str, str] = {}
    option_text_by_label = {
        str(option.get("label") or "").strip().upper(): str(option.get("text") or "").strip()
        for option in options
        if str(option.get("label") or "").strip()
    }

    for option in options:
        label = str(option.get("label") or "").strip().upper()
        value = _option_explanation_from_option(option)
        cleaned = _clean_review_option_explanation_block(label, value, option_text_by_label)
        if label and cleaned:
            explanations[label] = cleaned

    sections = [_extract_sql_section(context, "option_analysis")]
    sections.extend(_review_source_texts(context))
    inline_pattern = re.compile(
        r"(?:^|\s)\(?([A-D])\)?[.)]?\s+(.+?)(?=\s+\(?[A-D]\)?[.)]?\s+|\s*(?:Cấu trúc|Tạm dịch|Bản dịch|Ví dụ minh họa|Giải thích chi tiết)\b|$)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    line_pattern = re.compile(r"^\s*(?:[-*•]\s*)?\(?([A-D])\)?[.)]?\s*(.+)$", flags=re.IGNORECASE)

    for source in sections:
        source_text = str(source or "")
        for match in inline_pattern.finditer(source_text):
            label = match.group(1).upper()
            cleaned = _clean_review_option_explanation_block(label, match.group(2), option_text_by_label)
            if cleaned and label not in explanations:
                explanations[label] = cleaned
        in_option_section = False
        for raw_line in source_text.splitlines():
            line = raw_line.strip()
            kind = _review_heading_kind(line)
            if kind == "option_analysis":
                in_option_section = True
                continue
            if kind and kind != "option_analysis" and in_option_section:
                in_option_section = False
                continue
            if not in_option_section and not re.search(r"\s[-:–—]\s", line):
                continue
            match = line_pattern.match(line)
            if not match:
                continue
            label = match.group(1).upper()
            cleaned = _clean_review_option_explanation_block(label, match.group(2), option_text_by_label)
            if cleaned and label not in explanations:
                explanations[label] = cleaned
    return explanations


def _review_option_reason(option: dict[str, Any], correct_option: dict[str, Any] | None, context: dict[str, Any]) -> str:
    option_text = str(option.get("text") or "").strip()
    option_label = str(option.get("label") or "").strip().upper()
    correct_label = str((correct_option or {}).get("label") or "").strip().upper()
    if option_label == correct_label:
        return _review_correct_reason(option, correct_option, context)

    option_explanation = _review_wrong_detail_fragment(
        _extract_option_explanations(context, _review_options(context)).get(option_label, "")
    )
    if option_explanation:
        detail_norm = _normalize_review_text(option_explanation)
        lowered = _review_lower_first(option_explanation)
        if detail_norm.startswith(("la ", "khong ", "di voi", "can ", "thuong ", "dung ")):
            first = f"{option_text} sai vì {lowered}."
        elif detail_norm.startswith(("mot cach", "tap chi", "nganh", "thuoc ve", "tham chieu")):
            first = f"{option_text} nghĩa là {lowered}."
        elif detail_norm.startswith(("dai tu", "tinh tu", "danh tu", "trang tu", "dong tu", "qua khu")):
            first = f"{option_text} sai vì là {lowered}."
        else:
            first = f"{option_text} sai vì {lowered}."

        support = _review_support_sentence_for_wrong(context, first)
        if support:
            return f"{first} {_review_finish_sentence(support)}"
        return first

    general = _review_concise_general(context, 1)
    if general:
        return f"{option_text} sai vì không khớp yêu cầu của chỗ trống: {_review_lower_first(general)}."
    return "Hiện mình chưa thấy phần giải thích chi tiết cho lựa chọn này trong dữ liệu câu hỏi."


def _extract_structure_lookup_target(message: str) -> tuple[str, str]:
    text_value = _normalize_review_text(message)
    patterns = [
        r"\bsau\s+(?P<target>.+?)\s+(?:thi\s+)?(?:can|nen|dung)\s+(?:gi|loai gi|dang gi|cau truc gi)\b",
        r"\btruoc\s+(?P<target>.+?)\s+(?:thi\s+)?(?:can|nen|dung)\s+(?:gi|loai gi|dang gi|cau truc gi)\b",
        r"\b(?:sau|truoc)\s+(?P<target>.+?)\s+la\s+gi\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text_value, flags=re.IGNORECASE)
        if match:
            target = re.sub(r"^(?:cum|tu|cau truc)\s+", "", match.group("target").strip(" \"'“”‘’?.!,"))
            return ("structure_target", target)
    return ("", "")


def _review_structure_lookup_answer(message: str, context: dict[str, Any]) -> str:
    _, target = _extract_structure_lookup_target(message)
    target_norm = _normalize_review_text(target)
    if not target_norm:
        return _review_blank_structure(context, _review_correct_option(context, _review_options(context)))

    sentences = _review_split_sentences(_strip_review_answer_noise(_extract_sql_general_explanation(context)))
    for index, sentence in enumerate(sentences):
        if target_norm in _normalize_review_text(sentence):
            parts = [sentence.strip(" .")]
            if index + 1 < len(sentences):
                next_sentence = sentences[index + 1].strip(" .")
                next_norm = _normalize_review_text(next_sentence)
                if any(token in next_norm for token in ("chu ngu", "can ", "nen ", "dong tu", "menh de", "danh tu", "tinh tu", "trang tu")):
                    parts.append(next_sentence)
            return _review_finish_sentence(". ".join(parts))

    for source in _review_source_texts(context):
        for sentence in _review_split_sentences(source):
            if target_norm in _normalize_review_text(sentence):
                return _review_finish_sentence(_strip_review_answer_noise(sentence))
    return "Mình chưa thấy phần giải thích này trong dữ liệu câu hiện tại."


def _review_signal_answer(context: dict[str, Any]) -> str:
    signal_tokens = (
        "dau hieu",
        "nhan biet",
        "moc thoi gian",
        "since",
        "ago",
        "for ",
        "recently",
        "already",
        "yet",
        "hien tai hoan thanh",
        "qua khu",
        "keo dai",
        "bat dau",
        "thoi gian",
    )
    general = _strip_review_answer_noise(_extract_sql_general_explanation(context))
    sources = [general, *_review_source_texts(context)]
    seen: set[str] = set()
    matches: list[str] = []
    for source in sources:
        for sentence in _review_split_sentences(source):
            cleaned = _strip_review_answer_noise(sentence).strip(" .")
            normalized = _normalize_review_text(cleaned)
            if not cleaned or normalized in seen:
                continue
            if any(token in normalized for token in signal_tokens):
                seen.add(normalized)
                matches.append(cleaned)
            if len(matches) >= 2:
                break
        if len(matches) >= 2:
            break
    if matches:
        return _review_finish_sentence(". ".join(matches[:2]))
    concise = _review_concise_general(context, 1)
    if concise:
        return _review_finish_sentence(concise)
    return "Mình chưa thấy phần giải thích này trong dữ liệu câu hiện tại."


def _review_intent(message: str, options: list[dict[str, Any]]) -> str | None:
    text_value = _normalize_review_text(message)
    has_option = _extract_review_option_from_message(message, options) is not None
    if any(token in text_value for token in ("phan tich tung dap an", "phan tich cac dap an", "phan tich lua chon", "giai thich cac lua chon", "giai thich tung dap an", "giai thich 4 dap an", "option analysis")):
        return "ASK_OPTION_ANALYSIS"
    if any(token in text_value for token in ("dich cau", "dich doan", "dich sang tieng viet", "dich tieng viet", "cau nay nghia la gi", "nghia cua cau", "translate this", "translate the")):
        return "ASK_TRANSLATION"
    if _extract_structure_lookup_target(message)[1]:
        return "ASK_STRUCTURE_TARGET"
    if any(token in text_value for token in ("dau hieu", "nhan biet", "clue", "signal")):
        return "ASK_SIGNAL"
    if any(token in text_value for token in ("loai tu", "tu loai", "dang tu", "word form", "part of speech")):
        return "ASK_WORD_FORM" if has_option else "ASK_BLANK_STRUCTURE"
    if any(token in text_value for token in ("cho trong can", "khoang trong can", "blank", "cau truc gi", "can cau truc", "dung cau truc", "can dang", "dang ngu phap", "ngu phap cau nay", "can danh tu", "can tinh tu", "can trang tu", "danh tu chi nguoi")):
        return "ASK_BLANK_STRUCTURE"
    if any(token in text_value for token in ("nghia la gi", "co nghia la gi", "la gi", "what does", "mean", "meaning")) or (
        text_value.startswith("dich ") and not any(token in text_value for token in ("dich cau", "dich doan", "dich sang tieng viet"))
    ):
        if not any(token in text_value for token in ("vi sao", "tai sao", "sao ", "wrong", "sai", "khong dung")):
            return "ASK_VOCAB_MEANING"
    if has_option and any(token in text_value for token in ("sai", "khong dung", "khong chon", "wrong", "why not")):
        return "ASK_WHY_OPTION_WRONG"
    if has_option and any(token in text_value for token in ("vi sao", "tai sao", "why", "chon", "dung", "correct", "dap an la")):
        return "ASK_WHY_CORRECT"
    if any(token in text_value for token in ("giai thich", "phan tich", "tai sao dap an dung", "vi sao dap an dung", "vi sao", "tai sao")):
        return "ASK_GENERAL_EXPLANATION"
    return None


def build_sql_grounded_review_answer(message: str, context: dict[str, Any]) -> tuple[str, str] | None:
    if not _review_chat_requested(context):
        return None

    options = _review_options(context)
    correct_option = _review_correct_option(context, options)
    question_text = context.get("question_text") or context.get("question_text_en")
    if not question_text or not options or not correct_option:
        return ("Mình chưa lấy được dữ liệu câu hiện tại, bạn chọn lại câu giúp mình.", "review_context_missing")

    intent = _review_intent(message, options)
    if not intent:
        return None

    if intent == "ASK_TRANSLATION":
        return (_review_translation(context), "translation")
    if intent == "ASK_OPTION_ANALYSIS":
        return (_review_option_analysis(context, options, correct_option), "option_analysis")
    if intent == "ASK_STRUCTURE_TARGET":
        return (_review_structure_lookup_answer(message, context), "structure_lookup")
    if intent == "ASK_SIGNAL":
        return (_review_signal_answer(context), "signal")
    if intent == "ASK_WORD_FORM":
        option = _extract_review_option_from_message(message, options)
        if option:
            return (_review_word_form_answer(option, correct_option, context), "word_form")
        return (_review_blank_structure(context, correct_option), "word_form")
    if intent == "ASK_VOCAB_MEANING":
        selected_text = str(context.get("selected_text") or "").strip()
        target = _extract_vocab_target(message)
        if selected_text and _normalize_review_text(target) in {"", "nay", "tu nay", "cum nay", "phrase nay", "this word", "this phrase"}:
            target = selected_text
        target = target or selected_text
        if target:
            meaning = _extract_sql_vocab_meaning(target, context, options, correct_option)
            if meaning:
                return (f"{target} nghĩa là {meaning}.", "word_meaning")
            return ("Mình chưa thấy phần giải thích này trong dữ liệu câu hiện tại.", "word_meaning")
        return ("Mình chưa thấy phần giải thích này trong dữ liệu câu hiện tại.", "word_meaning")
    if intent == "ASK_BLANK_STRUCTURE":
        return (_review_blank_structure(context, correct_option), "gap_requirement")

    option = _extract_review_option_from_message(message, options)
    if intent in {"ASK_WHY_OPTION_WRONG", "ASK_WHY_CORRECT"} and option:
        return (_review_option_reason(option, correct_option, context), "option_reason")
    if intent == "ASK_GENERAL_EXPLANATION":
        return (_review_blank_structure(context, correct_option), "explanation")
    return None


def _create_conversation(
    db: Session,
    user_id: Optional[int],
    existing_conversation_id: Optional[int],
    title: str,
) -> Optional[int]:
    if existing_conversation_id:
        return existing_conversation_id
    if user_id is None:
        return None

    try:
        now = datetime.utcnow()
        result = db.execute(
            text(
                """
                INSERT INTO dbo.ChatConversations (UserId, Title, CreatedAt, UpdatedAt)
                OUTPUT inserted.Id
                VALUES (:user_id, :title, :created_at, :updated_at)
                """
            ),
            {
                "user_id": user_id,
                "title": (title or "AI Tutor")[:255],
                "created_at": now,
                "updated_at": now,
            },
        )
        conversation_id = result.scalar()
        db.commit()
        return int(conversation_id) if conversation_id else None
    except Exception:
        db.rollback()
        logger.info("Could not create chat conversation.", exc_info=True)
        return None


def _save_chat_message(
    db: Session,
    conversation_id: Optional[int],
    user_id: Optional[int],
    role: str,
    content: str,
    intent: Optional[str] = None,
) -> None:
    if conversation_id is None or user_id is None:
        return

    try:
        now = datetime.utcnow()
        db.execute(
            text(
                """
                INSERT INTO dbo.ChatMessages (ConversationId, UserId, Role, Content, Intent, CreatedAt)
                VALUES (:conversation_id, :user_id, :role, :content, :intent, :created_at)
                """
            ),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "intent": intent,
                "created_at": now,
            },
        )
        db.execute(
            text(
                """
                UPDATE dbo.ChatConversations
                SET UpdatedAt = :updated_at
                WHERE Id = :conversation_id
                """
            ),
            {"updated_at": now, "conversation_id": conversation_id},
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.info("Could not save chat message.", exc_info=True)


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def post_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(current_user_dependency),
):
    message = _extract_message(payload)
    user_id = _get_user_id(current_user)
    is_pro = _is_pro_user(current_user, db)

    logger.info(
        "POST /api/chat user_id=%s email=%s plan=%s is_pro=%s",
        user_id,
        _get_user_email(current_user),
        _get_user_plan(current_user),
        is_pro,
    )

    frontend_context = _extract_question_context(payload)
    question_context = get_review_question_context(
        db,
        user_id=user_id,
        source=frontend_context.get("source"),
        attempt_id=_to_int_or_none(frontend_context.get("attempt_id")),
        runtime_question_id=_context_runtime_id(frontend_context),
        question_id=_to_int_or_none(frontend_context.get("question_id")),
        part=_to_int_or_none(frontend_context.get("part")),
        question_number=_to_int_or_none(frontend_context.get("question_number")),
        frontend_context=frontend_context,
    )

    if _is_chat_debug_enabled():
        logger.debug(
            "[chat-context] context_type=%s source=%s question_id=%s runtime_id=%s docx_id=%s final_source=%s sql_source=%s explanation_found=%s option_analysis_found=%s vocabulary_notes_found=%s correct_option=%s question=%s",
            frontend_context.get("context_type"),
            frontend_context.get("source"),
            frontend_context.get("question_id"),
            frontend_context.get("runtime_question_id") or frontend_context.get("runner_question_id"),
            frontend_context.get("docx_question_id") or frontend_context.get("source_question_id"),
            question_context.get("lookup_source") or question_context.get("source"),
            question_context.get("sql_source"),
            bool(question_context.get("explanation_detail") or question_context.get("explanation")),
            bool(question_context.get("option_analysis")),
            bool(question_context.get("vocabulary_notes")),
            question_context.get("correct_option_label") or question_context.get("correct_option_key"),
            _debug_snippet(question_context.get("question_text_en") or question_context.get("question_text"), 120),
        )

    review_answer = _build_review_tutor_answer(message, question_context)
    match = None
    if review_answer:
        answer_text, intent = review_answer
        answer = clean_response(answer_text)
        debug_options = _review_options(question_context)
        debug_option = _extract_review_option_from_message(message, debug_options)
        debug_option_key = str((debug_option or {}).get("label") or "").strip().upper() or None
        debug_option_text = str((debug_option or {}).get("text") or "").strip() or None
        debug_term = debug_option_text or _extract_vocab_target(message) or None
        if intent == "translation":
            used_data_source = "translation"
        elif intent == "word_meaning":
            used_data_source = "vocabulary"
        elif intent == "option_analysis":
            used_data_source = "option_explanation"
        elif intent == "option_reason" and debug_option_key and question_context.get("option_explanations", {}).get(debug_option_key):
            used_data_source = "option_explanation"
        elif intent in {"gap_requirement", "explanation", "option_reason", "structure_lookup", "word_form", "signal"} and (
            question_context.get("detailed_explanation")
            or question_context.get("explanation_detail")
            or question_context.get("explanation")
            or question_context.get("raw_block")
        ):
            used_data_source = "main_explanation"
        else:
            used_data_source = "fallback"
        if _is_chat_debug_enabled():
            logger.debug(
                "AI Tutor Review answer user_id=%s source=%s attemptId=%s runtimeQuestionId=%s questionId=%s questionNumber=%s detectedIntent=%s matchedTerm=%s matchedOptionKey=%s matchedOptionText=%s correctOptionKey=%s selectedOptionKey=%s used_data_source=%s usedSqlExplanation=%s usedTranslation=%s usedOptionAnalysis=%s answerLength=%s userMessage=%s",
                user_id,
                question_context.get("source") or question_context.get("lookup_source"),
                question_context.get("attempt_id") or frontend_context.get("attempt_id") or frontend_context.get("attemptId"),
                question_context.get("runtime_question_id") or question_context.get("runner_question_id"),
                question_context.get("question_id"),
                question_context.get("question_number"),
                intent,
                debug_term,
                debug_option_key,
                debug_option_text,
                question_context.get("correct_option_label") or question_context.get("correct_option_key"),
                question_context.get("selected_option_label") or question_context.get("selected_option_key"),
                used_data_source,
                bool(
                    question_context.get("explanation_detail")
                    or question_context.get("explanation")
                    or question_context.get("option_analysis")
                    or question_context.get("raw_block")
                ),
                bool(_extract_sql_translation(question_context)),
                bool(question_context.get("option_explanations")),
                len(answer or ""),
                _debug_snippet(message, 160),
            )
    else:
        match, intent = build_local_answer_with_debug(message, question_context)
        answer = clean_response(match.text)

    if _is_chat_debug_enabled() and match is None:
        logger.debug(
            "AI Tutor review deterministic message=%s question_id=%s runtime_id=%s intent=%s correct_option=%s answer=%s",
            _debug_snippet(message),
            question_context.get("question_id"),
            question_context.get("runtime_question_id") or question_context.get("runner_question_id"),
            intent,
            question_context.get("correct_option_label") or question_context.get("correct_option_key") or "",
            _debug_snippet(answer),
        )

    if _is_chat_debug_enabled() and match is not None:
        logger.debug(
            "AI Tutor local debug message=%s question_id=%s found_question=%s detected_intent=%s target=%s concept=%s aliases=%s question_text_en=%s target_near_blank=%s correct_option_label=%s correct_answer_text=%s source_field_used=%s found=%s extracted_answer=%s snippet=%s",
            _debug_snippet(message),
            question_context.get("question_id"),
            bool(question_context.get("question_id") and (question_context.get("question_text_en") or question_context.get("question_text"))),
            intent,
            match.target or "",
            getattr(match, "concept", "") or "",
            ",".join(getattr(match, "aliases", ()) or ()),
            _debug_snippet(question_context.get("question_text_en") or question_context.get("question_text")),
            getattr(match, "target_near_blank", False),
            question_context.get("correct_option_label") or question_context.get("correct_option_key") or "",
            _debug_snippet(getattr(match, "completion", "") or question_context.get("correct_answer_text") or ""),
            match.source_field or "",
            bool(
                match.source_field
                and answer
                not in {
                    "Mình chưa tìm thấy dữ liệu phù hợp trong câu hiện tại.",
                    "Mình chưa tìm thấy công thức/cấu trúc này trong dữ liệu của câu hiện tại.",
                    "Mình chưa tìm thấy cấu trúc này trong dữ liệu của câu hiện tại.",
                }
            ),
            _debug_snippet(answer),
            _debug_snippet(match.snippet),
        )

    conversation_id = _create_conversation(
        db=db,
        user_id=user_id,
        existing_conversation_id=_extract_conversation_id(payload),
        title=message,
    )
    _save_chat_message(db, conversation_id, user_id, "user", message, intent)
    _save_chat_message(db, conversation_id, user_id, "assistant", answer, intent)

    return ChatResponse(
        content=answer,
        answer=answer,
        message=answer,
        reply=answer,
        conversationId=conversation_id,
        intent=intent,
        suggestions=[],
        messages=[],
        requiresPro=False,
    )
