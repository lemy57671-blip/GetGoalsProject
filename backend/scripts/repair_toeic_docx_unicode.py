from __future__ import annotations

import argparse
import logging
import re
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
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

WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

SOURCE_CANDIDATES = [
    BACKEND_ROOT / "runtime" / "static" / "toeic" / "raw" / "De_luyen_toeic_synced_audio.docx",
    BACKEND_ROOT / "runtime" / "source_materials" / "toeic_synced_bundle" / "De_luyen_toeic_synced_audio.docx",
    BACKEND_ROOT / "runtime" / "source_materials" / "De_luyen_toeic_synced_audio.docx",
    PROJECT_ROOT / "toeic_synced_bundle" / "De_luyen_toeic_synced_audio.docx",
    PROJECT_ROOT / "De_luyen_toeic_synced_audio.docx",
    Path("D:/Downloads/toeic_synced_bundle/De_luyen_toeic_synced_audio.docx"),
    Path("D:/Downloads/1/toeic_synced_bundle/De_luyen_toeic_synced_audio.docx"),
    Path("D:/Downloads/1/De_luyen_toeic_synced_audio.docx"),
]

UNICODE_COLUMNS = [
    "QuestionTextEn",
    "TranslationVi",
    "ExplanationDetail",
    "OptionAnalysis",
    "VocabularyNotes",
    "FinalTranslationVi",
    "RawBlock",
]

PART_RE = re.compile(r"^\s*Part\s+(\d+)\b", flags=re.IGNORECASE)
TEST_RE = re.compile(r"^\s*Test\s+(\d+)\b", flags=re.IGNORECASE)
QUESTION_RE = re.compile(
    r"^\s*C(?:au|\u00e2u)(?:\s+h(?:oi|\u1ecfi))?\s*(\d{1,3})[\s.):\-]*(.*)$",
    flags=re.IGNORECASE | re.DOTALL,
)
OPTION_RE = re.compile(r"^\s*\(([A-D])\)\s*(.*)$", flags=re.IGNORECASE)
LETTER_OPTION_RE = re.compile(r"^\s*([A-D])[.)]\s+(.*)$", flags=re.IGNORECASE)
OPTION_INLINE_RE = re.compile(
    r"(?:\(([A-D])\)|\b([A-D])[.)])\s*(.*?)(?=\s*(?:\([A-D]\)|\b[A-D][.)]\s+)|\s*(?:Gi\u1ea3i|Ph\u00e2n|C\u1ea5u|Ki\u1ebfn|T\u1eeb|B\u1ea3n|T\u1ea1m|Th\u00f4ng|C(?:au|\u00e2u)|Part|Test)\b|$)",
    flags=re.IGNORECASE | re.DOTALL,
)

EXPLANATION_LABELS = [
    r"Gi\u1ea3i\s+th\u00edch\s+chi\s+ti\u1ebft\s*:",
    r"Gi\u1ea3i\s+th\u00edch\s*:",
]
ANALYSIS_LABELS = [
    r"Ph\u00e2n\s+t\u00edch\s+l\u1ef1a\s+ch\u1ecdn\s+v\u00e0\s+gi\u1ea3i\s+th\u00edch\s+ngh\u0129a\s*:",
    r"Ph\u00e2n\s+t\u00edch\s+l\u1ef1a\s+ch\u1ecdn\s*:",
]
VOCAB_LABELS = [
    r"Ki\u1ebfn\s+th\u1ee9c\s+t\u1eeb\s+v\u1ef1ng\s*:",
    r"C\u1ea5u\s+tr\u00fac\s+v\u00e0\s+t\u1eeb\s+v\u1ef1ng\s+m\u1edf\s+r\u1ed9ng\s*:",
    r"T\u1eeb\s+v\u1ef1ng\s+m\u1edf\s+r\u1ed9ng\s*:",
    r"m\u1edf\s+r\u1ed9ng\s*:",
    r"C\u1ea5u\s+tr\u00fac\s*:",
]
TRANSLATION_LABELS = [
    r"B\u1ea3n\s+d\u1ecbch\s+(?:t|T)i\u1ebfng\s+Vi\u1ec7t(?:\s+c\u1ee7a\s+c\u00e2u\s+\u0111\u00e3\s+ho\u00e0n\s+ch\u1ec9nh)?\s*:",
    r"T\u1ea1m\s+d\u1ecbch\s*:",
]
INFO_LABELS = [
    r"Th\u00f4ng\s+tin\s*:",
]

TARGET_REPAIR_COLUMNS = [
    "TranslationVi",
    "ExplanationDetail",
    "OptionAnalysis",
    "VocabularyNotes",
    "FinalTranslationVi",
    "RawBlock",
]

SPECIFIC_BROKEN_PATTERNS = [
    "G?n",
    "?ây",
    "S?n ph?m",
    "V? trí",
    "c?n ?i?n",
    "d?ng t?",
    "m?t danh t?",
    "Câu h?i",
    "T?m d?ch",
    "c?a",
    "b?n",
    "??a",
    "???c",
    "?i?u",
]
BROKEN_REPLACEMENT_RE = re.compile(r"\?{2,}|\?[A-Za-zÀ-ỹ]|[A-Za-zÀ-ỹ]\?[A-Za-zÀ-ỹ]")


@dataclass
class ParsedDocxQuestion:
    test_number: int | None
    part_number: int | None
    question_number: int
    question_text: str
    option_signature: tuple[str, ...]
    raw_block: str
    explanation_detail: str | None
    option_analysis: str | None
    vocabulary_notes: str | None
    final_translation_vi: str | None

    @property
    def translation_vi(self) -> str | None:
        return self.final_translation_vi


def _resolve_source_path(explicit_path: str | None = None) -> Path:
    candidates = [Path(explicit_path)] if explicit_path else SOURCE_CANDIDATES
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find De_luyen_toeic_synced_audio.docx. Checked: "
        + ", ".join(str(item) for item in candidates)
    )


def _read_docx_paragraphs(path: Path) -> list[str]:
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
        value = "".join(parts).strip()
        if value:
            paragraphs.append(value)
    return paragraphs


def _expand_embedded_blocks(paragraphs: list[str]) -> list[str]:
    """Split DOCX paragraphs that contain headings, questions, options, and notes inline."""
    text_value = "\n".join(paragraphs)
    markers = [
        r"(Part\s+\d+\b)",
        r"(Test\s+\d+\b)",
        r"(C(?:au|\u00e2u)(?:\s+h(?:oi|\u1ecfi))?\s*\d{1,3}[\s.):\-])",
        r"(\([A-D]\))",
        r"(Gi\u1ea3i\s+th\u00edch\s+chi\s+ti\u1ebft\s*:)",
        r"(Gi\u1ea3i\s+th\u00edch\s*:)",
        r"(Ph\u00e2n\s+t\u00edch\s+l\u1ef1a\s+ch\u1ecdn\s*:)",
        r"(Ki\u1ebfn\s+th\u1ee9c\s+t\u1eeb\s+v\u1ef1ng\s*:)",
        r"(C\u1ea5u\s+tr\u00fac\s+v\u00e0\s+t\u1eeb\s+v\u1ef1ng\s+m\u1edf\s+r\u1ed9ng\s*:)",
        r"(C\u1ea5u\s+tr\u00fac\s*:)",
        r"(T\u1eeb\s+v\u1ef1ng\s+m\u1edf\s+r\u1ed9ng\s*:)",
        r"(B\u1ea3n\s+d\u1ecbch\s+(?:t|T)i\u1ebfng\s+Vi\u1ec7t(?:\s+c\u1ee7a\s+c\u00e2u\s+\u0111\u00e3\s+ho\u00e0n\s+ch\u1ec9nh)?\s*:)",
        r"(T\u1ea1m\s+d\u1ecbch\s*:)",
        r"(Th\u00f4ng\s+tin\s*:)",
    ]
    for marker in markers:
        text_value = re.sub(rf"(?<!^)(?<!\n)\s+{marker}", r"\n\1", text_value, flags=re.IGNORECASE)
    return [line.strip() for line in text_value.splitlines() if line.strip()]


def _normalize_question_text(value: Any) -> str:
    text_value = str(value or "").strip().lower()
    text_value = text_value.replace("\u2019", "'").replace("\u2018", "'")
    text_value = re.sub(r"_+", "_____", text_value)
    text_value = re.sub(r"\s+", " ", text_value)
    text_value = re.sub(r"([?!.])\s+", r"\1", text_value)
    text_value = re.sub(r"([?!.])\s+([\"'\u201c\u201d])", r"\1\2", text_value)
    return text_value


def _normalize_option_text(value: Any) -> str:
    return _normalize_question_text(value)


def _clean_question_text(value: str) -> str:
    cleaned = str(value or "").strip()
    cleaned = re.sub(r"^(?:0020)+", "", cleaned)
    return cleaned.strip()


def _strip_question_tail(value: str) -> str:
    stop_patterns = [
        r"\([A-D]\)",
        r"\s+[A-D][.)]\s+",
        *EXPLANATION_LABELS,
        *ANALYSIS_LABELS,
        *VOCAB_LABELS,
        *TRANSLATION_LABELS,
        *INFO_LABELS,
    ]
    match = re.search("|".join(stop_patterns), value, flags=re.IGNORECASE)
    if match:
        return value[: match.start()].strip()
    return value.strip()


def _find_label(raw_block: str, label_patterns: list[str], start_pos: int = 0) -> re.Match[str] | None:
    best_match: re.Match[str] | None = None
    for pattern in label_patterns:
        match = re.search(pattern, raw_block[start_pos:], flags=re.IGNORECASE)
        if not match:
            continue
        absolute_start = start_pos + match.start()
        if best_match is None or absolute_start < start_pos + best_match.start():
            best_match = match
    return best_match


def _extract_section(raw_block: str, start_labels: list[str], end_labels: list[str]) -> str | None:
    start_match = _find_label(raw_block, start_labels)
    if not start_match:
        return None
    body_start = start_match.end()
    body_end = len(raw_block)
    for pattern in end_labels:
        match = re.search(pattern, raw_block[body_start:], flags=re.IGNORECASE)
        if match:
            body_end = min(body_end, body_start + match.start())
    body = raw_block[body_start:body_end].strip()
    return body or None


def _extract_question_text(lines: list[str], first_line_text: str) -> str:
    parts: list[str] = []
    if first_line_text.strip():
        cleaned = _strip_question_tail(_clean_question_text(first_line_text))
        if cleaned:
            parts.append(cleaned)
    for line in lines[1:]:
        if _is_option_line(line):
            break
        if _find_label(line, [*EXPLANATION_LABELS, *ANALYSIS_LABELS, *VOCAB_LABELS, *TRANSLATION_LABELS, *INFO_LABELS]):
            break
        cleaned = _strip_question_tail(_clean_question_text(line))
        if cleaned:
            parts.append(cleaned)
    return " ".join(parts).strip()


def _is_option_line(value: str) -> bool:
    return bool(OPTION_RE.match(value) or LETTER_OPTION_RE.match(value))


def _extract_option_texts(raw_block: str) -> list[str]:
    options: list[str] = []
    for match in OPTION_INLINE_RE.finditer(raw_block):
        option_text = (match.group(3) or "").strip()
        if option_text:
            options.append(option_text)
    return options


def _extract_unlabeled_tail(lines: list[str]) -> str | None:
    last_option_index = -1
    for index, line in enumerate(lines):
        if _is_option_line(line):
            last_option_index = index
    if last_option_index < 0 or last_option_index + 1 >= len(lines):
        return None
    tail = "\n".join(line.strip() for line in lines[last_option_index + 1 :] if line.strip()).strip()
    if not tail:
        return None
    if not re.search(r"[À-ỹ]", tail):
        return None
    return tail


def _build_question(raw_lines: list[str], test_number: int | None, part_number: int | None, question_number: int, first_line_text: str) -> ParsedDocxQuestion:
    raw_block = "\n".join(raw_lines).strip()
    question_text = _extract_question_text(raw_lines, first_line_text)
    options = _extract_option_texts(raw_block)
    explanation_detail = _extract_section(
        raw_block,
        [*EXPLANATION_LABELS, *INFO_LABELS],
        [*ANALYSIS_LABELS, *VOCAB_LABELS, *TRANSLATION_LABELS],
    )
    option_analysis = _extract_section(
        raw_block,
        ANALYSIS_LABELS,
        [*VOCAB_LABELS, *TRANSLATION_LABELS],
    )
    vocabulary_notes = _extract_section(
        raw_block,
        VOCAB_LABELS,
        TRANSLATION_LABELS,
    )
    final_translation_vi = _extract_section(
        raw_block,
        TRANSLATION_LABELS,
        [*EXPLANATION_LABELS, *INFO_LABELS],
    )
    if not explanation_detail:
        explanation_detail = _extract_unlabeled_tail(raw_lines)
    return ParsedDocxQuestion(
        test_number=test_number,
        part_number=part_number,
        question_number=question_number,
        question_text=question_text,
        option_signature=tuple(_normalize_option_text(option) for option in options),
        raw_block=raw_block,
        explanation_detail=explanation_detail,
        option_analysis=option_analysis,
        vocabulary_notes=vocabulary_notes,
        final_translation_vi=final_translation_vi,
    )


def parse_docx_questions(path: Path) -> list[ParsedDocxQuestion]:
    paragraphs = _expand_embedded_blocks(_read_docx_paragraphs(path))
    questions: list[ParsedDocxQuestion] = []
    current_test: int | None = None
    current_part: int | None = None
    current_lines: list[str] = []
    current_question_number: int | None = None
    current_first_line_text = ""

    def flush_current() -> None:
        nonlocal current_lines, current_question_number, current_first_line_text
        if current_question_number is None or not current_lines:
            current_lines = []
            current_first_line_text = ""
            return
        questions.append(
            _build_question(
                current_lines,
                current_test,
                current_part,
                current_question_number,
                current_first_line_text,
            )
        )
        current_lines = []
        current_question_number = None
        current_first_line_text = ""

    for paragraph in paragraphs:
        part_match = PART_RE.match(paragraph)
        if part_match:
            flush_current()
            current_part = int(part_match.group(1))
            continue

        test_match = TEST_RE.match(paragraph)
        if test_match:
            flush_current()
            current_test = int(test_match.group(1))
            continue

        question_match = QUESTION_RE.match(paragraph)
        if question_match:
            flush_current()
            current_question_number = int(question_match.group(1))
            current_first_line_text = _clean_question_text(question_match.group(2))
            current_lines = [paragraph]
            continue

        if current_lines:
            current_lines.append(paragraph)

    flush_current()
    return questions


def _looks_broken_vietnamese(value: Any) -> bool:
    text_value = str(value or "")
    if "?" not in text_value:
        return False
    if any(pattern in text_value for pattern in SPECIFIC_BROKEN_PATTERNS):
        return True
    return bool(BROKEN_REPLACEMENT_RE.search(text_value))


def _contains_vietnamese(value: Any) -> bool:
    return bool(re.search(r"[À-ỹ]", str(value or "")))


def _row_needs_unicode_repair(row: dict[str, Any]) -> bool:
    return any(_looks_broken_vietnamese(row.get(column_name)) for column_name in TARGET_REPAIR_COLUMNS)


def _load_db_rows(db: Session, only_broken: bool = True) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT Id, TestNumber, PartNumber, QuestionNumber, QuestionTextEn,
                   TranslationVi, ExplanationDetail, OptionAnalysis,
                   VocabularyNotes, FinalTranslationVi, RawBlock
            FROM dbo.ToeicDocxQuestions
            ORDER BY Id
            """
        )
    ).mappings().all()
    result = [dict(row) for row in rows]
    options = db.execute(
        text(
            """
            SELECT QuestionId, OptionLabel, OptionTextEn
            FROM dbo.ToeicDocxOptions
            ORDER BY QuestionId, SortOrder, Id
            """
        )
    ).mappings().all()
    options_by_question: dict[int, list[str]] = defaultdict(list)
    for option in options:
        options_by_question[int(option["QuestionId"])].append(
            _normalize_option_text(option.get("OptionTextEn"))
        )
    for row in result:
        row["OptionSignature"] = tuple(options_by_question.get(int(row["Id"]), []))
    if only_broken:
        return [row for row in result if _row_needs_unicode_repair(row)]
    return result


def _build_lookup(questions: list[ParsedDocxQuestion]) -> tuple[dict[tuple[int | None, int | None, int, str], list[ParsedDocxQuestion]], dict[str, list[ParsedDocxQuestion]], dict[tuple[int | None, int | None, int], list[ParsedDocxQuestion]]]:
    by_full_key: dict[tuple[int | None, int | None, int, str], list[ParsedDocxQuestion]] = defaultdict(list)
    by_text: dict[str, list[ParsedDocxQuestion]] = defaultdict(list)
    by_position: dict[tuple[int | None, int | None, int], list[ParsedDocxQuestion]] = defaultdict(list)
    for question in questions:
        normalized = _normalize_question_text(question.question_text)
        if normalized:
            by_full_key[(question.test_number, question.part_number, question.question_number, normalized)].append(question)
            by_text[normalized].append(question)
        by_position[(question.test_number, question.part_number, question.question_number)].append(question)
    return by_full_key, by_text, by_position


def _match_question(
    row: dict[str, Any],
    by_full_key: dict[tuple[int | None, int | None, int, str], list[ParsedDocxQuestion]],
    by_text: dict[str, list[ParsedDocxQuestion]],
    by_position: dict[tuple[int | None, int | None, int], list[ParsedDocxQuestion]],
) -> tuple[ParsedDocxQuestion | None, str]:
    test_number = row.get("TestNumber")
    part_number = row.get("PartNumber")
    question_number = int(row.get("QuestionNumber") or 0)
    normalized_text = _normalize_question_text(row.get("QuestionTextEn"))

    candidates = by_full_key.get((test_number, part_number, question_number, normalized_text), [])
    if len(candidates) == 1:
        return candidates[0], "test_part_number_text"
    row_options = tuple(row.get("OptionSignature") or ())
    if row_options and len(candidates) > 1:
        option_matches = [item for item in candidates if item.option_signature == row_options]
        if len(option_matches) == 1:
            return option_matches[0], "test_part_number_text_options"

    if normalized_text:
        candidates = [
            item
            for item in by_text.get(normalized_text, [])
            if (not test_number or item.test_number == test_number)
            and (not part_number or item.part_number == part_number)
        ]
        if len(candidates) == 1:
            return candidates[0], "test_part_text"
        if row_options and len(candidates) > 1:
            option_matches = [item for item in candidates if item.option_signature == row_options]
            if len(option_matches) == 1:
                return option_matches[0], "test_part_text_options"

        candidates = [
            item
            for item in by_text.get(normalized_text, [])
            if (not test_number or item.test_number == test_number)
            and (not part_number or item.part_number == part_number)
            and item.question_number == question_number
        ]
        if len(candidates) == 1:
            return candidates[0], "number_text"
        if row_options and len(candidates) > 1:
            option_matches = [item for item in candidates if item.option_signature == row_options]
            if len(option_matches) == 1:
                return option_matches[0], "number_text_options"

        candidates = [
            item
            for item in by_text.get(normalized_text, [])
            if not test_number or item.test_number == test_number
        ]
        if len(candidates) == 1:
            return candidates[0], "test_text"
        if row_options and len(candidates) > 1:
            option_matches = [item for item in candidates if item.option_signature == row_options]
            if len(option_matches) == 1:
                return option_matches[0], "test_text_options"

        candidates = by_text.get(normalized_text, [])
        if len(candidates) == 1:
            return candidates[0], "text"
        if row_options and len(candidates) > 1:
            option_matches = [item for item in candidates if item.option_signature == row_options]
            if len(option_matches) == 1:
                return option_matches[0], "text_options"

    candidates = by_position.get((test_number, part_number, question_number), [])
    if len(candidates) == 1:
        candidate = candidates[0]
        if not normalized_text or _normalize_question_text(candidate.question_text) == normalized_text:
            return candidate, "test_part_number"

    return None, "unmatched"


def _ensure_nvarchar_columns() -> None:
    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'dbo'
                  AND TABLE_NAME = 'ToeicDocxQuestions'
                  AND COLUMN_NAME IN (
                      'QuestionTextEn',
                      'TranslationVi',
                      'ExplanationDetail',
                      'OptionAnalysis',
                      'VocabularyNotes',
                      'FinalTranslationVi',
                      'RawBlock'
                  )
                """
            )
        ).mappings().all()
        for row in rows:
            column_name = str(row["COLUMN_NAME"])
            data_type = str(row["DATA_TYPE"]).lower()
            if data_type != "nvarchar":
                logger.info("Altering dbo.ToeicDocxQuestions.%s from %s to NVARCHAR(MAX).", column_name, data_type)
                connection.exec_driver_sql(
                    f"ALTER TABLE dbo.ToeicDocxQuestions ALTER COLUMN [{column_name}] NVARCHAR(MAX) NULL"
                )


def _backup_table() -> str:
    base_name = f"ToeicDocxQuestions_Backup_FontFix_{datetime.now(UTC):%Y%m%d}"
    table_name = base_name
    with engine.begin() as connection:
        suffix = 1
        while connection.execute(
            text("SELECT OBJECT_ID(:table_name, N'U')"),
            {"table_name": f"dbo.{table_name}"},
        ).scalar():
            suffix += 1
            table_name = f"{base_name}_{suffix}"
        connection.exec_driver_sql(f"SELECT * INTO dbo.[{table_name}] FROM dbo.ToeicDocxQuestions")
    return table_name


def _update_question(db: Session, row_id: int, question: ParsedDocxQuestion) -> None:
    db.execute(
        text(
            """
            UPDATE dbo.ToeicDocxQuestions
            SET TranslationVi = COALESCE(:translation_vi, TranslationVi),
                ExplanationDetail = COALESCE(:explanation_detail, ExplanationDetail),
                OptionAnalysis = COALESCE(:option_analysis, OptionAnalysis),
                VocabularyNotes = COALESCE(:vocabulary_notes, VocabularyNotes),
                FinalTranslationVi = COALESCE(:final_translation_vi, FinalTranslationVi),
                RawBlock = COALESCE(:raw_block, RawBlock)
            WHERE Id = :row_id
            """
        ),
        {
            "row_id": row_id,
            "translation_vi": question.translation_vi,
            "explanation_detail": question.explanation_detail,
            "option_analysis": question.option_analysis,
            "vocabulary_notes": question.vocabulary_notes,
            "final_translation_vi": question.final_translation_vi,
            "raw_block": question.raw_block,
        },
    )


def repair_unicode(source_path: Path, apply: bool, only_broken: bool = True) -> dict[str, Any]:
    logger.info("Reading DOCX source: %s", source_path)
    parsed_questions = parse_docx_questions(source_path)
    parsed_with_vietnamese = [
        item
        for item in parsed_questions
        if item.explanation_detail
        or item.option_analysis
        or item.vocabulary_notes
        or item.final_translation_vi
        or _contains_vietnamese(item.raw_block)
    ]
    logger.info(
        "Parsed %s question blocks from DOCX; blocks with Vietnamese explanation fields=%s.",
        len(parsed_questions),
        len(parsed_with_vietnamese),
    )

    by_full_key, by_text, by_position = _build_lookup(parsed_with_vietnamese)

    if apply:
        _ensure_nvarchar_columns()
        backup_table = _backup_table()
        logger.info("Created backup table dbo.%s.", backup_table)
    else:
        backup_table = None
        logger.info("Dry run only. Pass --apply to create backup and update SQL Server.")

    stats: dict[str, Any] = {
        "parsed_blocks": len(parsed_questions),
        "parsed_blocks_with_vietnamese": len(parsed_with_vietnamese),
        "matched": 0,
        "updated": 0,
        "unmatched": 0,
        "match_strategies": defaultdict(int),
        "backup_table": backup_table,
        "sample_unmatched": [],
    }

    db = SessionLocal()
    try:
        rows = _load_db_rows(db, only_broken=only_broken)
        stats["candidate_rows"] = len(rows)
        for row in rows:
            match, strategy = _match_question(row, by_full_key, by_text, by_position)
            if not match:
                stats["unmatched"] += 1
                if len(stats["sample_unmatched"]) < 10:
                    stats["sample_unmatched"].append(
                        {
                            "id": row.get("Id"),
                            "test": row.get("TestNumber"),
                            "part": row.get("PartNumber"),
                            "question_number": row.get("QuestionNumber"),
                            "question_text": row.get("QuestionTextEn"),
                        }
                    )
                continue
            stats["matched"] += 1
            stats["match_strategies"][strategy] += 1
            if apply:
                _update_question(db, int(row["Id"]), match)
                stats["updated"] += 1
        if apply:
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    stats["match_strategies"] = dict(stats["match_strategies"])
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair Unicode-corrupted Vietnamese fields in dbo.ToeicDocxQuestions.")
    parser.add_argument("--source", help="Path to De_luyen_toeic_synced_audio.docx.")
    parser.add_argument("--apply", action="store_true", help="Create a backup table and update dbo.ToeicDocxQuestions.")
    parser.add_argument("--all", action="store_true", help="Scan every row instead of only rows that look Unicode-corrupted.")
    args = parser.parse_args()

    source_path = _resolve_source_path(args.source)
    stats = repair_unicode(source_path, apply=bool(args.apply), only_broken=not args.all)
    logger.info("Repair stats: %s", stats)


if __name__ == "__main__":
    main()
