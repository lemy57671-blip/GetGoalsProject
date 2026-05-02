from __future__ import annotations

import logging
import os
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
            or option.get("optionKey")
            or option.get("OptionKey")
            or option.get("key")
            or _option_label(index)
        ).strip()
        text_value = str(
            option.get("text")
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

    return {
        "question_id": question_id,
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
        "transcript": _get_attr(payload, "transcript") or extra.get("transcript") or _get_attr(q, "transcript", "Transcript"),
        "options": _format_options(options),
        "selected_answer": (
            _get_attr(payload, "selected_answer", "selectedAnswer")
            or extra.get("selected_answer")
            or extra.get("selectedAnswer")
            or _get_attr(q, "selected_answer", "selectedAnswer", "userAnswer", "user_answer")
        ),
        "selected_answer_index": _extract_index(selected_answer_index),
        "correct_answer": (
            _get_attr(payload, "correct_answer", "correctAnswer")
            or extra.get("correct_answer")
            or extra.get("correctAnswer")
            or _get_attr(q, "correct_answer", "correctAnswer", "answer", "Answer")
        ),
        "correct_answer_index": _extract_index(correct_answer_index),
        "explanation": _get_attr(payload, "explanation") or extra.get("explanation") or _get_attr(q, "explanation", "Explanation"),
        "skill": _get_attr(q, "skill", "Skill", "skill_code", "skillCode") or extra.get("skill"),
        "subskill": _get_attr(q, "subskill", "Subskill", "subskill_code", "subskillCode") or extra.get("subskill"),
        "difficulty": _get_attr(q, "difficulty", "Difficulty") or extra.get("difficulty"),
    }


def _load_docx_question_from_db(db: Session, question_id: int) -> dict[str, Any]:
    for table_prefix in ("dbo.", "QuanLyData.dbo."):
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

    for table_prefix in ("dbo.", "QuanLyData.dbo."):
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


def _load_question_from_db(db: Session, question_id: Any, expected_question_text: Any = None) -> dict[str, Any]:
    if not question_id:
        return {}
    try:
        qid = int(question_id)
    except Exception:
        return {}

    docx_context = _load_docx_question_from_db(db, qid)
    if docx_context and _text_matches_expected(docx_context.get("question_text"), expected_question_text):
        return docx_context

    runner_context = _load_runner_question_from_db(db, qid)
    if runner_context:
        return runner_context

    return docx_context


def _merge_question_context(frontend_ctx: dict[str, Any], db_ctx: dict[str, Any]) -> dict[str, Any]:
    result = dict(frontend_ctx)
    db_priority_keys = {
        "question_id",
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
    }
    for key, value in db_ctx.items():
        if key in db_priority_keys and value not in (None, "", [], {}):
            result[key] = value
        elif result.get(key) in (None, "", [], {}):
            result[key] = value
    return result


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
    db_context = _load_question_from_db(
        db,
        frontend_context.get("question_id"),
        frontend_context.get("question_text"),
    )
    question_context = _merge_question_context(frontend_context, db_context)

    match, intent = build_local_answer_with_debug(message, question_context)
    answer = clean_response(match.text)

    if _is_chat_debug_enabled():
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
