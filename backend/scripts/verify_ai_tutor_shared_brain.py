from __future__ import annotations

import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.routes.chat import get_review_question_context, post_chat  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.schemas.chat import ChatRequest  # noqa: E402


MISSING_DETAIL_FALLBACK = (
    "Hiện câu này chưa có lời giải chi tiết trong dữ liệu. "
    "Mình sẽ giải nhanh dựa trên câu hỏi và đáp án hiện có."
)


@dataclass(frozen=True)
class Case:
    name: str
    message: str
    expected_intent: str
    mode: str = "practice"
    selected_answer: str | None = None
    target_option: str | None = None
    question_kind: str = "rich"
    require_fallback: bool = False
    required_fragments: tuple[str, ...] = ()
    forbidden_fragments: tuple[str, ...] = ()


class SharedBrainLogCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.records: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        if not str(record.msg).startswith("AI Tutor shared brain"):
            return
        args = record.args if isinstance(record.args, tuple) else ()
        keys = (
            "source",
            "mode",
            "questionId",
            "selectedAnswer",
            "normalizedMessage",
            "detectedIntent",
            "targetOption",
            "targetOptionText",
            "dbContextFound",
            "hasExplanation",
            "hasExplanationDetail",
            "hasOptionAnalysis",
            "hasGrammarNotes",
            "hasTranslation",
            "answerBuilderUsed",
        )
        self.records.append(dict(zip(keys, args)))


def _has_text_sql(column: str) -> str:
    return f"NULLIF(LTRIM(RTRIM(CAST({column} AS NVARCHAR(MAX)))), '') IS NOT NULL"


def _scalar_int(db: Any, sql: str, params: dict[str, Any] | None = None) -> int | None:
    row = db.execute(text(sql), params or {}).first()
    if not row or row[0] is None:
        return None
    return int(row[0])


def find_rich_question_id(db: Any) -> int:
    sql = f"""
        SELECT TOP 1 q.Id
        FROM dbo.ToeicPracticeQuestions q
        WHERE {_has_text_sql('q.QuestionText')}
          AND (
                {_has_text_sql('q.CorrectOptionKey')}
             OR EXISTS (
                    SELECT 1
                    FROM dbo.ToeicPracticeQuestionOptions co
                    WHERE co.QuestionId = q.Id AND co.IsCorrect = 1
                )
          )
          AND (
                SELECT COUNT(*)
                FROM dbo.ToeicPracticeQuestionOptions o
                WHERE o.QuestionId = q.Id AND {_has_text_sql('o.OptionText')}
          ) >= 4
          AND (
                {_has_text_sql('q.Explanation')}
             OR EXISTS (
                    SELECT 1
                    FROM dbo.ToeicQuestionExplanations e
                    WHERE e.RuntimeQuestionId = q.Id
                      AND (
                            {_has_text_sql('e.ExplanationText')}
                         OR {_has_text_sql('e.RawBlock')}
                         OR {_has_text_sql('e.VocabularyNotes')}
                         OR {_has_text_sql('e.GrammarNotes')}
                      )
                )
          )
        ORDER BY
          CASE
            WHEN EXISTS (
                SELECT 1
                FROM dbo.ToeicQuestionExplanations e
                WHERE e.RuntimeQuestionId = q.Id
                  AND (
                        e.ExplanationText LIKE N'%Translation%'
                     OR e.RawBlock LIKE N'%Translation%'
                     OR e.RawBlock LIKE N'%Dịch%'
                     OR e.RawBlock LIKE N'%Bản dịch%'
                  )
            )
            THEN 0 ELSE 1
          END,
          q.Id
    """
    question_id = _scalar_int(db, sql)
    if not question_id:
        raise RuntimeError("Could not find a TOEIC practice question with SQL context.")
    return question_id


def find_comply_question_id(db: Any) -> int | None:
    sql = f"""
        SELECT TOP 1 q.Id
        FROM dbo.ToeicPracticeQuestions q
        LEFT JOIN dbo.ToeicQuestionExplanations e ON e.RuntimeQuestionId = q.Id
        WHERE {_has_text_sql('q.QuestionText')}
          AND (
                q.QuestionText LIKE N'%comply%'
             OR q.Explanation LIKE N'%comply%'
             OR e.ExplanationText LIKE N'%comply%'
             OR e.RawBlock LIKE N'%comply%'
             OR e.VocabularyNotes LIKE N'%comply%'
             OR EXISTS (
                    SELECT 1
                    FROM dbo.ToeicPracticeQuestionOptions o
                    WHERE o.QuestionId = q.Id AND o.OptionText LIKE N'%comply%'
                )
          )
          AND (
                SELECT COUNT(*)
                FROM dbo.ToeicPracticeQuestionOptions o
                WHERE o.QuestionId = q.Id AND {_has_text_sql('o.OptionText')}
          ) >= 4
        ORDER BY q.Id
    """
    return _scalar_int(db, sql)


def find_future_perfect_question_id(db: Any) -> int | None:
    sql = f"""
        SELECT TOP 1 q.Id
        FROM dbo.ToeicPracticeQuestions q
        WHERE {_has_text_sql('q.QuestionText')}
          AND q.QuestionText LIKE N'%by the time%'
          AND EXISTS (
                SELECT 1
                FROM dbo.ToeicPracticeQuestionOptions o
                WHERE o.QuestionId = q.Id
                  AND o.OptionText LIKE N'%will have demolished%'
          )
          AND (
                SELECT COUNT(*)
                FROM dbo.ToeicPracticeQuestionOptions o
                WHERE o.QuestionId = q.Id AND {_has_text_sql('o.OptionText')}
          ) >= 4
        ORDER BY q.Id
    """
    return _scalar_int(db, sql)


def find_missing_explanation_question_id(db: Any) -> int | None:
    sql = f"""
        SELECT TOP 1 q.Id
        FROM dbo.ToeicPracticeQuestions q
        WHERE {_has_text_sql('q.QuestionText')}
          AND (
                {_has_text_sql('q.CorrectOptionKey')}
             OR EXISTS (
                    SELECT 1
                    FROM dbo.ToeicPracticeQuestionOptions co
                    WHERE co.QuestionId = q.Id AND co.IsCorrect = 1
                )
          )
          AND (
                SELECT COUNT(*)
                FROM dbo.ToeicPracticeQuestionOptions o
                WHERE o.QuestionId = q.Id AND {_has_text_sql('o.OptionText')}
          ) >= 4
          AND NOT {_has_text_sql('q.Explanation')}
          AND NOT EXISTS (
                SELECT 1
                FROM dbo.ToeicQuestionExplanations e
                WHERE e.RuntimeQuestionId = q.Id
                  AND (
                        {_has_text_sql('e.ExplanationText')}
                     OR {_has_text_sql('e.RawBlock')}
                     OR {_has_text_sql('e.VocabularyNotes')}
                     OR {_has_text_sql('e.GrammarNotes')}
                  )
          )
        ORDER BY q.Id
    """
    return _scalar_int(db, sql)


def _response_text(response: Any) -> str:
    for key in ("answer", "message", "content", "reply"):
        value = getattr(response, key, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _first_capture(capture: SharedBrainLogCapture) -> dict[str, Any]:
    if not capture.records:
        raise AssertionError("No shared-brain log record was emitted.")
    return capture.records[-1]


async def call_shared_brain(db: Any, payload: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    capture = SharedBrainLogCapture()
    logger = logging.getLogger("app.api.routes.chat")
    previous_level = logger.level
    logger.addHandler(capture)
    logger.setLevel(logging.INFO)
    try:
        response = await post_chat(ChatRequest(**payload), db=db, current_user=None)
    finally:
        logger.removeHandler(capture)
        logger.setLevel(previous_level)

    answer = _response_text(response)
    intent = str(getattr(response, "intent", "") or "")
    return answer, intent, _first_capture(capture)


def normalize_answer(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def assert_payloads_equivalent(web_payload: dict[str, Any], mobile_payload: dict[str, Any]) -> None:
    web_without_source = {key: value for key, value in web_payload.items() if key != "source"}
    mobile_without_source = {key: value for key, value in mobile_payload.items() if key != "source"}
    if web_without_source != mobile_without_source:
        raise AssertionError(f"Payloads differ beyond source: {web_without_source} != {mobile_without_source}")
    if web_payload.get("source") != "web" or mobile_payload.get("source") != "mobile":
        raise AssertionError("Payload sources are not web/mobile.")
    expected_keys = {"message", "questionId", "selectedAnswer", "mode", "source"}
    if set(web_payload) != expected_keys or set(mobile_payload) != expected_keys:
        raise AssertionError(f"Unexpected payload keys: web={set(web_payload)} mobile={set(mobile_payload)}")


def correct_answer_from_context(db: Any, question_id: int) -> tuple[str, str]:
    context = get_review_question_context(
        db,
        source="web",
        runtime_question_id=question_id,
        question_id=question_id,
        frontend_context={"message": "debug", "questionId": question_id, "mode": "practice", "source": "web"},
    )
    label = str(context.get("correct_option_label") or context.get("correct_option_key") or "").strip().upper()
    text_value = str(context.get("correct_answer_text") or "").strip()
    return label, text_value


def validate_answer_shape(case: Case, answer: str, rich_correct: tuple[str, str]) -> None:
    normalized = normalize_answer(answer)
    if not normalized:
        raise AssertionError("Answer is empty.")
    if "No explanation is available" in answer:
        raise AssertionError("Answer contains old weak fallback.")
    if case.require_fallback and MISSING_DETAIL_FALLBACK not in answer:
        raise AssertionError("Missing-explanation fallback text was not returned.")
    if not case.require_fallback and MISSING_DETAIL_FALLBACK in answer and case.question_kind != "missing":
        raise AssertionError("Unexpected missing-explanation fallback for rich SQL question.")
    for fragment in case.required_fragments:
        if fragment not in answer:
            raise AssertionError(f"Answer missing required fragment: {fragment}")
    for fragment in case.forbidden_fragments:
        if fragment in answer:
            raise AssertionError(f"Answer contains forbidden fragment: {fragment}")

    if case.expected_intent == "correct_answer":
        if "Đáp án đúng" not in answer or "Lý do" not in answer:
            raise AssertionError("Correct-answer response does not include answer plus short reason.")
    elif case.expected_intent == "how_to_solve":
        if "Yêu cầu" not in answer and "Cần nhìn" not in answer:
            raise AssertionError("How-to-solve response does not mention approach/clue/requirement.")
        option_headers = sum(1 for label in ("A", "B", "C", "D") if re.search(rf"(^|\n){label}\s*[—.-]", answer))
        if option_headers >= 4:
            raise AssertionError("How-to-solve response looks like full option analysis.")
    elif case.expected_intent == "why_correct":
        if "đúng vì" not in answer.lower() and "Đáp án đúng" not in answer:
            raise AssertionError("Why-correct response does not explain the correct option.")
    elif case.expected_intent == "full_option_analysis":
        for label in ("A", "B", "C", "D"):
            if not re.search(rf"(^|\n){label}\s*[—.-]", answer):
                raise AssertionError("Full option analysis does not include A/B/C/D.")
    elif case.expected_intent == "option_reason":
        if case.target_option and not re.search(rf"(^|\n|\"| ){case.target_option}\s*[—.-]", answer):
            raise AssertionError("Option-reason response does not mention the requested option.")
        option_headers = sum(1 for label in ("A", "B", "C", "D") if re.search(rf"(^|\n){label}\s*[—.-]", answer))
        if option_headers >= 4:
            raise AssertionError("Option-reason response analyzes all options.")
    elif case.expected_intent == "selected_wrong_reason":
        if "Bạn chọn" not in answer or "Đáp án đúng" not in answer:
            raise AssertionError("Selected-answer response does not compare selected and correct answers.")
    elif case.expected_intent == "hint":
        correct_label, correct_text = rich_correct
        if "Đáp án đúng" in answer:
            raise AssertionError("Hint reveals the answer marker.")
        if correct_text and correct_text.lower() in answer.lower():
            raise AssertionError("Hint reveals the correct answer text.")
        if correct_label and re.search(rf"\b{re.escape(correct_label)}\b", answer):
            raise AssertionError("Hint reveals the correct answer label.")
    elif case.expected_intent == "vocabulary_meaning":
        if "comply with" not in answer.lower():
            raise AssertionError("Word meaning response did not focus on 'comply with'.")
    elif case.expected_intent == "tense_requirement":
        required_fragments = (
            "tương lai hoàn thành",
            "will have + V3",
            "by the time + S + V hiện tại đơn",
            "B. will have demolished",
        )
        for fragment in required_fragments:
            if fragment not in answer:
                raise AssertionError(f"Tense response missing required fragment: {fragment}")


async def run_case(
    db: Any,
    case: Case,
    question_id: int,
    rich_correct: tuple[str, str],
) -> dict[str, Any]:
    base_payload = {
        "message": case.message,
        "questionId": question_id,
        "selectedAnswer": case.selected_answer,
        "mode": case.mode,
    }
    web_payload = {**base_payload, "source": "web"}
    mobile_payload = {**base_payload, "source": "mobile"}
    assert_payloads_equivalent(web_payload, mobile_payload)

    web_answer, web_intent, web_log = await call_shared_brain(db, web_payload)
    mobile_answer, mobile_intent, mobile_log = await call_shared_brain(db, mobile_payload)

    if normalize_answer(web_answer) != normalize_answer(mobile_answer):
        raise AssertionError("Web and Mobile answers differ.")
    if web_intent != mobile_intent:
        raise AssertionError(f"Web and Mobile response intents differ: {web_intent} != {mobile_intent}")
    if web_log.get("detectedIntent") != mobile_log.get("detectedIntent"):
        raise AssertionError("Backend logs report different detected intents.")
    if web_log.get("normalizedMessage") != mobile_log.get("normalizedMessage"):
        raise AssertionError("Backend logs report different normalized messages.")
    if web_log.get("targetOption") != mobile_log.get("targetOption"):
        raise AssertionError("Backend logs report different target options.")
    if web_log.get("targetOptionText") != mobile_log.get("targetOptionText"):
        raise AssertionError("Backend logs report different target option text.")
    if web_intent != case.expected_intent:
        raise AssertionError(f"Expected intent {case.expected_intent}, got {web_intent}.")
    if case.target_option and web_log.get("targetOption") != case.target_option:
        raise AssertionError(f"Expected target option {case.target_option}, got {web_log.get('targetOption')}.")
    validate_answer_shape(case, web_answer, rich_correct)

    return {
        "name": case.name,
        "questionId": question_id,
        "intent": web_intent,
        "normalizedMessage": web_log.get("normalizedMessage"),
        "targetOption": web_log.get("targetOption"),
        "targetOptionText": web_log.get("targetOptionText"),
        "dbContextFound": web_log.get("dbContextFound"),
        "hasExplanation": web_log.get("hasExplanation"),
        "hasExplanationDetail": web_log.get("hasExplanationDetail"),
        "hasOptionAnalysis": web_log.get("hasOptionAnalysis"),
        "hasGrammarNotes": web_log.get("hasGrammarNotes"),
        "hasTranslation": web_log.get("hasTranslation"),
        "answerBuilderUsed": web_log.get("answerBuilderUsed"),
        "answerPreview": normalize_answer(web_answer)[:180],
    }


async def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    cases = [
        Case("Correct answer intent", "đáp án là gì", "correct_answer"),
        Case("No-accent correct answer", "dap an la gi", "correct_answer"),
        Case("How to solve", "câu này làm sao", "how_to_solve"),
        Case("Typo/no-accent how to solve", "cau nay lam s", "how_to_solve"),
        Case("Why correct", "vì sao nó đúng", "why_correct"),
        Case("No-accent why correct", "vi s no dung", "why_correct"),
        Case("Option reason", "vì sao B sai", "option_reason", target_option="B"),
        Case("No-accent option reason", "sao b sai", "option_reason", target_option="B"),
        Case("Selected answer check", "tui chọn A sao sai", "selected_wrong_reason", selected_answer="A", target_option="A"),
        Case("Full option analysis", "phân tích từng đáp án", "full_option_analysis"),
        Case("Translation", "dịch câu này", "translation"),
        Case("Word meaning", "comply with là gì", "vocabulary_meaning", question_kind="comply"),
        Case("Grammar", "tại sao dùng V-ing", "grammar_explanation"),
        Case("Gap requirement", "chỗ trống cần loại từ gì", "word_form_requirement"),
        Case("Tense requirement", "chỗ trống cần thì gì", "tense_requirement", question_kind="future_perfect"),
        Case("No-accent tense requirement", "cho trong can thi gi", "tense_requirement", question_kind="future_perfect"),
        Case(
            "Future option A reason",
            "tại sao A sai",
            "option_reason",
            target_option="A",
            question_kind="future_perfect",
            required_fragments=(
                "A. demolish sai",
                "hiện tại đơn",
                "by the time the waste removal trucks arrive at 3:30",
                "will have + V3",
                "B. will have demolished",
            ),
        ),
        Case(
            "Future option text reason",
            "demolish sai ở đâu",
            "option_reason",
            target_option="A",
            question_kind="future_perfect",
            required_fragments=(
                "\"demolish\" là option A",
                "hiện tại đơn",
                "will have + V3",
                "B. will have demolished",
            ),
        ),
        Case(
            "Future hint no answer",
            "hint thôi đừng nói đáp án",
            "hint",
            question_kind="future_perfect",
            required_fragments=("by the time the waste removal trucks arrive at 3:30",),
            forbidden_fragments=("Đáp án đúng", "will have demolished"),
        ),
        Case("Signal", "keyword ở đâu", "signal"),
        Case("Hint", "gợi ý thôi đừng nói đáp án", "hint"),
        Case("Trap", "câu này có bẫy gì", "trap_explanation"),
        Case(
            "Missing explanation fallback",
            "câu này làm sao",
            "how_to_solve",
            question_kind="missing",
            require_fallback=True,
        ),
    ]

    db = SessionLocal()
    failures: list[tuple[str, str]] = []
    results: list[dict[str, Any]] = []
    try:
        rich_qid = find_rich_question_id(db)
        comply_qid = find_comply_question_id(db)
        future_perfect_qid = find_future_perfect_question_id(db)
        missing_qid = find_missing_explanation_question_id(db)
        rich_correct = correct_answer_from_context(db, rich_qid)

        print(f"richQuestionId={rich_qid}")
        print(f"complyQuestionId={comply_qid or 'NOT_FOUND'}")
        print(f"futurePerfectQuestionId={future_perfect_qid or 'NOT_FOUND'}")
        print(f"missingExplanationQuestionId={missing_qid or 'NOT_FOUND'}")

        for case in cases:
            if case.question_kind == "comply":
                if not comply_qid:
                    failures.append((case.name, "No SQL question containing 'comply' was found."))
                    continue
                question_id = comply_qid
            elif case.question_kind == "future_perfect":
                if not future_perfect_qid:
                    failures.append((case.name, "No SQL future-perfect 'will have demolished' question was found."))
                    continue
                question_id = future_perfect_qid
            elif case.question_kind == "missing":
                if not missing_qid:
                    failures.append((case.name, "No SQL question without explanation was found."))
                    continue
                question_id = missing_qid
            else:
                question_id = rich_qid

            try:
                case_correct = correct_answer_from_context(db, question_id)
                results.append(await run_case(db, case, question_id, case_correct))
                print(f"PASS | {case.name}")
            except Exception as exc:  # noqa: BLE001
                failures.append((case.name, str(exc)))
                print(f"FAIL | {case.name} | {exc}")

        print("\nBackend shared-brain log fields observed:")
        for item in results:
            print(
                " - {name}: q={questionId} intent={intent} target={targetOption} "
                "normalized={normalizedMessage} db={dbContextFound} exp={hasExplanation} "
                "detail={hasExplanationDetail} options={hasOptionAnalysis} "
                "grammar={hasGrammarNotes} translation={hasTranslation}".format(**item)
            )

        if failures:
            print("\nFailures:")
            for name, reason in failures:
                print(f" - {name}: {reason}")
            return 1

        print("\nAll shared AI Tutor Web/Mobile checks passed.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
