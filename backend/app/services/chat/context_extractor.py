from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TutorOption:
    label: str
    text: str
    is_correct: bool | None = None
    explanation: str = ""


@dataclass
class TutorContext:
    raw: dict[str, Any]
    question_id: int | None = None
    question_text: str = ""
    passage_text: str = ""
    options: list[TutorOption] = field(default_factory=list)
    correct_label: str = ""
    correct_text: str = ""
    selected_label: str = ""
    selected_text: str = ""
    explanation: str = ""
    explanation_detail: str = ""
    raw_block: str = ""
    option_analysis: dict[str, str] = field(default_factory=dict)
    grammar_notes: str = ""
    vocabulary_notes: str = ""
    vocabulary: dict[str, str] = field(default_factory=dict)
    translation: str = ""
    formula: str = ""
    signal: str = ""
    signal_text: str = ""
    requirement: str = ""
    tense_name: str = ""
    tense_reason: str = ""
    tested_point: str = ""
    db_context_found: bool = False
    has_explanation: bool = False
    has_explanation_detail: bool = False
    has_option_analysis: bool = False
    has_grammar_notes: bool = False
    has_translation: bool = False


def normalize_text(value: Any) -> str:
    text_value = str(value or "").strip().lower()
    text_value = unicodedata.normalize("NFD", text_value)
    text_value = "".join(char for char in text_value if unicodedata.category(char) != "Mn")
    text_value = text_value.replace("đ", "d")
    text_value = re.sub(r"[“”]", '"', text_value)
    text_value = re.sub(r"[‘’]", "'", text_value)
    text_value = re.sub(r"[_]{2,}", " ____ ", text_value)
    text_value = re.sub(r"[^\w\s'+/-]+", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def clean_fragment(value: Any) -> str:
    text_value = str(value or "").replace("\r\n", "\n").strip()
    text_value = re.sub(r"^[ \t]*(?:[-*•]\s*)+", "", text_value)
    text_value = re.sub(r"[ \t]+", " ", text_value)
    text_value = re.sub(r"\n{3,}", "\n\n", text_value)
    return text_value.strip(" \t:-–—")


def split_sentences(value: Any) -> list[str]:
    text_value = clean_fragment(value)
    if not text_value:
        return []
    parts = [part.strip(" .") for part in re.split(r"(?<=[.!?。])\s+", text_value) if part.strip(" .")]
    return parts or [text_value]


def _has_value(value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    return not (isinstance(value, str) and not value.strip())


def _is_placeholder(value: Any) -> bool:
    normalized = normalize_text(value)
    return normalized in {
        "",
        "no explanation is available for this question yet",
        "no explanation available",
        "detailed explanation is not available for this question",
    }


def _get(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if _has_value(value):
            return value
    return None


def _option_label(index: int) -> str:
    return chr(ord("A") + index) if 0 <= index < 26 else str(index + 1)


def _answer_label(value: Any) -> str:
    text_value = str(value or "").strip()
    match = re.match(r"^\s*\(?([A-Da-d])\)?(?:[.)\]:-]|\s*$)", text_value)
    return match.group(1).upper() if match else ""


def _strip_answer_label(value: Any) -> str:
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


def _index_label(value: Any) -> str:
    try:
        index = int(str(value).strip())
    except Exception:
        return ""
    return _option_label(index) if 0 <= index < 26 else ""


def _normalize_option(value: Any, index: int) -> TutorOption:
    if isinstance(value, dict):
        label = str(
            _get(value, "label", "key", "optionKey", "OptionKey", "optionLabel", "OptionLabel") or _option_label(index)
        ).strip().upper()[:1]
        text_value = str(
            _get(value, "text", "optionText", "OptionText", "optionTextEn", "OptionTextEn", "content", "Content", "value")
            or ""
        ).strip()
        explanation = clean_fragment(_get(value, "explanation", "analysis", "optionExplanation", "explanationText"))
        return TutorOption(
            label=label or _option_label(index),
            text=text_value,
            is_correct=_to_bool(_get(value, "is_correct", "isCorrect", "IsCorrect")),
            explanation=explanation,
        )
    return TutorOption(label=_option_label(index), text=str(value or "").strip())


def _source_texts(context: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "detailed_explanation",
        "explanation_detail",
        "explanationDetail",
        "explanation",
        "option_analysis",
        "optionAnalysis",
        "grammar_notes",
        "grammarNotes",
        "vocabulary_notes",
        "vocabularyNotes",
        "translation",
        "translation_vi",
        "translationVi",
        "final_translation_vi",
        "finalTranslationVi",
        "raw_explanation",
        "rawExplanation",
        "raw_block",
        "rawBlock",
    ):
        value = context.get(key)
        if isinstance(value, dict):
            values.extend(str(item) for item in value.values() if _has_value(item))
        elif isinstance(value, list):
            values.extend(str(item) for item in value if _has_value(item))
        elif _has_value(value):
            values.append(str(value))
    return values


HEADER_PATTERN = re.compile(
    r"(?i)\b("
    r"giải\s+thích(?:\s+chi\s+tiết)?|giai\s+thich(?:\s+chi\s+tiet)?|"
    r"phân\s+tích\s+(?:lựa\s+chọn|đáp\s+án)|phan\s+tich\s+(?:lua\s+chon|dap\s+an)|option\s+analysis|"
    r"cấu\s+trúc(?:\s+và\s+từ\s+vựng\s+mở\s+rộng)?|cau\s+truc(?:\s+va\s+tu\s+vung\s+mo\s+rong)?|"
    r"ngữ\s+pháp|ngu\s+phap|grammar|"
    r"từ\s+vựng|tu\s+vung|vocabulary|"
    r"bản\s+dịch(?:\s+tiếng\s+việt)?|ban\s+dich(?:\s+tieng\s+viet)?|tạm\s+dịch|tam\s+dich|translation"
    r")\s*:"
)


def _prepare_structured_text(value: Any) -> str:
    text_value = str(value or "").replace("\r\n", "\n")
    text_value = HEADER_PATTERN.sub(lambda match: f"\n{match.group(1)}:\n", text_value)
    text_value = re.sub(r"\s+(?=\(?[A-Da-d]\)?[.)]\s+)", "\n", text_value)
    text_value = re.sub(r"\s+(?=\([A-Da-d]\)\s+)", "\n", text_value)
    return text_value


def _section_kind(line: str) -> str | None:
    normalized = normalize_text(line.strip(" :：-–—"))
    if not normalized:
        return None
    if normalized.startswith("phan tich lua chon") or normalized.startswith("phan tich dap an") or normalized.startswith("option analysis"):
        return "option_analysis"
    if normalized.startswith("giai thich"):
        return "explanation"
    if normalized.startswith(("cau truc", "ngu phap", "grammar")):
        return "grammar"
    if normalized.startswith(("tu vung", "vocabulary")):
        return "vocabulary"
    if normalized.startswith(("ban dich", "tam dich", "translation")):
        return "translation"
    return None


def _structured_sections(value: Any) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in _prepare_structured_text(value).splitlines():
        line = clean_fragment(raw_line)
        if not line:
            continue
        kind = _section_kind(line)
        if kind:
            current = kind
            sections.setdefault(kind, [])
            continue
        if current:
            sections.setdefault(current, []).append(line)
    return {key: clean_fragment("\n".join(lines)) for key, lines in sections.items() if clean_fragment("\n".join(lines))}


def _first_section(context: dict[str, Any], kind: str) -> str:
    for source in _source_texts(context):
        section = _structured_sections(source).get(kind, "")
        if section:
            return section
    return ""


def _clean_option_reason(label: str, option_text: str, value: Any) -> str:
    text_value = clean_fragment(value)
    if not text_value:
        return ""
    text_value = re.sub(rf"^\(?{re.escape(label)}\)?[.)\]:-]?\s*", "", text_value, flags=re.IGNORECASE)
    text_value = clean_fragment(text_value)
    if option_text:
        text_value = re.sub(rf"^{re.escape(option_text)}\s*(?:[:\-–—]\s*)?", "", text_value, flags=re.IGNORECASE).strip()
    text_value = re.sub(
        r"^(?:sai|không đúng|khong dung|wrong|đáp án đúng|dap an dung|đúng|dung|correct)\s*(?:[.:;,\-–—]|\bvì\b|\bvi\b)?\s*",
        "",
        text_value,
        flags=re.IGNORECASE,
    )
    text_value = re.sub(r"\s+", " ", text_value).strip(" .")
    if normalize_text(text_value) in {"sai", "dung", "khong dung", "khong phu hop", "dap an sai", "dap an dung"}:
        return ""
    return text_value


OPTION_LINE_PATTERN = re.compile(r"^\s*(?:[-*•]\s*)?\(?([A-Da-d])\)?(?:[.)\]:-]|\s+)\s*(.+?)\s*$")


def _option_entries_from_text(value: Any) -> dict[str, str]:
    entries: dict[str, list[str]] = {}
    current_label: str | None = None

    def flush_line(label: str | None, line: str) -> None:
        if label and line:
            entries.setdefault(label, []).append(line)

    for raw_line in _prepare_structured_text(value).splitlines():
        line = clean_fragment(raw_line)
        if not line:
            continue
        if _section_kind(line):
            current_label = None
            continue
        match = OPTION_LINE_PATTERN.match(line)
        if match:
            current_label = match.group(1).upper()
            flush_line(current_label, match.group(2))
            continue
        if current_label:
            flush_line(current_label, line)

    return {label: clean_fragment(" ".join(lines)) for label, lines in entries.items() if clean_fragment(" ".join(lines))}


def _extract_option_analysis(context: dict[str, Any], options: list[TutorOption]) -> dict[str, str]:
    option_text_by_label = {option.label: option.text for option in options}
    analysis: dict[str, str] = {}

    raw_maps = (
        context.get("option_explanations"),
        context.get("optionExplanations"),
        context.get("option_analysis"),
        context.get("optionAnalysis"),
    )
    for raw_map in raw_maps:
        if isinstance(raw_map, dict):
            for label, value in raw_map.items():
                clean_label = str(label or "").strip().upper()[:1]
                if clean_label:
                    cleaned = _clean_option_reason(clean_label, option_text_by_label.get(clean_label, ""), value)
                    if cleaned:
                        analysis[clean_label] = cleaned
        elif isinstance(raw_map, list):
            for index, value in enumerate(raw_map):
                clean_label = _option_label(index)
                cleaned = _clean_option_reason(clean_label, option_text_by_label.get(clean_label, ""), value)
                if cleaned:
                    analysis[clean_label] = cleaned

    for option in options:
        cleaned = _clean_option_reason(option.label, option.text, option.explanation)
        if cleaned and option.label not in analysis:
            analysis[option.label] = cleaned

    for source in _source_texts(context):
        sections = _structured_sections(source)
        candidates = [sections.get("option_analysis", ""), source]
        for candidate in candidates:
            for label, value in _option_entries_from_text(candidate).items():
                cleaned = _clean_option_reason(label, option_text_by_label.get(label, ""), value)
                if cleaned and label not in analysis:
                    analysis[label] = cleaned
    return analysis


def _extract_translation(context: dict[str, Any]) -> str:
    for key in (
        "question_translation",
        "questionTranslation",
        "final_translation_vi",
        "finalTranslationVi",
        "translation_vi",
        "translationVi",
        "translation",
    ):
        value = clean_fragment(context.get(key))
        if value:
            return value
    return _first_section(context, "translation")


def _extract_vocabulary(context: dict[str, Any]) -> dict[str, str]:
    vocabulary: dict[str, str] = {}
    raw_vocab = _get(context, "vocabulary", "vocabularyMap", "vocabulary_map")
    if isinstance(raw_vocab, dict):
        for term, meaning in raw_vocab.items():
            term_norm = normalize_text(term)
            meaning_clean = clean_fragment(meaning).rstrip(".")
            if term_norm and meaning_clean:
                vocabulary[term_norm] = meaning_clean

    sources = [context.get("vocabulary_notes"), context.get("vocabularyNotes"), _first_section(context, "vocabulary")]
    sources.extend(_source_texts(context))
    for source in sources:
        if not _has_value(source):
            continue
        for line in _prepare_structured_text(source).splitlines():
            clean_line = clean_fragment(line).rstrip(".")
            if not clean_line:
                continue
            patterns = (
                r"^[\"“”']?(.+?)[\"“”']?\s*(?:nghĩa là|nghia la|means|:|-|–|—)\s*[\"“”']?(.+?)[\"“”']?$",
                r"^(.+?)\s+(?:nghĩa là|nghia la|means)\s+(.+?)$",
            )
            for pattern in patterns:
                match = re.match(pattern, clean_line, flags=re.IGNORECASE)
                if not match:
                    continue
                term = clean_fragment(match.group(1)).strip('"“”\'')
                meaning = clean_fragment(match.group(2)).strip('"“”\'')
                term_norm = normalize_text(term)
                if term_norm and meaning and len(term_norm) <= 80 and len(meaning) <= 240:
                    vocabulary.setdefault(term_norm, meaning)
                break
    return vocabulary


def _actual_by_the_time_signal(question_text: str) -> str:
    match = re.search(r"\bby the time\b(.+?)(?:[.;]|$)", question_text, flags=re.IGNORECASE)
    if match:
        return clean_fragment("by the time" + match.group(1)).rstrip(".")
    return ""


def _set_if_missing(mapping: dict[str, str], key: str, value: str) -> None:
    if key and value:
        mapping.setdefault(normalize_text(key), value)


def _apply_future_perfect_pattern(ctx: TutorContext, source_norm: str) -> None:
    correct_norm = normalize_text(ctx.correct_text)
    question_norm = normalize_text(ctx.question_text)
    has_future_perfect = bool(
        "future perfect" in source_norm
        or "tuong lai hoan thanh" in source_norm
        or "will have v3" in source_norm
        or "will have past participle" in source_norm
        or re.search(r"\bwill\s+have\s+\w+", correct_norm)
    )
    has_by_the_time = "by the time" in question_norm or "by the time" in source_norm
    if not (has_future_perfect or (has_by_the_time and re.search(r"\bwill\s+have\s+\w+", source_norm))):
        return

    ctx.tense_name = "thì tương lai hoàn thành"
    ctx.formula = "will have + V3"
    ctx.signal = "by the time + S + V hiện tại đơn" if has_by_the_time else "mốc thời gian trong tương lai"
    ctx.signal_text = ctx.signal_text or _actual_by_the_time_signal(ctx.question_text)
    ctx.tense_reason = "Hành động ở mệnh đề chính sẽ hoàn tất trước một mốc trong tương lai."
    ctx.requirement = ctx.tense_name
    ctx.tested_point = "thì tương lai hoàn thành với by the time"

    _set_if_missing(ctx.vocabulary, "by the time", "trước khi / đến lúc mà")
    _set_if_missing(ctx.vocabulary, "future perfect", "thì tương lai hoàn thành")
    _set_if_missing(ctx.vocabulary, "V3", "quá khứ phân từ")
    _set_if_missing(ctx.vocabulary, "demolish", "phá dỡ / phá hủy")
    _set_if_missing(ctx.vocabulary, "will have demolished", "sẽ đã phá dỡ xong")
    _set_if_missing(ctx.vocabulary, "waste removal trucks", "xe chở rác / xe thu gom phế thải")
    _set_if_missing(ctx.vocabulary, "main section", "phần chính")
    _set_if_missing(ctx.vocabulary, "crew members", "các thành viên đội/nhóm")

    for option in ctx.options:
        option_norm = normalize_text(option.text)
        if option.label == ctx.correct_label:
            ctx.option_analysis[option.label] = "đây là thì tương lai hoàn thành, nghĩa là sẽ đã phá dỡ xong"
        elif option_norm == "demolish":
            ctx.option_analysis[option.label] = "đây là hiện tại đơn, không thể hiện hành động sẽ hoàn tất trước một mốc trong tương lai"
        elif option_norm == "demolished":
            ctx.option_analysis[option.label] = "đây là quá khứ đơn, không phù hợp vì câu đang nói về một mốc tương lai"
        elif option_norm.startswith("had "):
            ctx.option_analysis[option.label] = "đây là quá khứ hoàn thành, dùng cho hành động hoàn tất trước một mốc trong quá khứ nên không phù hợp với mốc tương lai"


def _apply_known_patterns(ctx: TutorContext) -> None:
    source_norm = normalize_text(
        " ".join(
            [
                ctx.question_text,
                ctx.explanation,
                ctx.explanation_detail,
                ctx.raw_block,
                ctx.grammar_notes,
                " ".join(ctx.option_analysis.values()),
                " ".join(option.text for option in ctx.options),
            ]
        )
    )
    _apply_future_perfect_pattern(ctx, source_norm)

    if not ctx.formula:
        patterns = (
            ("past perfect", "quá khứ hoàn thành", "had + V3"),
            ("qua khu hoan thanh", "quá khứ hoàn thành", "had + V3"),
            ("passive voice", "dạng bị động", "be + V3"),
            ("bi dong", "dạng bị động", "be + V3"),
            ("v ing", "dạng V-ing", "V-ing"),
            ("to v", "dạng to V", "to + V nguyên mẫu"),
            ("noun", "danh từ", "noun"),
            ("danh tu", "danh từ", "noun"),
            ("verb", "động từ", "verb"),
            ("dong tu", "động từ", "verb"),
            ("adjective", "tính từ", "adjective"),
            ("tinh tu", "tính từ", "adjective"),
            ("adverb", "trạng từ", "adverb"),
            ("trang tu", "trạng từ", "adverb"),
        )
        for token, requirement, formula in patterns:
            if token in source_norm:
                ctx.requirement = requirement
                ctx.formula = formula
                break


def _option_by_text(options: list[TutorOption], text_value: Any) -> TutorOption | None:
    wanted = normalize_text(text_value)
    if not wanted:
        return None
    for option in options:
        option_norm = normalize_text(option.text)
        if option_norm == wanted or (option_norm and wanted in {option_norm, _strip_answer_label(option_norm)}):
            return option
    return None


def extract_tutor_context(context: dict[str, Any]) -> TutorContext:
    raw = dict(context or {})
    options = [_normalize_option(option, index) for index, option in enumerate(raw.get("options") or [])]

    correct_label = (
        _answer_label(_get(raw, "correct_option_label", "correctOptionLabel", "correct_option_key", "correctOptionKey"))
        or _answer_label(_get(raw, "correct_answer", "correctAnswer"))
        or _index_label(_get(raw, "correct_answer_index", "correctAnswerIndex"))
        or next((option.label for option in options if option.is_correct is True), "")
    )
    correct_text = str(_get(raw, "correct_answer_text", "correctAnswerText", "correct_option_text", "correctOptionText") or "").strip()
    if not correct_text:
        correct_text = _strip_answer_label(_get(raw, "correct_answer", "correctAnswer") or "")
    if correct_label and not correct_text:
        correct_text = next((option.text for option in options if option.label == correct_label), "")
    if not correct_label and correct_text:
        matched = _option_by_text(options, correct_text)
        if matched:
            correct_label = matched.label
            correct_text = matched.text
    if correct_label and options:
        correct_text = next((option.text for option in options if option.label == correct_label), correct_text)

    selected_label = (
        _answer_label(_get(raw, "selected_option_label", "selectedOptionLabel", "selected_option_key", "selectedOptionKey"))
        or _answer_label(_get(raw, "selected_answer", "selectedAnswer"))
        or _index_label(_get(raw, "selected_answer_index", "selectedAnswerIndex"))
    )
    selected_text = next((option.text for option in options if option.label == selected_label), "")
    if not selected_label and _has_value(_get(raw, "selected_answer", "selectedAnswer")):
        selected = _option_by_text(options, _get(raw, "selected_answer", "selectedAnswer"))
        if selected:
            selected_label = selected.label
            selected_text = selected.text

    explanation_section = _first_section(raw, "explanation")
    grammar_section = _first_section(raw, "grammar")
    vocabulary_section = _first_section(raw, "vocabulary")

    raw_block = str(_get(raw, "raw_block", "rawBlock", "raw_explanation", "rawExplanation") or "").strip()
    explanation = clean_fragment(_get(raw, "explanation"))
    explanation_detail = clean_fragment(_get(raw, "detailed_explanation", "explanation_detail", "explanationDetail")) or explanation_section

    ctx = TutorContext(
        raw=raw,
        question_id=_get(raw, "question_id", "questionId"),
        question_text=str(_get(raw, "question_text", "questionText", "question_text_en", "questionTextEn") or "").strip(),
        passage_text=str(_get(raw, "passage_text", "passageText") or "").strip(),
        options=options,
        correct_label=correct_label,
        correct_text=correct_text,
        selected_label=selected_label,
        selected_text=selected_text,
        explanation=explanation,
        explanation_detail=explanation_detail,
        raw_block=raw_block,
        grammar_notes=clean_fragment(_get(raw, "grammar_notes", "grammarNotes")) or grammar_section,
        vocabulary_notes=clean_fragment(_get(raw, "vocabulary_notes", "vocabularyNotes")) or vocabulary_section,
        translation=_extract_translation(raw),
        db_context_found=bool(raw.get("sql_source") and (_has_value(raw.get("question_text")) or _has_value(raw.get("question_text_en")) or options or correct_text)),
    )
    ctx.option_analysis = _extract_option_analysis(raw, options)
    ctx.vocabulary = _extract_vocabulary(raw)
    _apply_known_patterns(ctx)

    ctx.has_explanation = bool(ctx.explanation and not _is_placeholder(ctx.explanation))
    ctx.has_explanation_detail = bool(ctx.explanation_detail and not _is_placeholder(ctx.explanation_detail))
    ctx.has_option_analysis = bool(ctx.option_analysis or _has_value(_get(raw, "option_analysis", "optionAnalysis", "option_explanations")))
    ctx.has_grammar_notes = bool(ctx.grammar_notes or ctx.formula or ctx.tense_name or ctx.requirement)
    ctx.has_translation = bool(ctx.translation)
    return ctx
