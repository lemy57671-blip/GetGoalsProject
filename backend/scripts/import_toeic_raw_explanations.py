from __future__ import annotations

import json
import logging
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from sqlalchemy import text
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal, engine


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MANIFESTS_DIR = BACKEND_ROOT / "runtime" / "static" / "toeic" / "manifests"
MIGRATION_PATH = BACKEND_ROOT / "app" / "db" / "migrations" / "20260506_toeic_raw_explanations.sql"

IMPORT_TARGETS = [
    {
        "test_type": "fulltest",
        "test_number": 1,
        "title": "TOEIC Full Test 1 Raw Explanations",
        "manifest": "fulltest_test1_questions.json",
        "source_candidates": [
            BACKEND_ROOT / "runtime" / "static" / "toeic" / "raw" / "fulltest.docx",
            BACKEND_ROOT / "runtime" / "source_materials" / "fulltest.docx",
            PROJECT_ROOT / "fulltest.docx",
            Path("D:/Downloads/fulltest.docx"),
            Path("D:/Downloads/1/fulltest.docx"),
        ],
    },
    {
        "test_type": "minitest",
        "test_number": 1,
        "title": "TOEIC Mini Test 1 Raw Explanations",
        "manifest": "minitest_test1_questions.json",
        "source_candidates": [
            BACKEND_ROOT / "runtime" / "static" / "toeic" / "raw" / "Mini Test.docx",
            BACKEND_ROOT / "runtime" / "source_materials" / "Mini Test.docx",
            PROJECT_ROOT / "Mini Test.docx",
            Path("D:/Downloads/Mini Test.docx"),
            Path("D:/Downloads/1/Mini Test.docx"),
        ],
    },
]

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _ensure_raw_tables() -> None:
    if not MIGRATION_PATH.exists():
        raise FileNotFoundError(f"Raw explanation migration not found: {MIGRATION_PATH}")

    sql_text = MIGRATION_PATH.read_text(encoding="utf-8")
    statements = [part.strip() for part in re.split(r"(?im)^\s*GO\s*$", sql_text) if part.strip()]
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)


def _read_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(document_xml)
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{WORD_NAMESPACE}p"):
        parts: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{WORD_NAMESPACE}t":
                parts.append(node.text or "")
            elif node.tag == f"{WORD_NAMESPACE}tab":
                parts.append("\t")
            elif node.tag in {f"{WORD_NAMESPACE}br", f"{WORD_NAMESPACE}cr"}:
                parts.append("\n")
        text_value = "".join(parts).strip()
        if text_value:
            paragraphs.append(text_value)
    return "\n".join(paragraphs)


def _resolve_source_path(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    joined = ", ".join(str(item) for item in candidates)
    raise FileNotFoundError(f"Could not find DOCX source. Checked: {joined}")


def _load_manifest(name: str) -> list[dict[str, Any]]:
    path = MANIFESTS_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list.")
    return [item for item in data if isinstance(item, dict)]


def _get_passage_text(item: dict[str, Any]) -> str | None:
    passage = item.get("passage")
    if isinstance(passage, dict):
        return str(passage.get("text") or passage.get("passageText") or "").strip() or None
    if isinstance(passage, str) and passage.strip():
        return passage.strip()
    return None


def _resolve_correct_key(item: dict[str, Any]) -> str | None:
    correct_answer = str(item.get("correctAnswer") or "").strip().upper()
    if re.fullmatch(r"[A-Z]", correct_answer):
        return correct_answer
    index = item.get("correctAnswerIndex")
    if isinstance(index, int) and 0 <= index < 26:
        return chr(ord("A") + index)
    return correct_answer[:10] or None


def _option_by_key(options: list[Any], key: str | None) -> str | None:
    if not key:
        return None
    index = ord(key[0].upper()) - ord("A") if "A" <= key[0].upper() <= "Z" else -1
    if 0 <= index < len(options):
        return str(options[index] or "")
    return None


def _build_numbered_blocks(raw_text: str) -> dict[int, str]:
    blocks: dict[int, list[str]] = {}
    current_number: int | None = None
    marker_pattern = re.compile(
        r"^(?:(?:Question)|(?:C(?:au|\u00e2u)\s+h(?:oi|\u1ecfi)))?\s*(\d{1,3})[\).:\s-]+",
        flags=re.IGNORECASE,
    )
    for line in raw_text.splitlines():
        clean = line.strip()
        matched = marker_pattern.match(clean)
        if matched:
            value = int(matched.group(1))
            if 1 <= value <= 200:
                current_number = value
                blocks.setdefault(value, [])
        if current_number is not None:
            blocks.setdefault(current_number, []).append(line)
    return {key: "\n".join(value).strip() for key, value in blocks.items() if value}


def _snippet_for_question_text(raw_text: str, question_text: str | None, limit: int = 2400) -> str:
    text_value = re.sub(r"\s+", " ", question_text or "").strip()
    if len(text_value) < 12:
        return ""
    fragment = text_value[: min(len(text_value), 80)]
    index = raw_text.lower().find(fragment.lower())
    if index < 0:
        words = text_value.split()
        fragment = " ".join(words[:8])
        index = raw_text.lower().find(fragment.lower())
    if index < 0:
        return ""
    start = max(0, index - 500)
    end = min(len(raw_text), index + limit)
    return raw_text[start:end].strip()


def _raw_block_for_item(raw_text: str, numbered_blocks: dict[int, str], item: dict[str, Any]) -> str:
    question_number = int(item.get("questionNumber") or 0)
    if question_number in numbered_blocks:
        return numbered_blocks[question_number]
    snippet = _snippet_for_question_text(raw_text, str(item.get("question") or ""))
    if snippet:
        return snippet
    options = [str(value or "") for value in (item.get("options") or [])]
    option_lines = [f"{chr(ord('A') + index)}. {text}" for index, text in enumerate(options) if text]
    return "\n".join(
        [
            "Manifest fallback block; exact DOCX question block was not isolated.",
            f"Part: {item.get('part') or ''}",
            f"QuestionNumber: {item.get('questionNumber') or ''}",
            f"Question: {item.get('question') or ''}",
            *option_lines,
            f"CorrectOptionKey: {_resolve_correct_key(item) or ''}",
        ]
    ).strip()


def _extract_labeled_text(raw_block: str, labels: list[str]) -> str | None:
    if not raw_block:
        return None
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"(?:{label_pattern})\s*[:.-]\s*(?P<body>.*?)(?=\n\s*(?:Explanation|Giai thich|Vocabulary|Grammar|Tu vung|Ngu phap|Answer|Dap an)\s*[:.-]|\Z)",
        raw_block,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    body = re.sub(r"\s+", " ", match.group("body")).strip()
    return body or None


def _load_runtime_lookup(db: Session, test_type: str, test_number: int) -> dict[tuple[int, int], dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT q.Id AS RuntimeQuestionId,
                   q.Part,
                   q.QuestionNumber,
                   q.QuestionText,
                   p.GroupCode,
                   p.PassageText
            FROM dbo.ToeicPracticeQuestions q
            INNER JOIN dbo.ToeicPracticeSets s ON s.Id = q.SetId
            LEFT JOIN dbo.ToeicPracticePassages p ON p.Id = q.PassageId
            WHERE s.Type = :test_type
              AND s.TestNumber = :test_number
            """
        ),
        {"test_type": test_type, "test_number": test_number},
    ).mappings().all()
    lookup: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        part = int(row.get("Part") or 0)
        question_number = int(row.get("QuestionNumber") or 0)
        if part > 0 and question_number > 0:
            lookup[(part, question_number)] = dict(row)
    return lookup


def _replace_raw_document(
    db: Session,
    source_path: Path,
    test_type: str,
    test_number: int,
    title: str,
    raw_text: str,
) -> int:
    existing_rows = db.execute(
        text(
            """
            SELECT Id
            FROM dbo.ToeicRawDocuments
            WHERE SourceFile = :source_file
              AND TestType = :test_type
              AND TestNumber = :test_number
            """
        ),
        {"source_file": source_path.name, "test_type": test_type, "test_number": test_number},
    ).mappings().all()
    for row in existing_rows:
        document_id = int(row.get("Id"))
        db.execute(text("DELETE FROM dbo.ToeicQuestionExplanations WHERE RawDocumentId = :document_id"), {"document_id": document_id})
        db.execute(text("DELETE FROM dbo.ToeicRawDocuments WHERE Id = :document_id"), {"document_id": document_id})

    row = db.execute(
        text(
            """
            INSERT INTO dbo.ToeicRawDocuments (SourceFile, TestType, TestNumber, Title, RawText)
            OUTPUT INSERTED.Id
            VALUES (:source_file, :test_type, :test_number, :title, :raw_text)
            """
        ),
        {
            "source_file": source_path.name,
            "test_type": test_type,
            "test_number": test_number,
            "title": title,
            "raw_text": raw_text,
        },
    ).first()
    if not row:
        raise RuntimeError("Could not insert ToeicRawDocuments row.")
    return int(row[0])


def _insert_explanation_row(
    db: Session,
    raw_document_id: int,
    target: dict[str, Any],
    item: dict[str, Any],
    runtime_row: dict[str, Any] | None,
    raw_block: str,
) -> None:
    options = [str(value or "") for value in (item.get("options") or [])]
    correct_key = _resolve_correct_key(item)
    explanation_text = str(item.get("explanation") or "").strip() or _extract_labeled_text(raw_block, ["Explanation", "Giai thich"])
    vocabulary_notes = _extract_labeled_text(raw_block, ["Vocabulary", "Tu vung"])
    grammar_notes = _extract_labeled_text(raw_block, ["Grammar", "Ngu phap"])

    db.execute(
        text(
            """
            INSERT INTO dbo.ToeicQuestionExplanations
            (
                RawDocumentId,
                RuntimeQuestionId,
                TestType,
                TestNumber,
                Part,
                QuestionNumber,
                GroupCode,
                QuestionText,
                PassageText,
                OptionA,
                OptionB,
                OptionC,
                OptionD,
                CorrectOptionKey,
                CorrectAnswerText,
                ExplanationText,
                VocabularyNotes,
                GrammarNotes,
                RawBlock
            )
            VALUES
            (
                :raw_document_id,
                :runtime_question_id,
                :test_type,
                :test_number,
                :part,
                :question_number,
                :group_code,
                :question_text,
                :passage_text,
                :option_a,
                :option_b,
                :option_c,
                :option_d,
                :correct_option_key,
                :correct_answer_text,
                :explanation_text,
                :vocabulary_notes,
                :grammar_notes,
                :raw_block
            )
            """
        ),
        {
            "raw_document_id": raw_document_id,
            "runtime_question_id": runtime_row.get("RuntimeQuestionId") if runtime_row else None,
            "test_type": target["test_type"],
            "test_number": target["test_number"],
            "part": int(item.get("part") or 0) or None,
            "question_number": int(item.get("questionNumber") or 0) or None,
            "group_code": runtime_row.get("GroupCode") if runtime_row else str(item.get("groupId") or "").strip() or None,
            "question_text": str(item.get("question") or ""),
            "passage_text": runtime_row.get("PassageText") if runtime_row and runtime_row.get("PassageText") else _get_passage_text(item),
            "option_a": options[0] if len(options) > 0 else None,
            "option_b": options[1] if len(options) > 1 else None,
            "option_c": options[2] if len(options) > 2 else None,
            "option_d": options[3] if len(options) > 3 else None,
            "correct_option_key": correct_key,
            "correct_answer_text": _option_by_key(options, correct_key),
            "explanation_text": explanation_text,
            "vocabulary_notes": vocabulary_notes,
            "grammar_notes": grammar_notes,
            "raw_block": raw_block or None,
        },
    )


def import_target(db: Session, target: dict[str, Any]) -> None:
    source_path = _resolve_source_path(target["source_candidates"])
    logger.info("Reading raw DOCX source: %s", source_path)
    raw_text = _read_docx_text(source_path)
    if not raw_text.strip():
        raise ValueError(f"Could not extract text from {source_path}")

    items = _load_manifest(str(target["manifest"]))
    runtime_lookup = _load_runtime_lookup(db, str(target["test_type"]), int(target["test_number"]))
    raw_document_id = _replace_raw_document(
        db,
        source_path,
        str(target["test_type"]),
        int(target["test_number"]),
        str(target["title"]),
        raw_text,
    )
    numbered_blocks = _build_numbered_blocks(raw_text)

    inserted = 0
    mapped = 0
    for item in items:
        part = int(item.get("part") or 0)
        question_number = int(item.get("questionNumber") or 0)
        runtime_row = runtime_lookup.get((part, question_number))
        if runtime_row:
            mapped += 1
        raw_block = _raw_block_for_item(raw_text, numbered_blocks, item)
        _insert_explanation_row(db, raw_document_id, target, item, runtime_row, raw_block)
        inserted += 1

    db.commit()
    logger.info(
        "Imported %s raw explanation rows for %s test=%s; mapped runtime questions=%s.",
        inserted,
        target["test_type"],
        target["test_number"],
        mapped,
    )


def main() -> None:
    _ensure_raw_tables()
    db = SessionLocal()
    try:
        for target in IMPORT_TARGETS:
            import_target(db, target)
        logger.info("TOEIC raw explanation import complete. Runner tables were not modified.")
    except Exception:
        db.rollback()
        logger.exception("TOEIC raw explanation import failed.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
