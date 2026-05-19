from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Literal

from app.schemas.chat import ChatContextBundle, IntentResult

logger = logging.getLogger(__name__)

LocalIntent = Literal[
    "word_meaning",
    "collocation_preposition",
    "gap_requirement",
    "correct_answer",
    "option_reason",
    "full_option_analysis",
    "translation",
    "explanation",
    "hint",
    "grammar_structure",
    "grammar_formula_request",
    "target_completion_request",
    "grammar_structure_definition",
    "collocation_preposition_request",
    "relative_pronoun_request",
    "general",
]

NO_MATCH_REPLY = "Mình chưa tìm thấy dữ liệu phù hợp trong câu hiện tại."
GRAMMAR_FORMULA_NO_MATCH_REPLY = "Mình chưa tìm thấy công thức/cấu trúc này trong dữ liệu của câu hiện tại."
GRAMMAR_STRUCTURE_NO_MATCH_REPLY = "Mình chưa tìm thấy cấu trúc này trong dữ liệu của câu hiện tại."
PREPOSITIONS = (
    "from",
    "to",
    "with",
    "for",
    "of",
    "on",
    "in",
    "at",
    "by",
    "about",
    "into",
    "over",
    "under",
    "between",
    "among",
    "as",
)
GENERIC_TARGETS = {
    "",
    "a",
    "b",
    "c",
    "d",
    "answer",
    "cau nay",
    "cau",
    "de",
    "tu nay",
    "cum nay",
    "option",
    "dap an",
    "cho trong",
    "khoang trong",
    "o trong",
    "cong thuc",
    "cau truc",
    "cach dung",
    "loai tu",
    "nay",
    "này",
    "this",
    "this word",
    "this phrase",
    "cong thuc cua tu nay",
    "cau truc cua tu nay",
    "cach dung tu nay",
    "cong thuc cua cum nay",
    "cau truc cua cum nay",
    "cach dung cum nay",
    "ngu phap cua cau nay",
    "cau truc cua cau nay",
    "cau nay dung cau truc gi",
    "cau nay hoi ngu phap gi",
    "gi",
    "gì",
}


@dataclass
class ProviderResult:
    status_code: int
    reply: str
    raw_error: str | None = None


@dataclass
class AnswerMatch:
    text: str = ""
    source_field: str = ""
    target: str = ""
    option_label: str | None = None
    snippet: str = ""
    target_near_blank: bool = False
    completion: str = ""
    concept: str = ""
    aliases: tuple[str, ...] = ()


def normalize_text(text: Any) -> str:
    value = str(text or "").strip().lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = value.replace("đ", "d")
    value = re.sub(r"[“”]", '"', value)
    value = re.sub(r"[‘’]", "'", value)
    value = re.sub(r"[_]{2,}", " ____ ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_response(text: Any) -> str:
    value = str(text or "").replace("\r\n", "\n").strip()
    value = re.sub(r"```+", "", value)
    value = re.sub(r"\*\*+", "", value)
    value = re.sub(r"^[#>]+\s*", "", value, flags=re.MULTILINE)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def detect_intent(message: str) -> LocalIntent:
    text = normalize_text(message)
    option_label = extract_option_label(message)

    if _has_any(text, "goi y", "hint", "cho goi y", "nhac nhe"):
        return "hint"

    if _has_any(
        text,
        "phan tich dap an",
        "phan tich tung dap an",
        "giai thich a b c d",
        "giai thich abcd",
        "cac dap an con lai sai",
    ):
        return "full_option_analysis"

    if _has_any(
        text,
        "dap an la gi",
        "dap an dung",
        "chon gi",
        "chon dap an nao",
        "cau nao dung",
        "lua chon nao dung",
        "answer la gi",
        "correct answer",
        "which answer",
        "answer",
    ) and not _has_any(
        text,
        "vi sao",
        "tai sao",
        "sao",
        "why",
        "khong chon",
        "sai",
        "wrong",
        "giai thich",
        "phan tich",
        "explain",
    ):
        return "correct_answer"

    if option_label and _has_any(text, "vi sao", "tai sao", "sao", "sai", "dung", "wrong", "correct", "khong chon"):
        if _has_any(text, "la gi", "nghia la gi", "co nghia la gi") and not _has_any(text, "vi sao", "tai sao", "sai", "dung"):
            return "word_meaning"
        return "option_reason"

    if _has_any(text, "sai", "wrong", "khong chon", "khong phai") and _has_any(text, "vi sao", "tai sao", "sao", "why"):
        return "option_reason"

    if _has_any(text, "vi sao", "tai sao", "sao", "sai", "dung", "wrong", "correct", "khong chon") and extract_word_or_phrase(message, [], ""):
        return "option_reason"

    if _has_any(text, "dich cau", "dich de", "dich sang tieng viet", "dich doan", "cau nay nghia la gi"):
        return "translation"

    if _is_relative_pronoun_intent(text):
        return "relative_pronoun_request"

    if _is_collocation_preposition_intent(message, text):
        return "collocation_preposition_request"

    if _is_grammar_structure_definition_intent(text):
        return "grammar_structure_definition"

    if _is_target_completion_intent(text):
        return "target_completion_request"

    if _has_any(
        text,
        "cong thuc",
        "cach dung",
        "dung nhu the nao",
        "dung sao",
        "di voi gi",
        "di voi gioi tu",
        "gioi tu gi",
        "gioi tu nao",
        "dung voi gioi tu",
        "dung voi gi",
        "sau ",
        "truoc ",
        "cau truc ",
        "la loai tu gi",
        "la danh tu hay tinh tu",
        "cau nay dung cau truc gi",
        "ngu phap cua cau nay",
        "cau nay hoi ngu phap",
    ):
        return "grammar_formula_request"

    if _has_any(
        text,
        "khoang trong can",
        "cho trong can",
        "o trong can",
        "can loai tu",
        "can dang tu",
        "can danh tu",
        "can tinh tu",
        "can v-ing",
        "can v-ed",
        "sau cho trong",
        "cau nay can dang",
        "cau nay hoi ngu phap",
    ):
        return "grammar_formula_request"

    if _has_any(
        text,
        "ngu phap cau nay",
        "cau truc cau nay",
        "menh de nay",
        "sao dung bi dong",
        "sao dung v-ing",
        "sao dung trang tu",
    ):
        return "grammar_formula_request"

    if _has_any(text, "giai thich cau nay", "giai thich", "tai sao ra dap an", "vi sao chon dap an do"):
        return "explanation"

    if extract_word_or_phrase(message, [], ""):
        return "word_meaning"

    return "general"


def extract_option_label(message: str) -> str | None:
    text = normalize_text(message)
    number_match = re.search(r"\b(?:option|dap an|lua chon|chon)\s*([1-4])\b", text)
    if number_match:
        return chr(ord("A") + int(number_match.group(1)) - 1)

    patterns = [
        r"\b(?:option|dap an|lua chon|chon|dien)\s*([a-d])\b",
        r"\b([a-d])\s*(?:la gi|nghia la gi|co nghia la gi|sai|dung|wrong|correct)\b",
        r"\b(?:vi sao|tai sao|sao|khong chon|khong phai)\s+([a-d])\b",
        r"^([a-d])\s*$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).upper()
    return None


def extract_word_or_phrase(
    message: str,
    options: list[dict[str, Any]] | None = None,
    question_text: str | None = None,
) -> str | None:
    option_label = extract_option_label(message)
    normalized = normalize_text(message)
    if option_label and _has_any(normalized, "la gi", "nghia", "dich", "mean"):
        option = _find_option_by_label({"options": options or []}, option_label)
        if option:
            return _strip_answer_label(option.get("text"))

    quoted = re.findall(r"[\"“”']([^\"“”']+)[\"“”']", message)
    if quoted:
        target = _clean_target_phrase(quoted[0])
        if _is_useful_target(target):
            return target

    patterns = [
        r"(?:đại\s+từ\s+quan\s+hệ|dai\s+tu\s+quan\s+he)\s+(?:nào\s+)?(?:thay\s+thế\s+cho|thay\s+the\s+cho)\s+(.+?)(?:[?.!]|$)",
        r"(.+?)\s+(?:dùng\s+đại\s+từ\s+quan\s+hệ\s+gì|dung\s+dai\s+tu\s+quan\s+he\s+gi)",
        r"(.+?)\s+(?:đi\s+với\s+từ\s+gì|di\s+voi\s+tu\s+gi|đi\s+với\s+gì|di\s+voi\s+gi|kết\s+hợp\s+với\s+từ\s+nào|ket\s+hop\s+voi\s+tu\s+nao|collocation\s+là\s+gì|collocation\s+la\s+gi|tạo\s+cụm\s+gì|tao\s+cum\s+gi)",
        r"(.+?)\s+(?:ra\s+cụm\s+danh\s+từ\s+gì|ra\s+cum\s+danh\s+tu\s+gi|tạo\s+cụm\s+danh\s+từ\s+gì|tao\s+cum\s+danh\s+tu\s+gi)",
        r"(?:cụm\s+danh\s+từ\s+của|cum\s+danh\s+tu\s+cua)\s+(.+?)(?:\s+(?:là|la)|[?.!]|$)",
        r"(?:sau|trước|truoc)\s+(.+?)\s+(?:là\s+gì|la\s+gi|cần\s+gì|can\s+gi|cần\s+loại\s+từ\s+gì|can\s+loai\s+tu\s+gi|cần|can)",
        r"(?:công\s+thức|cong\s+thuc|cấu\s+trúc|cau\s+truc|cách\s+dùng|cach\s+dung)\s+(?:của|cua)?\s*(.+?)(?:\s+(?:là\s+gì|la\s+gi|như\s+thế\s+nào|nhu\s+the\s+nao|ra\s+sao|dùng|dung)|[?.!]|$)",
        r"(.+?)\s+(?:công\s+thức|cong\s+thuc|cấu\s+trúc|cau\s+truc)\s+(?:là\s+gì|la\s+gi)",
        r"(.+?)\s+(?:dùng\s+như\s+thế\s+nào|dung\s+nhu\s+the\s+nao|dùng\s+sao|dung\s+sao|cách\s+dùng|cach\s+dung)",
        r"(.+?)\s+(?:là\s+loại\s+từ\s+gì|la\s+loai\s+tu\s+gi|là\s+danh\s+từ\s+hay\s+tính\s+từ|la\s+danh\s+tu\s+hay\s+tinh\s+tu)",
        r"(.+?)\s+(?:đi\s+với|di\s+voi|dùng\s+với|dung\s+voi|đi\s+với\s+giới\s+từ|di\s+voi\s+gioi\s+tu)",
        r"(?:sau|trước|truoc)\s+(.+?)\s+(?:dùng|dung|cần|can)",
        r"(?:dịch\s+từ|dich\s+tu|nghĩa\s+của|nghia\s+cua|từ|tu|cụm|cum|cấu\s+trúc|cau\s+truc)\s+(.+?)(?:\s+(?:là|la|nghĩa|nghia|đi|di|dùng|dung|$)|[?.!]|$)",
        r"(.+?)\s+(?:là\s+gì|la\s+gi|nghĩa\s+là\s+gì|nghia\s+la\s+gi|có\s+nghĩa\s+là\s+gì|co\s+nghia\s+la\s+gi|mean|means|meaning)",
        r"what\s+does\s+(.+?)\s+mean",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if not match:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        target = _clean_target_phrase(match.group(1))
        if _is_useful_target(target):
            return _restore_phrase_case(target, options or [], question_text or "")

    return None


def find_meaning_in_context(target: str | None, context: dict[str, Any]) -> AnswerMatch:
    term = _clean_target_phrase(target or "")
    if not term:
        return AnswerMatch()

    option = _find_option_for_term(context, term)
    option_label = str(option.get("label") or "").strip().upper() if option else None
    if option:
        term = _strip_answer_label(option.get("text")) or term

    sources = [
        ("OptionAnalysis", context.get("option_analysis")),
        ("VocabularyNotes", context.get("vocabulary_notes") or context.get("vocabulary")),
        ("ExplanationDetail", context.get("explanation_detail") or context.get("explanation")),
        ("RawBlock", context.get("raw_block")),
    ]
    sources = [(field, value) for field, value in sources if _compact(value)]
    for source_field, source_text in sources:
        parsed = _parse_meaning_from_text(source_text, term, option_label)
        if parsed.get("meaning"):
            answer = _format_meaning_answer(parsed.get("term") or term, parsed["meaning"], parsed.get("part_of_speech"))
            return AnswerMatch(answer, source_field, parsed.get("term") or term, option_label, parsed.get("snippet") or "")

    if option:
        translation = _clean_meaning(option.get("translation"))
        if translation:
            return AnswerMatch(_format_meaning_answer(term, translation, ""), "ToeicDocxOptions.TranslationVi", term, option_label, translation)

    return AnswerMatch()


def find_collocation_in_context(target: str | None, context: dict[str, Any]) -> AnswerMatch:
    term = _clean_target_phrase(target or "")
    if not term:
        return AnswerMatch()

    for source_field, source_text in _context_sources(context):
        text = _compact(source_text)
        if not text:
            continue

        structure = _extract_structure_for_target(term, text)
        if structure:
            prep = _extract_preposition(term, structure)
            meaning = _extract_meaning_near_structure(term, text, structure)
            if prep:
                display = _quote(_lower_first(term))
                answer = f"{display} đi với giới từ “{prep}”. Cấu trúc: {structure}."
                return AnswerMatch(answer, source_field, term, None, structure)
            if meaning:
                answer = f"{structure} nghĩa là “{_format_meaning_text(meaning)}”."
                return AnswerMatch(answer, source_field, term, None, structure)
            return AnswerMatch(f"Cấu trúc: {structure}.", source_field, term, None, structure)

        collocation_sentence = _find_sentence_with_target_and_keywords(text, term, ("cấu trúc", "cau truc", "giới từ", "gioi tu", "đi với", "di voi", "dùng với", "dung voi"))
        if collocation_sentence:
            return AnswerMatch(_ensure_sentence(collocation_sentence), source_field, term, None, collocation_sentence)

    return AnswerMatch()


def extract_gap_requirement(context: dict[str, Any]) -> AnswerMatch:
    source_text = context.get("explanation_detail") or context.get("explanation") or context.get("option_analysis") or context.get("raw_block")
    source_field = _field_for_context_value(context, source_text)
    sentences = _split_sentences(source_text)
    best_sentence = ""
    best_score = 0
    keywords = (
        "cho trong",
        "khoang trong",
        "o trong",
        "can",
        "dung truoc",
        "dung sau",
        "sau",
        "truoc",
        "bo nghia",
        "danh tu",
        "dong tu",
        "tinh tu",
        "trang tu",
        "v-ing",
        "v-ed",
        "v3",
        "to v",
        "bi dong",
    )
    for sentence in sentences:
        text = normalize_text(sentence)
        score = sum(1 for item in keywords if item in text)
        if "cho trong" in text or "khoang trong" in text or "o trong" in text:
            score += 4
        if "can" in text:
            score += 3
        if re.search(r"\([a-d]\)", text) or "dap an" in text:
            score -= 2
        if score > best_score:
            best_score = score
            best_sentence = sentence

    if not best_sentence:
        return AnswerMatch()
    answer = _format_gap_requirement(best_sentence)
    return AnswerMatch(answer, source_field or "ExplanationDetail", "", None, best_sentence)


def extract_option_reason(option_label: str | None, context: dict[str, Any]) -> AnswerMatch:
    if not option_label:
        return AnswerMatch()
    label = option_label.upper()
    for source_field, source_text in [
        ("OptionAnalysis", context.get("option_analysis")),
        ("RawBlock", context.get("raw_block")),
    ]:
        entry = _parse_option_entry(source_text, label)
        if entry:
            term = entry.get("term") or _option_text(label, context)
            body = entry.get("body") or ""
            return AnswerMatch(_format_option_reason(label, term, body, context), source_field, term, label, body)

    option = _find_option_by_label(context, label)
    if option:
        is_correct = option.get("is_correct") is True
        explanation = extract_gap_requirement(context).text or _first_sentence(context.get("explanation_detail") or context.get("explanation"))
        verdict = "đúng" if is_correct else "sai"
        if explanation:
            return AnswerMatch(f"{label} {verdict} dựa trên dữ liệu câu: {explanation}", "ExplanationDetail", _strip_answer_label(option.get("text")), label, explanation)
        return AnswerMatch(f"{label} {verdict} theo dữ liệu đáp án hiện có.", "ToeicDocxOptions.IsCorrect", _strip_answer_label(option.get("text")), label, "")

    return AnswerMatch()


def extract_option_reason_by_message(message: str, context: dict[str, Any]) -> AnswerMatch:
    explicit_label = extract_option_label(message)
    label = explicit_label or _option_label_for_message_target(message, context)
    if label:
        match = extract_option_reason(label, context)
        if match.text and not explicit_label and match.target:
            term = _strip_answer_label(match.target)
            match.text = re.sub(
                rf"^{re.escape(label)}\s+(sai|đúng|dung)\s+vì\s+“?{re.escape(term)}”?\s*",
                lambda found: f"{_quote(term)} {found.group(1)} vì ",
                match.text,
                flags=re.IGNORECASE,
            )
        return match
    return AnswerMatch()


def extract_translation(context: dict[str, Any]) -> AnswerMatch:
    for key, field in [
        ("final_translation_vi", "FinalTranslationVi"),
        ("translation_vi", "TranslationVi"),
        ("translation", "TranslationVi"),
    ]:
        value = _compact(context.get(key))
        if value:
            return AnswerMatch(_ensure_sentence(value), field, "", None, value)

    raw = str(context.get("raw_block") or "")
    match = re.search(r"(?:Bản dịch tiếng Việt|Ban dich tieng Viet|Dịch|Dich)\s*[:：]\s*(?P<value>.+?)(?:\n\s*\n|$)", raw, flags=re.IGNORECASE | re.DOTALL)
    if match:
        value = _compact(match.group("value"))
        return AnswerMatch(_ensure_sentence(value), "RawBlock", "", None, value[:240])
    return AnswerMatch()


def extract_hint(context: dict[str, Any]) -> AnswerMatch:
    gap = extract_gap_requirement(context)
    if not gap.text:
        return AnswerMatch()
    answer = gap.text
    answer = re.sub(r"(?i)^Khoảng trống cần\s+", "Hãy nhìn vị trí chỗ trống: cần ", answer)
    answer = re.sub(r"(?i)^Câu cần\s+", "Hãy chú ý cấu trúc câu: cần ", answer)
    answer = _remove_answer_leaks(answer, context)
    return AnswerMatch(_ensure_sentence(answer), gap.source_field, gap.target, gap.option_label, gap.snippet)


def extract_grammar_structure(context: dict[str, Any]) -> AnswerMatch:
    for source_field, source_text in [
        ("ExplanationDetail", context.get("explanation_detail") or context.get("explanation")),
        ("VocabularyNotes", context.get("vocabulary_notes") or context.get("vocabulary")),
        ("OptionAnalysis", context.get("option_analysis")),
        ("RawBlock", context.get("raw_block")),
    ]:
        sentence = _best_sentence_for_keywords(
            source_text,
            ("cấu trúc", "cau truc", "ngữ pháp", "ngu phap", "bị động", "bi dong", "v-ing", "v-ed", "trạng từ", "trang tu", "tính từ", "tinh tu", "danh từ", "danh tu", "động từ", "dong tu"),
        )
        if sentence:
            return AnswerMatch(_ensure_sentence(sentence), source_field, "", None, sentence)
    return extract_gap_requirement(context)


def answer_target_completion(target: str | None, context: dict[str, Any], message: str) -> AnswerMatch:
    term = _clean_target_phrase(target or "")
    normalized_message = normalize_text(message)
    if not _is_useful_target(term):
        return AnswerMatch()

    relation = _target_blank_relation(term, context)
    completion = _correct_completion_text(context)
    correct_label = str(context.get("correct_option_label") or context.get("correct_option_key") or "").strip().upper()
    option_entry = _parse_option_entry(context.get("option_analysis"), correct_label) if correct_label else {}
    explanation_sentence = _completion_explanation_sentence(term, completion, context)
    target_near_blank = bool(relation)

    if not relation and completion and normalize_text(term) == normalize_text(completion):
        reverse = _answer_completion_neighbor_request(term, context, normalized_message)
        if reverse.text:
            return reverse

    if relation and completion:
        phrase = f"{term} {completion}" if relation == "target_before_blank" else f"{completion} {term}"
        source = "CorrectAnswerText"
        snippet = phrase
        if option_entry:
            source = "OptionAnalysis"
            snippet = option_entry.get("body") or snippet
        elif explanation_sentence:
            source = "ExplanationDetail"
            snippet = explanation_sentence

        if _is_after_target_need_request(normalized_message) and relation == "target_before_blank":
            needed = _extract_needed_after_target(term, explanation_sentence) or _extract_needed_after_target(
                term, context.get("explanation_detail") or context.get("explanation") or context.get("raw_block")
            )
            answer = (
                f"Sau {_quote(_lower_first(term))} cần {needed}. Trong câu này là {_quote(completion)}."
                if needed
                else f"Sau {_quote(_lower_first(term))} là {_quote(completion)} trong câu này."
            )
            return AnswerMatch(answer, source, term, correct_label or None, snippet, True, completion)

        if _is_before_target_need_request(normalized_message) and relation == "blank_before_target":
            needed = _extract_needed_before_target(term, explanation_sentence) or _extract_needed_before_target(
                term, context.get("explanation_detail") or context.get("explanation") or context.get("raw_block")
            )
            answer = (
                f"Trước {_quote(_lower_first(term))} cần {needed}."
                if needed
                else f"Trước {_quote(_lower_first(term))} là {_quote(completion)} trong câu này."
            )
            return AnswerMatch(answer, source, term, correct_label or None, snippet, True, completion)

        if _is_preposition_request(normalized_message):
            preposition = _extract_preposition(term, phrase)
            if preposition:
                structure = _structure_from_explanation(term, completion, context) or phrase
                return AnswerMatch(
                    f"{_quote(_lower_first(term))} đi với giới từ “{preposition}”. Cấu trúc: {structure}.",
                    source,
                    term,
                    correct_label or None,
                    snippet,
                    True,
                    completion,
                )

        reason = _completion_reason(completion, option_entry, explanation_sentence)
        if _asks_for_noun_phrase(normalized_message):
            answer = f"{_quote(_lower_first(term))} đi với {_quote(completion)} để tạo cụm danh từ {_quote(phrase)}."
            if reason:
                answer += f"\n{reason}"
        else:
            answer = f"{_quote(_lower_first(term))} đi với {_quote(completion)}: {phrase}."
        return AnswerMatch(answer, source, term, correct_label or None, snippet, True, completion)

    if term:
        formula = _find_formula_structure_for_target(term, context, prefer_preposition=_is_preposition_request(normalized_message))
        if formula.text:
            return formula

    return AnswerMatch()


def answer_collocation_preposition_request(target: str | None, context: dict[str, Any], message: str) -> AnswerMatch:
    normalized_message = normalize_text(message)
    term = _clean_target_phrase(target or "")
    completion = _correct_completion_text(context)

    if not _is_useful_target(term):
        term = _infer_collocation_target_from_blank(context, completion)

    if _is_blank_preposition_request(normalized_message):
        structure = _find_structure_for_completion_and_target(term, completion, context)
        if completion:
            if structure:
                answer = f"Khoảng trống nên dùng giới từ {_quote(completion)}.\nCấu trúc: {structure}."
            else:
                answer = f"Khoảng trống nên dùng giới từ {_quote(completion)}."
            return AnswerMatch(answer, "CorrectAnswerText", term, None, structure or completion, bool(term), completion)

    if _is_useful_target(term):
        structure_match = _find_formula_structure_for_target(term, context, prefer_preposition=_is_preposition_request(normalized_message))
        if structure_match.text:
            structure = _clean_structure(structure_match.snippet or structure_match.text.replace("Cấu trúc:", ""))
            if not structure:
                structure = _extract_structure_for_target(term, structure_match.text)
            structure = _localize_structure_terms(structure)
            completion_text = _completion_after_target(term, structure)
            if completion_text and not _is_preposition_word(completion_text):
                return AnswerMatch(
                    f"{_quote(_lower_first(term))} đi với {_quote(completion_text)}.\nCấu trúc: {structure}.",
                    structure_match.source_field,
                    term,
                    None,
                    structure,
                    False,
                    completion_text,
                )
            if _is_preposition_request(normalized_message):
                preposition = _extract_preposition(term, structure)
                if preposition:
                    return AnswerMatch(
                        f"{_quote(_lower_first(term))} đi với giới từ {_quote(preposition)}.\nCấu trúc: {structure}.",
                        structure_match.source_field,
                        term,
                        None,
                        structure,
                        False,
                        preposition,
                    )
            if completion_text:
                return AnswerMatch(
                    f"{_quote(_lower_first(term))} đi với {_quote(completion_text)}.\nCấu trúc: {structure}.",
                    structure_match.source_field,
                    term,
                    None,
                    structure,
                    False,
                    completion_text,
                )
            return structure_match

        relation = _target_blank_relation(term, context)
        if relation and completion:
            phrase = f"{term} {completion}" if relation == "target_before_blank" else f"{completion} {term}"
            structure = _find_structure_for_completion_and_target(term, completion, context) or phrase
            if _is_preposition_word(completion) and _is_preposition_request(normalized_message):
                answer = f"{_quote(_lower_first(term))} đi với giới từ {_quote(completion)}.\nCấu trúc: {structure}."
            else:
                answer = f"{_quote(_lower_first(term))} đi với {_quote(completion)}.\nCấu trúc: {structure}."
            return AnswerMatch(answer, "CorrectAnswerText", term, None, structure, True, completion)

    return answer_target_completion(term, context, message)


def answer_relative_pronoun_request(target: str | None, context: dict[str, Any], message: str) -> AnswerMatch:
    term = _clean_target_phrase(target or "") or _infer_relative_pronoun_antecedent(context)
    answer = _correct_completion_text(context)
    if not answer:
        return AnswerMatch()

    for source_field, source_text in [
        ("ExplanationDetail", context.get("explanation_detail") or context.get("explanation")),
        ("OptionAnalysis", context.get("option_analysis")),
        ("VocabularyNotes", context.get("vocabulary_notes") or context.get("vocabulary")),
        ("RawBlock", context.get("raw_block")),
    ]:
        sentence = _relative_pronoun_sentence(source_text, term, answer)
        if sentence:
            role = _extract_relative_pronoun_role(sentence, context)
            display_term = term or _infer_relative_pronoun_antecedent(context)
            if display_term and role:
                text = f"Đại từ quan hệ thay thế cho {_quote(display_term)} là {_quote(answer)}, vì nó {role}."
            elif display_term:
                text = f"Đại từ quan hệ thay thế cho {_quote(display_term)} là {_quote(answer)}."
            else:
                text = f"Đại từ quan hệ cần dùng là {_quote(answer)}."
            return AnswerMatch(text, source_field, display_term, None, sentence, True, answer)

    display_term = term or _infer_relative_pronoun_antecedent(context)
    if display_term:
        return AnswerMatch(
            f"Đại từ quan hệ thay thế cho {_quote(display_term)} là {_quote(answer)}.",
            "CorrectAnswerText",
            display_term,
            None,
            answer,
            True,
            answer,
        )
    return AnswerMatch(f"Đại từ quan hệ cần dùng là {_quote(answer)}.", "CorrectAnswerText", "", None, answer, True, answer)


def find_grammar_formula_answer(target: str | None, question_context: dict[str, Any], message: str) -> AnswerMatch:
    context = question_context or {}
    normalized_message = normalize_text(message)
    term = _clean_target_phrase(target or "")

    completion = answer_target_completion(term, context, message)
    if completion.text:
        return completion

    if _is_gap_formula_request(normalized_message):
        gap = extract_gap_requirement(context)
        if gap.text:
            return gap

    if not _is_useful_target(term):
        general = _find_general_formula_answer(context, normalized_message)
        if general.text:
            return general
        term = _infer_formula_target(context)

    if term and _is_part_of_speech_request(normalized_message):
        part_of_speech = _find_part_of_speech_for_target(term, context)
        if part_of_speech.text:
            return part_of_speech

    if term:
        formula = _find_formula_structure_for_target(
            term,
            context,
            prefer_preposition=_is_preposition_request(normalized_message),
        )
        if formula.text:
            return formula

        part_of_speech = _find_part_of_speech_for_target(term, context)
        if part_of_speech.text and _is_part_of_speech_request(normalized_message):
            return part_of_speech

    general = _find_general_formula_answer(context, normalized_message)
    if general.text and not term:
        return general

    return AnswerMatch()


def build_local_answer(message: str, question_context: dict[str, Any]) -> tuple[str, LocalIntent]:
    match, intent = build_local_answer_with_debug(message, question_context)
    return match.text or NO_MATCH_REPLY, intent


def build_local_answer_with_debug(message: str, question_context: dict[str, Any]) -> tuple[AnswerMatch, LocalIntent]:
    context = question_context or {}
    intent = detect_intent(message)
    if not _has_question_data(context):
        return AnswerMatch(NO_MATCH_REPLY), intent

    options = _get_options(context)
    question_text = str(context.get("question_text_en") or context.get("question_text") or "")
    target = extract_word_or_phrase(message, options, question_text)
    option_label = extract_option_label(message)
    match = answer_priority_intent_question(message, context, target, option_label)
    if match.text:
        if not match.target and target:
            match.target = target
        if not match.option_label and option_label:
            match.option_label = option_label
        match.text = clean_response(match.text)
        return match, intent

    match = answer_option_or_source_specific_question(message, context, target, option_label)
    if match.text:
        if not match.target and target:
            match.target = target
        if not match.option_label and option_label:
            match.option_label = option_label
        match.text = clean_response(match.text)
        return match, intent

    if intent == "word_meaning":
        if option_label and _has_any(normalize_text(message), "la gi", "nghia", "dich", "mean"):
            target = _option_text(option_label, context)
        match = find_meaning_in_context(target, context)
        if not match.text and target:
            match = find_collocation_in_context(target, context)
    elif intent == "collocation_preposition":
        match = find_collocation_in_context(target, context)
        if not match.text:
            match = find_meaning_in_context(target, context)
    elif intent == "gap_requirement":
        match = extract_gap_requirement(context)
    elif intent == "correct_answer":
        match = _format_correct_answer(context)
    elif intent == "option_reason":
        match = extract_option_reason_by_message(message, context)
    elif intent == "full_option_analysis":
        match = _format_full_option_analysis(context)
    elif intent == "translation":
        match = extract_translation(context)
    elif intent == "explanation":
        match = _format_explanation(context)
    elif intent == "hint":
        match = extract_hint(context)
    elif intent == "grammar_structure":
        match = extract_grammar_structure(context)
    elif intent == "grammar_formula_request":
        match = find_grammar_formula_answer(target, context, message)
    elif intent == "target_completion_request":
        match = answer_target_completion(target, context, message)
    elif intent == "grammar_structure_definition":
        match = answer_grammar_structure_definition(message, context)
    elif intent == "collocation_preposition_request":
        match = answer_collocation_preposition_request(target, context, message)
    elif intent == "relative_pronoun_request":
        match = answer_relative_pronoun_request(target, context, message)
    else:
        match = extract_gap_requirement(context)
        if not match.text:
            match = _format_explanation(context)

    if not match.text:
        if intent == "grammar_structure_definition":
            reply = GRAMMAR_STRUCTURE_NO_MATCH_REPLY
        elif intent in {"grammar_formula_request", "target_completion_request"}:
            reply = GRAMMAR_FORMULA_NO_MATCH_REPLY
        else:
            reply = NO_MATCH_REPLY
        match = AnswerMatch(reply, "", target or "", option_label, "")
    if not match.target and target:
        match.target = target
    if not match.option_label and option_label:
        match.option_label = option_label
    match.text = clean_response(match.text)
    return match, intent


class LocalAlgorithmProvider:
    async def generate(
        self, intent_result: IntentResult, context: ChatContextBundle, user_message: str
    ) -> ProviderResult:
        try:
            question_context = context.raw or {}
            match, _ = build_local_answer_with_debug(user_message, question_context)
            return ProviderResult(status_code=200, reply=match.text or NO_MATCH_REPLY)
        except Exception as exc:
            logger.exception("LocalAlgorithmProvider failed: %s", exc)
            return ProviderResult(
                status_code=500,
                reply="Hệ thống chat nội bộ gặp sự cố khi xử lý dữ liệu câu hỏi.",
                raw_error=str(exc),
            )


def _has_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _has_question_data(context: dict[str, Any]) -> bool:
    return any(
        context.get(key)
        for key in (
            "question_id",
            "question_text",
            "question_text_en",
            "options",
            "correct_answer",
            "correct_answer_text",
            "explanation",
            "explanation_detail",
            "option_analysis",
            "vocabulary_notes",
            "raw_block",
        )
    )


def _get_options(context: dict[str, Any]) -> list[dict[str, Any]]:
    return [option for option in context.get("options") or [] if isinstance(option, dict)]


def _context_sources(context: dict[str, Any], include_translation: bool = False) -> list[tuple[str, Any]]:
    sources = [
        ("VocabularyNotes", context.get("vocabulary_notes") or context.get("vocabulary")),
        ("ExplanationDetail", context.get("explanation_detail") or context.get("explanation")),
        ("OptionAnalysis", context.get("option_analysis")),
    ]
    if include_translation:
        sources.extend(
            [
                ("FinalTranslationVi", context.get("final_translation_vi")),
                ("TranslationVi", context.get("translation_vi") or context.get("translation")),
            ]
        )
    sources.append(("RawBlock", context.get("raw_block")))
    return [(field, value) for field, value in sources if _compact(value)]


OPTION_ENTRY_MARKER_RE = re.compile(
    r"(?:\(\s*(?P<label_paren>[A-D])\s*\)|\b(?P<label_plain>[A-D])\s*[.)-])\s*(?P<body>.*?)(?=(?:\(\s*[A-D]\s*\)|\b[A-D]\s*[.)-])\s*|$)",
    flags=re.IGNORECASE | re.DOTALL,
)

OPTION_STATUS_RE = re.compile(
    r"\b(?:Sai|Wrong|Correct|(?:\u0110|D)úng|(?:\u0110|D)áp\s+án\s+(?:\u0111úng|dung)|Là\s+(?:danh|tính|\u0111ộng|trạng|dong|tinh|trang)|Nghĩa\s+là|Nghia\s+la)\b",
    flags=re.IGNORECASE,
)

OPTION_REQUEST_STOPWORDS = {
    "anh",
    "cau",
    "chon",
    "cho",
    "context",
    "cua",
    "dung",
    "for",
    "from",
    "giai",
    "gi",
    "giai thich",
    "have",
    "khong",
    "la",
    "loai",
    "mot",
    "nghia",
    "nay",
    "sao",
    "tai",
    "the",
    "to",
    "tu",
    "with",
    "vi",
    "why",
}


def answer_priority_intent_question(
    message: str,
    context: dict[str, Any],
    target: str | None = None,
    option_label: str | None = None,
) -> AnswerMatch:
    normalized_message = normalize_text(message)
    entries = _option_entries_from_context(context)

    if _is_preposition_question(normalized_message):
        match = _answer_preposition_question(normalized_message, context)
        if match.text:
            return match

    if _is_evidence_request(normalized_message):
        match = _answer_evidence_request(normalized_message, context, entries, option_label)
        if match.text:
            return match

    if _is_compare_request(normalized_message):
        match = _answer_compare_request(normalized_message, context, entries)
        if match.text:
            return match

    if _is_structure_question(normalized_message):
        match = _answer_structure_question(normalized_message, message, context, entries)
        if match.text:
            return match

    if _is_part_of_speech_question(normalized_message):
        label = option_label or _option_label_for_message_or_target(message, context, entries, target)
        if label and label in entries:
            return _format_option_part_of_speech_answer(label, entries[label], context, include_correct=False)

    if _is_meaning_question(normalized_message) and not _is_option_reason_or_answer_request(normalized_message):
        match = _answer_meaning_question(normalized_message, message, context, entries, target, option_label)
        if match.text:
            return match

    if _is_example_request(normalized_message):
        match = _answer_example_request(normalized_message, context)
        if match.text:
            return match

    return AnswerMatch()


def _is_compare_request(normalized_message: str) -> bool:
    return bool(
        " vs " in f" {normalized_message} "
        or " khac " in f" {normalized_message} "
        or " khac gi" in normalized_message
        or "va" in normalized_message and "khac" in normalized_message
    )


def _is_preposition_question(normalized_message: str) -> bool:
    return bool(
        "gioi tu" in normalized_message
        or "di voi gi" in normalized_message
        or "di voi tu gi" in normalized_message
        or "dung voi gi" in normalized_message
        or re.search(r"\bsau\s+[a-z][a-z'-]*\s+(?:di voi|dung voi|dung gioi tu)", normalized_message)
    )


def _is_evidence_request(normalized_message: str) -> bool:
    return _has_any(
        normalized_message,
        "chung minh",
        "bang chung",
        "cau nao",
        "doan nao",
        "chi tiet nao",
        "evidence",
        "where",
    ) and (
        _has_any(normalized_message, "dap an", "chon", "answer")
        or extract_option_label(normalized_message) is not None
    )


def _answer_evidence_request(
    normalized_message: str,
    context: dict[str, Any],
    entries: dict[str, dict[str, Any]],
    option_label: str | None,
) -> AnswerMatch:
    label = option_label or extract_option_label(normalized_message) or str(context.get("correct_option_key") or context.get("correct_option_label") or "").strip().upper()
    if label not in {"A", "B", "C", "D"}:
        return AnswerMatch()

    entry = entries.get(label, {})
    option_text = str(entry.get("text") or _option_text(label, context) or "").strip()
    sources = [
        ("Passage", context.get("passage_text") or _passage_text_from_context(context)),
        ("RawBlock", context.get("raw_block")),
        ("ExplanationDetail", context.get("explanation_detail") or context.get("explanation")),
        ("OptionAnalysis", entry.get("analysis")),
    ]
    keywords = _evidence_keywords(option_text)

    for source_field, source_text in sources:
        snippet = _find_evidence_snippet(source_text, keywords)
        if snippet:
            return AnswerMatch(
                f"Chi tiết chứng minh là: “{snippet}”. Chi tiết này hỗ trợ lựa chọn {label}.",
                source_field,
                option_text,
                label,
                snippet,
            )

    if option_text:
        return AnswerMatch(
            f"Mình chưa thấy câu trích dẫn riêng cho {label}, nhưng lựa chọn này liên quan đến ý “{option_text}”.",
            "Options",
            option_text,
            label,
            option_text,
        )
    return AnswerMatch()


def _passage_text_from_context(context: dict[str, Any]) -> str:
    passage = context.get("passage")
    if isinstance(passage, dict):
        return str(passage.get("text") or passage.get("passageText") or passage.get("passage_text") or "")
    return ""


def _evidence_keywords(option_text: str) -> list[str]:
    normalized = normalize_text(option_text)
    tokens = [token for token in re.findall(r"[a-z0-9][a-z0-9'-]*", normalized) if len(token) > 3 and token not in OPTION_REQUEST_STOPWORDS]
    expanded = set(tokens)
    if "payment" in expanded or "pay" in expanded:
        expanded.update({"pay", "payment", "balance", "paid"})
    if "request" in expanded:
        expanded.update({"request", "must", "need", "required"})
    if "reservation" in expanded:
        expanded.update({"reservation", "confirm", "booking"})
    return list(expanded)


def _find_evidence_snippet(source_text: Any, keywords: list[str]) -> str:
    text = _compact(source_text)
    if not text:
        return ""

    quoted = re.findall(r"[“\"']([^“”\"']{12,260})[”\"']", text)
    candidates = quoted or _split_sentences(text)
    best = ""
    best_score = 0
    for candidate in candidates:
        normalized = normalize_text(candidate)
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score > best_score:
            best_score = score
            best = candidate
    if best and (best_score > 0 or not keywords):
        return _compact(best)[:260]
    return ""


def _answer_preposition_question(normalized_message: str, context: dict[str, Any]) -> AnswerMatch:
    target = _extract_preposition_target(normalized_message, context)
    if not target:
        return AnswerMatch()
    preposition, structure, source_field = _find_preposition_structure(target, context)
    if not preposition:
        return AnswerMatch()

    structure = structure or f"{target} {preposition} + noun"
    display_structure = re.sub(
        r"\+\s*(?:rules/regulations|rules|regulations|regulation)\b.*$",
        "+ noun",
        structure,
        flags=re.IGNORECASE,
    )
    example = _preposition_example(target, preposition, context)
    lines = [
        f"{target} đi với {preposition}.",
        f"Cấu trúc: {display_structure}.",
    ]
    if example:
        lines.append(f"Ví dụ: {example}.")
    return AnswerMatch("\n".join(lines), source_field or "VocabularyNotes/QuestionText", target, None, display_structure)


def _extract_preposition_target(normalized_message: str, context: dict[str, Any]) -> str:
    answer = _strip_answer_label(context.get("correct_answer_text") or context.get("correct_answer") or "")
    if answer and _has_any(
        normalized_message,
        "sau tu nay",
        "tu nay di voi",
        "tu nay dung",
        "di voi gioi tu gi",
        "dung gioi tu gi",
    ):
        return answer

    patterns = [
        r"\bsau\s+(?P<target>[a-z][a-z'-]*)\s+(?:di voi|dung voi|dung gioi tu|can gioi tu)",
        r"\b(?P<target>[a-z][a-z'-]*)\s+(?:di voi|dung voi)\s+(?:gioi tu\s+)?(?:gi|nao)",
        r"\b(?P<target>[a-z][a-z'-]*)\s+\w*\s*(?:gioi tu)\s+(?:gi|nao)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_message)
        if match:
            target = match.group("target")
            if target not in OPTION_REQUEST_STOPWORDS:
                return _restore_target_from_context(target, context)
    return ""


def _restore_target_from_context(normalized_target: str, context: dict[str, Any]) -> str:
    for option in _get_options(context):
        text = _strip_answer_label(option.get("text"))
        if normalize_text(text) == normalized_target:
            return text
    answer = _strip_answer_label(context.get("correct_answer_text") or context.get("correct_answer") or "")
    if normalize_text(answer) == normalized_target:
        return answer
    return normalized_target


def _find_preposition_structure(target: str, context: dict[str, Any]) -> tuple[str, str, str]:
    target_norm = normalize_text(target)
    prep_union = "|".join(PREPOSITIONS)
    for source_field, source_text in _context_sources(context):
        text = _compact(source_text)
        normalized = normalize_text(text)
        if target_norm not in normalized:
            continue
        pattern = rf"\b{re.escape(target)}\s+(?P<prep>{prep_union})\b(?:\s*\+\s*(?P<object>[^.。;\n:：]+))?"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            prep = match.group("prep").lower()
            obj = _clean_structure(match.groupdict().get("object") or "noun")
            structure = f"{target} {prep} + {obj}"
            return prep, structure, source_field

        pattern_norm = rf"\b{re.escape(target_norm)}\s+(?P<prep>{prep_union})\b(?:\s*\+\s*(?P<object>[^.;:]+))?"
        match = re.search(pattern_norm, normalized, flags=re.IGNORECASE)
        if match:
            prep = match.group("prep").lower()
            obj = _clean_structure(match.groupdict().get("object") or "noun")
            return prep, f"{target} {prep} + {obj}", source_field

    question = str(context.get("question_text") or context.get("question_text_en") or "")
    after_blank = re.search(r"_{2,}\s+(?P<prep>" + prep_union + r")\b\s*(?P<object>(?:the\s+)?[A-Za-z][A-Za-z' -]*)?", question, flags=re.IGNORECASE)
    if after_blank:
        prep = after_blank.group("prep").lower()
        obj_text = after_blank.group("object") or ""
        obj = "noun"
        if obj_text:
            first_words = " ".join(re.findall(r"[A-Za-z][A-Za-z'-]*", obj_text)[:3])
            if first_words:
                obj = "noun"
        return prep, f"{target} {prep} + {obj}", "QuestionText"
    return "", "", ""


def _preposition_example(target: str, preposition: str, context: dict[str, Any]) -> str:
    question = str(context.get("question_text") or context.get("question_text_en") or "")
    match = re.search(r"_{2,}\s+" + re.escape(preposition) + r"\s+(?P<object>(?:the\s+)?[A-Za-z][A-Za-z' -]*)", question, flags=re.IGNORECASE)
    if match:
        words = re.findall(r"[A-Za-z][A-Za-z'-]*", match.group("object"))
        if words:
            limit = 2 if normalize_text(words[0]) in {"the", "a", "an"} else 2
            return f"{target} {preposition} {' '.join(words[:limit])}"
    if normalize_text(target) == "comply" and preposition == "with":
        return "comply with the regulations"
    return f"{target} {preposition} the rules"


def _answer_compare_request(
    normalized_message: str,
    context: dict[str, Any],
    entries: dict[str, dict[str, Any]],
) -> AnswerMatch:
    if "during" in normalized_message and "while" in normalized_message:
        return AnswerMatch(
            "During + noun/noun phrase: trong suốt/trong khi diễn ra việc gì.\n"
            "While + clause S + V: trong khi ai đó làm gì.\n"
            "Ví dụ: During the meeting / While we were meeting.",
            "fallback_grammar_rule",
            "during/while",
            None,
            "during vs while",
        )
    if "rough" in normalized_message and "roughly" in normalized_message:
        return AnswerMatch(
            "Rough là tính từ, nghĩa là thô/không bằng phẳng hoặc xấp xỉ tùy ngữ cảnh.\n"
            "Roughly là trạng từ, thường nghĩa là khoảng/xấp xỉ khi đứng trước số lượng.",
            "fallback_grammar_rule",
            "rough/roughly",
            None,
            "rough vs roughly",
        )

    labels = [
        label
        for label, entry in entries.items()
        if normalize_text(entry.get("text")) and re.search(rf"\b{re.escape(normalize_text(entry.get('text')))}\b", normalized_message)
    ]
    if len(labels) >= 2:
        lines = []
        for label in labels[:2]:
            entry = entries[label]
            analysis = _clean_option_analysis_for_display(entry.get("analysis"))
            if analysis:
                lines.append(f"{entry.get('text')}: {analysis}")
        if lines:
            return AnswerMatch("\n".join(lines), "OptionAnalysis", "", None, "\n".join(lines))
    return AnswerMatch()


def _is_structure_question(normalized_message: str) -> bool:
    return bool(
        _has_any(normalized_message, "sau ", "truoc ", "di voi", "dung voi", "dung gi", "dung sao", "dung nhu the nao", "cau truc", "cong thuc")
        or "+" in normalized_message
        or _is_relative_that_question(normalized_message)
    )


def _answer_structure_question(
    normalized_message: str,
    message: str,
    context: dict[str, Any],
    entries: dict[str, dict[str, Any]],
) -> AnswerMatch:
    if _is_relative_that_question(normalized_message):
        return _answer_that_relative_function(context)

    if "during" in normalized_message:
        return AnswerMatch(
            "Sau during dùng danh từ hoặc cụm danh từ. Ví dụ: during the meeting, during the election.",
            "fallback_grammar_rule",
            "during",
            None,
            "during + noun/noun phrase",
        )

    if "roughly" in normalized_message and ("number" in normalized_message or "so" in normalized_message or "+" in normalized_message or "vi du" in normalized_message):
        return AnswerMatch(
            "Roughly + number nghĩa là khoảng/xấp xỉ.\nVí dụ: Roughly 200 people attended the event.",
            "fallback_grammar_rule",
            "roughly + number",
            None,
            "roughly + number",
        )

    if "plan on" in normalized_message:
        completion = _completion_mentioned_in_message(normalized_message, context)
        if completion:
            return AnswerMatch(
                f"Sau plan on dùng V-ing. Vì vậy cần “{completion}”. Cấu trúc: plan on + V-ing = dự định làm gì.",
                "fallback_grammar_rule",
                "plan on",
                None,
                "plan on + V-ing",
            )
        return AnswerMatch(
            "Sau plan on dùng V-ing. Cấu trúc: plan on + V-ing = dự định làm gì.\nVí dụ: We plan on expanding next year.",
            "fallback_grammar_rule",
            "plan on",
            None,
            "plan on + V-ing",
        )

    if "preference" in normalized_message and ("for" in normalized_message or "preference for" in normalized_message):
        if "clear" in normalized_message:
            return AnswerMatch(
                "have a clear preference for nghĩa là có sự ưu tiên/ưa thích rõ ràng đối với ai hoặc điều gì.",
                "fallback_grammar_rule",
                "have a clear preference for",
                None,
                "have a clear preference for",
            )
        return AnswerMatch(
            "have a preference for + noun nghĩa là có sự ưu tiên/ưa thích đối với ai hoặc điều gì.",
            "fallback_grammar_rule",
            "have a preference for",
            None,
            "have a preference for + noun",
        )

    phrase = _answer_source_phrase_message(message, context, entries, include_correct=False)
    if phrase.text:
        return phrase

    target_match = re.search(r"\bsau\s+([a-z][a-z'-]*)", normalized_message)
    if target_match:
        target = target_match.group(1)
        sentence = _best_sentence_for_term_and_keywords(
            target,
            context,
            ("can", "danh tu", "tinh tu", "dong tu", "trang tu", "phu hop"),
        )
        if sentence:
            return AnswerMatch(_ensure_sentence(sentence), "ExplanationDetail/OptionAnalysis", target, None, sentence)
    return AnswerMatch()


def _is_relative_that_question(normalized_message: str) -> bool:
    return "that" in normalized_message and _has_any(normalized_message, "chuc nang", "trong cau", "thay cho", "lam gi", "vai tro")


def _answer_that_relative_function(context: dict[str, Any]) -> AnswerMatch:
    question = str(context.get("question_text") or context.get("question_text_en") or "")
    antecedent = _infer_relative_pronoun_antecedent(context) or "danh từ đứng trước nó"
    clause = ""
    match = re.search(r"_{2,}\s+([^,.]+)", question)
    if match:
        clause_body = match.group(1).strip()
        clause_body = re.split(r"\s+(?:is|are|was|were)\s+", clause_body, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        clause = f"that {clause_body}"
    role = "làm chủ ngữ"
    if clause and re.match(r"that\s+[A-Za-z][A-Za-z'-]*s?\b", clause):
        role = "làm chủ ngữ"
    if antecedent:
        if clause:
            text = f"That là đại từ quan hệ, thay cho “{antecedent}” và {role} của mệnh đề quan hệ “{clause}...” ."
        else:
            text = f"That là đại từ quan hệ, thay cho “{antecedent}” và {role} trong mệnh đề quan hệ."
    else:
        text = "That là đại từ quan hệ, thay cho danh từ đứng trước nó và làm chủ ngữ/tân ngữ trong mệnh đề quan hệ."
    return AnswerMatch(text.replace("...” .", "...”."), "fallback_grammar_rule", "that", None, question)


def _answer_meaning_question(
    normalized_message: str,
    message: str,
    context: dict[str, Any],
    entries: dict[str, dict[str, Any]],
    target: str | None,
    option_label: str | None,
) -> AnswerMatch:
    meaning_target = _meaning_target_from_message(normalized_message, context, target, option_label)
    if meaning_target:
        lookup_target = _base_preposition_target(meaning_target)
        preposition, structure, source_field = _find_preposition_structure(lookup_target, context)
        meaning = _find_term_meaning_near_structure(meaning_target, context) or _find_term_meaning_near_structure(lookup_target, context)
        if meaning and preposition and structure:
            return AnswerMatch(
                f"{meaning_target} nghĩa là {meaning}. Cụm thường dùng: {structure}.",
                source_field or "VocabularyNotes",
                meaning_target,
                option_label,
                structure,
            )

    if "roughly" in normalized_message:
        return AnswerMatch(
            "Roughly nghĩa là khoảng/xấp xỉ, thường đứng trước số lượng. Ví dụ: roughly fifteen customers.",
            "fallback_grammar_rule",
            "roughly",
            None,
            "roughly + number",
        )
    if "preference" in normalized_message and "for" in normalized_message:
        if "clear" in normalized_message:
            return AnswerMatch(
                "have a clear preference for nghĩa là có sự ưu tiên/ưa thích rõ ràng đối với ai hoặc điều gì.",
                "fallback_grammar_rule",
                "have a clear preference for",
                None,
                "have a clear preference for",
            )
        return AnswerMatch(
            "have a preference for + noun nghĩa là có sự ưu tiên/ưa thích đối với ai hoặc điều gì.",
            "fallback_grammar_rule",
            "have a preference for",
            None,
            "have a preference for + noun",
        )

    phrase = _answer_source_phrase_message(message, context, entries, include_correct=False)
    if phrase.text:
        return phrase

    label = option_label or _option_label_for_message_or_target(message, context, entries, target)
    if label and label in entries:
        return _format_option_meaning_answer(label, entries[label], context, include_correct=False)
    return AnswerMatch()


def _meaning_target_from_message(
    normalized_message: str,
    context: dict[str, Any],
    target: str | None,
    option_label: str | None,
) -> str:
    if target and normalize_text(target) not in GENERIC_TARGETS:
        return _restore_target_from_context(normalize_text(target), context)
    if option_label:
        return _option_text(option_label, context)
    patterns = [
        r"\b(?P<target>[a-z][a-z'-]*)\s+(?:nghia|la gi|mean)",
        r"\b(?:nghia cua|tu)\s+(?P<target>[a-z][a-z'-]*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_message)
        if match and match.group("target") not in OPTION_REQUEST_STOPWORDS:
            return _restore_target_from_context(match.group("target"), context)
    return ""


def _base_preposition_target(target: str) -> str:
    tokens = normalize_text(target).split()
    if len(tokens) >= 2 and tokens[1] in PREPOSITIONS:
        return tokens[0]
    return target


def _find_term_meaning_near_structure(target: str, context: dict[str, Any]) -> str:
    target_norm = normalize_text(target)
    for _source_field, source_text in _context_sources(context, include_translation=True):
        for sentence in _split_sentences(source_text):
            normalized = normalize_text(sentence)
            if target_norm not in normalized:
                continue
            patterns = [
                r"(?:nghĩa|nghia)\s+(?:là|la)\s+(?P<meaning>[^.。;]+)",
                r"[:：]\s*(?P<meaning>[^.。;]+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, sentence, flags=re.IGNORECASE)
                if match:
                    meaning = _clean_meaning(match.group("meaning"))
                    meaning = re.sub(r"\s+(?:quy định|rules/regulations|rules|regulations)\b.*$", "", meaning, flags=re.IGNORECASE).strip(" .")
                    if meaning and normalize_text(meaning) != target_norm:
                        return meaning
    return ""


def _is_example_request(normalized_message: str) -> bool:
    return _has_any(normalized_message, "vi du", "cho toi vi du", "example")


def _answer_example_request(normalized_message: str, context: dict[str, Any]) -> AnswerMatch:
    if "roughly" in normalized_message:
        return AnswerMatch(
            "Roughly + number nghĩa là khoảng/xấp xỉ.\nVí dụ: Roughly 200 people attended the event.",
            "fallback_grammar_rule",
            "roughly + number",
            None,
            "Roughly 200 people attended the event.",
        )
    if "during" in normalized_message:
        return AnswerMatch(
            "During + noun/noun phrase: trong suốt/trong khi diễn ra việc gì.\nVí dụ: During the meeting, we discussed the budget.",
            "fallback_grammar_rule",
            "during",
            None,
            "During the meeting",
        )
    return AnswerMatch()


def _is_option_reason_or_answer_request(normalized_message: str) -> bool:
    return _has_any(
        normalized_message,
        "dap an",
        "chon gi",
        "chon dap an",
        "cau nay chon",
        "vi sao chon",
        "tai sao chon",
        "vi sao khong chon",
        "tai sao khong chon",
        "why not",
        "not choose",
        "not correct",
        "khong chon",
        "khong dung",
        "khong phai",
        "sai o dau",
        "tai sao sai",
        "vi sao sai",
        "why is",
        "wrong",
    )


def _is_explain_wrong_option_request(normalized_message: str) -> bool:
    return bool(
        _has_any(
            normalized_message,
            "vi sao khong chon",
            "tai sao khong chon",
            "khong chon",
            "khong dung",
            "khong phai",
            "sai o dau",
            "tai sao sai",
            "vi sao sai",
            "why not",
            "not choose",
            "not correct",
            "wrong",
        )
    )


def _should_include_correct_for_option_request(normalized_message: str) -> bool:
    if _is_explain_wrong_option_request(normalized_message):
        return False
    return _has_any(
        normalized_message,
        "vi sao chon",
        "tai sao chon",
        "why",
        "dap an",
        "chung minh",
        "bang chung",
        "evidence",
    )


def _completion_mentioned_in_message(normalized_message: str, context: dict[str, Any]) -> str:
    for entry in _option_entries_from_context(context).values():
        term = str(entry.get("text") or "")
        if term and normalize_text(term) in normalized_message:
            return term
    answer = _strip_answer_label(context.get("correct_answer_text") or context.get("correct_answer") or "")
    if answer and normalize_text(answer) in normalized_message:
        return answer
    return ""


def answer_option_or_source_specific_question(
    message: str,
    context: dict[str, Any],
    target: str | None = None,
    option_label: str | None = None,
) -> AnswerMatch:
    normalized_message = normalize_text(message)
    entries = _option_entries_from_context(context)
    label = option_label or _option_label_for_message_or_target(message, context, entries, target)
    include_correct = _should_include_correct_for_option_request(normalized_message)

    if not option_label and _should_prefer_source_phrase(normalized_message):
        phrase = _answer_source_phrase_message(message, context, entries, include_correct=include_correct)
        if phrase.text:
            return phrase

    if label and label in entries and _is_option_specific_message(normalized_message, message, entries[label]):
        entry = entries[label]
        if _is_part_of_speech_question(normalized_message):
            return _format_option_part_of_speech_answer(label, entry, context, include_correct=include_correct)
        if _is_meaning_question(normalized_message):
            return _format_option_meaning_answer(label, entry, context, include_correct=include_correct)
        return _format_option_specific_reason_answer(label, entry, context, include_correct=include_correct)

    if _is_contextual_need_message(normalized_message):
        contextual = _answer_contextual_need_message(message, context, entries)
        if contextual.text:
            return contextual

    phrase = _answer_source_phrase_message(message, context, entries, include_correct=include_correct)
    if phrase.text:
        return phrase

    return AnswerMatch()


def _should_prefer_source_phrase(normalized_message: str) -> bool:
    tokens = _meaningful_message_tokens(normalized_message)
    structure_request = _has_any(normalized_message, "cau truc", "cong thuc", "dung sao", "dung nhu the nao", "di voi")
    phrase_cue = bool(re.search(r"\b(?:have|be|engage|look|take|make|get)\b", normalized_message))
    if structure_request and tokens:
        return True
    return bool(
        (len(tokens) >= 2 or (phrase_cue and tokens))
        and _has_any(normalized_message, "nghia", "mean")
    )


def _option_entries_from_context(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    correct_label, correct_text = _correct_label_and_text(context)
    for index, option in enumerate(_get_options(context)):
        label = str(option.get("label") or option.get("key") or _option_label(index)).strip().upper()
        if label not in {"A", "B", "C", "D"}:
            continue
        entries[label] = {
            "label": label,
            "text": _strip_answer_label(option.get("text")),
            "analysis": "",
            "is_correct": option.get("is_correct") is True or label == correct_label,
            "source_field": "Options",
        }

    for source_field, source_text in [
        ("OptionAnalysis", context.get("option_analysis")),
        ("RawBlock", context.get("raw_block")),
    ]:
        for parsed in _parse_option_entries_from_text(source_text, entries):
            label = parsed["label"]
            current = entries.setdefault(
                label,
                {
                    "label": label,
                    "text": "",
                    "analysis": "",
                    "is_correct": label == correct_label,
                    "source_field": source_field,
                },
            )
            if parsed.get("text") and not current.get("text"):
                current["text"] = parsed["text"]
            if parsed.get("analysis") and _is_substantive_option_analysis(parsed["analysis"]):
                current["analysis"] = parsed["analysis"]
                current["source_field"] = source_field
            if parsed.get("is_correct") is True:
                current["is_correct"] = True

    if correct_label:
        entries.setdefault(
            correct_label,
            {
                "label": correct_label,
                "text": correct_text,
                "analysis": "",
                "is_correct": True,
                "source_field": "CorrectAnswerText",
            },
        )
        entries[correct_label]["is_correct"] = True
        if correct_text and not entries[correct_label].get("text"):
            entries[correct_label]["text"] = correct_text
    return entries


def _parse_option_entries_from_text(source: Any, known_entries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    text = _compact(source)
    if not text:
        return []
    parsed: list[dict[str, Any]] = []
    for match in OPTION_ENTRY_MARKER_RE.finditer(text):
        label = (match.group("label_paren") or match.group("label_plain") or "").upper()
        if label not in {"A", "B", "C", "D"}:
            continue
        body = _compact(match.group("body"))
        if not body:
            continue
        option_text = str(known_entries.get(label, {}).get("text") or "")
        term, analysis = _split_option_term_and_analysis(body, option_text)
        parsed.append(
            {
                "label": label,
                "text": term or option_text,
                "analysis": analysis,
                "is_correct": _option_body_is_correct(analysis),
            }
        )
    return parsed


def _split_option_term_and_analysis(body: str, option_text: str = "") -> tuple[str, str]:
    text = _compact(body)
    if not text:
        return "", ""

    if option_text:
        expected = _strip_answer_label(option_text)
        match = re.match(rf"(?P<term>{re.escape(expected)})\b\s*(?:[:\uff1a]|[-\u2013\u2014])?\s*(?P<analysis>.*)$", text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return expected, _compact(match.group("analysis"))
        if OPTION_STATUS_RE.match(text) or _has_any(normalize_text(text), "sai", "dap an dung", "wrong", "correct"):
            return expected, text

    delimiter = re.search(r"\s*(?:[:\uff1a]|\s[-\u2013\u2014]\s)\s*", text)
    if delimiter and delimiter.start() <= 80:
        return _clean_target_phrase(text[: delimiter.start()]), _compact(text[delimiter.end() :])

    status = OPTION_STATUS_RE.search(text)
    if status and status.start() > 0:
        return _clean_target_phrase(text[: status.start()]), _compact(text[status.start() :])

    return _clean_target_phrase(text), ""


def _is_substantive_option_analysis(value: Any) -> bool:
    text = normalize_text(value)
    if not text:
        return False
    return any(
        marker in text
        for marker in (
            "sai",
            "dung",
            "dap an",
            "nghia",
            "danh tu",
            "tinh tu",
            "dong tu",
            "trang tu",
            "phu hop",
            "khong phu hop",
            "correct",
            "wrong",
        )
    )


def _option_body_is_correct(value: Any) -> bool:
    text = normalize_text(value)
    return "dap an dung" in text or "correct" in text or bool(re.search(r"\bdung\b", text))


def _option_label_for_message_or_target(
    message: str,
    context: dict[str, Any],
    entries: dict[str, dict[str, Any]],
    target: str | None,
) -> str | None:
    target_norm = normalize_text(target or "")
    message_norm = normalize_text(message)
    if target_norm:
        for label, entry in entries.items():
            if _normalized_terms_match(normalize_text(entry.get("text")), target_norm):
                return label
    for label, entry in entries.items():
        term = normalize_text(entry.get("text"))
        if len(term) < 2:
            continue
        if re.search(rf"\b{re.escape(term)}\b", message_norm):
            return label
    return _option_label_for_message_target(message, context)


def _is_option_specific_message(normalized_message: str, raw_message: str, entry: dict[str, Any]) -> bool:
    term = normalize_text(entry.get("text"))
    has_term = bool(term and re.search(rf"\b{re.escape(term)}\b", normalized_message))
    return bool(
        has_term
        or _has_any(
            normalized_message,
            "vi sao",
            "tai sao",
            "khong chon",
            "chon",
            "sai",
            "dung",
            "nghia",
            "la gi",
            "tu loai",
            "loai tu",
            "danh tu",
            "tinh tu",
            "dong tu",
            "trang tu",
            "why",
        )
    )


def _is_part_of_speech_question(normalized_message: str) -> bool:
    return _has_any(normalized_message, "tu loai", "loai tu", "danh tu", "tinh tu", "dong tu", "trang tu", "noun", "verb", "adjective", "adverb")


def _is_meaning_question(normalized_message: str) -> bool:
    return _has_any(normalized_message, "nghia", "la gi", "mean", "means", "meaning", "dich")


def _is_contextual_need_message(normalized_message: str) -> bool:
    if re.search(r"\bsau\s+\S+\s+(?:can|la gi|dung gi|dung tu gi|can gi)", normalized_message):
        return True
    return _has_any(
        normalized_message,
        "tu nao",
        "dap an nao",
        "can loai tu",
        "can dang tu",
        "mo ta trang thai",
        "trang thai cua",
        "sau clear",
        "sau social",
        "sau be",
    )


def _format_option_part_of_speech_answer(
    label: str,
    entry: dict[str, Any],
    context: dict[str, Any],
    include_correct: bool = False,
) -> AnswerMatch:
    term = str(entry.get("text") or "").strip()
    analysis = str(entry.get("analysis") or "")
    part_of_speech = _extract_detailed_part_of_speech(analysis) or _extract_part_of_speech(analysis)
    if not part_of_speech:
        part_of_speech = _infer_part_of_speech(term)
    if not part_of_speech:
        return _format_option_specific_reason_answer(label, entry, context)

    pieces = [f"{term} l\u00e0 {part_of_speech}."]
    requirement = _best_requirement_sentence_for_option(term, context)
    if requirement and not entry.get("is_correct"):
        pieces.append(_ensure_sentence(requirement))
    elif analysis:
        reason = _best_option_reason_sentence(analysis)
        if reason and normalize_text(reason) != normalize_text(part_of_speech):
            pieces.append(_ensure_sentence(reason))
    correct = _correct_answer_sentence(context)
    if include_correct and correct and not entry.get("is_correct"):
        pieces.append(correct)
    return AnswerMatch(" ".join(pieces), entry.get("source_field") or "OptionAnalysis", term, label, analysis)


def _format_option_meaning_answer(
    label: str,
    entry: dict[str, Any],
    context: dict[str, Any],
    include_correct: bool = False,
) -> AnswerMatch:
    term = str(entry.get("text") or "").strip()
    analysis = str(entry.get("analysis") or "")
    meaning = _extract_meaning_from_option_analysis(analysis, term)
    part_of_speech = _extract_detailed_part_of_speech(analysis) or _extract_part_of_speech(analysis)
    if meaning:
        if part_of_speech:
            text = f"{term} l\u00e0 {part_of_speech}, ngh\u0129a l\u00e0 \u201c{meaning}\u201d."
        else:
            text = f"{term} ngh\u0129a l\u00e0 \u201c{meaning}\u201d."
    elif part_of_speech:
        text = f"{term} l\u00e0 {part_of_speech}."
    else:
        return _format_option_specific_reason_answer(label, entry, context)
    if include_correct and not entry.get("is_correct"):
        correct = _correct_answer_sentence(context)
        if correct:
            text = f"{text} {correct}"
    return AnswerMatch(text, entry.get("source_field") or "OptionAnalysis", term, label, analysis)


def _format_option_specific_reason_answer(label: str, entry: dict[str, Any], context: dict[str, Any], include_correct: bool = False) -> AnswerMatch:
    term = str(entry.get("text") or "").strip()
    analysis = _clean_option_analysis_for_display(entry.get("analysis"))
    if not analysis:
        analysis = _best_requirement_sentence_for_option(term, context)
    status = "\u0111\u00fang" if entry.get("is_correct") else "sai"
    if analysis:
        subject = _capitalize_term(term) if term else label
        text = f"{subject} {status} v\u00ec {analysis}"
    else:
        subject = _capitalize_term(term) if term else label
        text = f"{subject} {status} theo d\u1eef li\u1ec7u \u0111\u00e1p \u00e1n hi\u1ec7n c\u00f3."
    if include_correct and not entry.get("is_correct"):
        correct = _correct_phrase_sentence(context) or _correct_answer_sentence(context)
        if correct:
            text = f"{text} {correct}"
    return AnswerMatch(_ensure_sentence(text), entry.get("source_field") or "OptionAnalysis", term, label, analysis)


def _answer_contextual_need_message(message: str, context: dict[str, Any], entries: dict[str, dict[str, Any]]) -> AnswerMatch:
    normalized_message = normalize_text(message)
    target = ""
    target_match = re.search(r"\bsau\s+([a-z][a-z'-]*)", normalized_message)
    if target_match:
        target = target_match.group(1)

    sentence = ""
    if target:
        sentence = _best_sentence_for_term_and_keywords(
            target,
            context,
            ("can", "danh tu", "tinh tu", "dong tu", "trang tu", "phu hop", "social", "clear"),
        )
    if not sentence:
        sentence = _best_sentence_for_keywords(
            context.get("explanation_detail") or context.get("explanation") or context.get("option_analysis") or context.get("raw_block"),
            ("can", "danh tu", "tinh tu", "dong tu", "trang tu", "mo ta", "trang thai", "phu hop"),
        )
    correct_label, correct_text = _correct_label_and_text(context)
    correct_entry = entries.get(correct_label or "")
    include_correct = "tu nao" in normalized_message or "dap an nao" in normalized_message or _is_option_reason_or_answer_request(normalized_message)
    parts = []
    if sentence:
        parts.append(_ensure_sentence(sentence))
    if include_correct and correct_label and correct_text:
        parts.append(_correct_answer_sentence(context))
    if include_correct and correct_entry and correct_entry.get("analysis"):
        reason = _clean_option_analysis_for_display(correct_entry.get("analysis"))
        if reason and not any(normalize_text(reason) in normalize_text(part) for part in parts):
            parts.append(_ensure_sentence(reason))
    if not parts:
        return AnswerMatch()
    return AnswerMatch(" ".join(part for part in parts if part), "ExplanationDetail/OptionAnalysis", correct_text, correct_label, sentence)


def _answer_source_phrase_message(
    message: str,
    context: dict[str, Any],
    entries: dict[str, dict[str, Any]],
    include_correct: bool = False,
) -> AnswerMatch:
    normalized_message = normalize_text(message)
    if not _has_any(normalized_message, "nghia", "cau truc", "cong thuc", "dung sao", "dung nhu the nao", "di voi", "collocation", "mean"):
        return AnswerMatch()

    tokens = _meaningful_message_tokens(normalized_message)
    if not tokens:
        return AnswerMatch()

    scored: list[tuple[int, str, str]] = []
    for source_field, source_text in _context_sources(context, include_translation=True):
        for sentence in _split_sentences(source_text):
            sentence_norm = normalize_text(sentence)
            score = sum(1 for token in tokens if _message_token_in_text(token, sentence_norm))
            if "+" in sentence:
                score += 1
            if any(marker in sentence_norm for marker in ("nghia", "cau truc", "dung voi", "di voi")):
                score += 1
            if score >= 2:
                scored.append((score, source_field, sentence))

    if not scored:
        return AnswerMatch()

    scored.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[str, str]] = []
    seen: set[str] = set()
    for _score, source_field, sentence in scored:
        normalized = normalize_text(sentence)
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append((source_field, sentence))
        if len(selected) >= 2:
            break

    answer_lines = [_ensure_sentence(sentence) for _field, sentence in selected]
    correct_label, correct_text = _correct_label_and_text(context)
    if include_correct and correct_text and normalize_text(correct_text) in normalized_message:
        correct = _correct_answer_sentence(context)
        if correct:
            answer_lines.append(correct)
    return AnswerMatch(" ".join(answer_lines), selected[0][0], "", None, " ".join(answer_lines))


def _meaningful_message_tokens(normalized_message: str) -> list[str]:
    raw_tokens = re.findall(r"[a-z0-9][a-z0-9'-]*", normalized_message)
    return [token for token in raw_tokens if len(token) > 2 and token not in OPTION_REQUEST_STOPWORDS]


def _message_token_in_text(token: str, normalized_text: str) -> bool:
    return bool(re.search(rf"\b{re.escape(token)}\b", normalized_text))


def _best_sentence_for_term_and_keywords(target: str, context: dict[str, Any], keywords: tuple[str, ...]) -> str:
    target_norm = normalize_text(target)
    best = ""
    best_score = 0
    for _source_field, source_text in _context_sources(context):
        for sentence in _split_sentences(source_text):
            normalized = normalize_text(sentence)
            if target_norm and target_norm not in normalized:
                continue
            score = sum(1 for keyword in keywords if keyword in normalized)
            if score > best_score:
                best = sentence
                best_score = score
    return best


def _best_requirement_sentence_for_option(term: str, context: dict[str, Any]) -> str:
    term_norm = normalize_text(term)
    keywords = ("can", "danh tu", "tinh tu", "dong tu", "trang tu", "phu hop", "khong phu hop", "social", "clear", "trang thai")
    best = ""
    best_score = 0
    for _source_field, source_text in _context_sources(context):
        for sentence in _split_sentences(source_text):
            normalized = normalize_text(sentence)
            score = sum(1 for keyword in keywords if keyword in normalized)
            if term_norm and term_norm in normalized:
                score += 1
            if score > best_score:
                best = sentence
                best_score = score
    return best


def _best_option_reason_sentence(analysis: Any) -> str:
    for sentence in _split_sentences(analysis):
        normalized = normalize_text(sentence)
        if any(token in normalized for token in ("khong phu hop", "phu hop", "can", "sau", "truoc")):
            return _clean_option_analysis_for_display(sentence)
    return ""


def _extract_detailed_part_of_speech(analysis: Any) -> str:
    for sentence in _split_sentences(analysis):
        normalized = normalize_text(sentence)
        if not any(token in normalized for token in ("danh tu", "tinh tu", "dong tu", "trang tu", "noun", "verb", "adjective", "adverb")):
            continue
        cleaned = _clean_option_analysis_for_display(sentence)
        match = re.search(r"(?:L\u00e0|La)\s+(?P<value>[^.;]+)", cleaned, flags=re.IGNORECASE)
        if match:
            return match.group("value").strip(" .")
        return cleaned.strip(" .")
    return ""


def _extract_meaning_from_option_analysis(analysis: Any, term: str) -> str:
    text = _compact(analysis)
    patterns = [
        r"(?:ngh\u0129a|nghia)\s+(?:l\u00e0|la)\s+\u201c?(?P<meaning>[^.\u201d;]+)",
        r"(?:c\u00f3\s+)?(?:ngh\u0129a|nghia)\s+(?:l\u00e0|la)\s+\"?(?P<meaning>[^.\";]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_meaning(match.group("meaning"))
    return ""


def _clean_option_analysis_for_display(value: Any) -> str:
    text = _compact(value)
    text = re.sub(
        r"^(?:Sai|Wrong|Correct|(?:\u0110|D)úng|(?:\u0110|D)áp\s+án\s+(?:\u0111úng|dung)|Dap\s+an\s+dung|Dap\s+an)\s*[:.\u3002-]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return _ensure_sentence(text) if text else ""


def _correct_label_and_text(context: dict[str, Any]) -> tuple[str, str]:
    label = str(context.get("correct_option_label") or context.get("correct_option_key") or "").strip().upper()
    text = _strip_answer_label(context.get("correct_answer_text") or "")
    if not text:
        correct_answer = _compact(context.get("correct_answer"))
        match = re.match(r"^([A-D])\s*[.)\u2014-]?\s*(.+)$", correct_answer, flags=re.IGNORECASE)
        if match:
            label = label or match.group(1).upper()
            text = _strip_answer_label(match.group(2))
        elif correct_answer:
            text = _strip_answer_label(correct_answer)
    for option in _get_options(context):
        option_label = str(option.get("label") or option.get("key") or "").strip().upper()
        if label and option_label == label and not text:
            text = _strip_answer_label(option.get("text"))
        if not label and option.get("is_correct") is True:
            label = option_label
            text = text or _strip_answer_label(option.get("text"))
    return label, text


def _correct_answer_sentence(context: dict[str, Any]) -> str:
    label, text = _correct_label_and_text(context)
    if label and text:
        return f"\u0110\u00e1p \u00e1n \u0111\u00fang l\u00e0 {label} \u2014 {text}."
    if text:
        return f"\u0110\u00e1p \u00e1n \u0111\u00fang l\u00e0 {text}."
    return ""


FORMULA_KEYWORDS = (
    "cong thuc",
    "cau truc",
    "cach dung",
    "dung voi",
    "di voi",
    "gioi tu",
    "sau",
    "truoc",
    "cho trong",
    "khoang trong",
    "can",
    "danh tu",
    "dong tu",
    "tinh tu",
    "trang tu",
    "v-ing",
    "v-ed",
    "to v",
    "bi dong",
    "phan tu",
)


GRAMMAR_CONCEPTS: dict[str, dict[str, Any]] = {
    "future_simple": {
        "label": "tương lai đơn",
        "kind": "tense",
        "aliases": ("tuong lai don", "future simple", "will + v", "will"),
        "keywords": ("will + v", "tuong lai don", "next year", "will"),
        "structure_patterns": (r"will\s*\+\s*V(?:\s+nguyên\s+mẫu)?",),
    },
    "present_simple": {
        "label": "hiện tại đơn",
        "kind": "tense",
        "aliases": ("hien tai don", "present simple"),
        "keywords": ("hien tai don", "v/vs", "do/does", "usually", "often"),
        "structure_patterns": (r"(?:V/Vs|V\(s/es\)|do/does\s*\+\s*V|does/do\s*\+\s*V)",),
    },
    "past_simple": {
        "label": "quá khứ đơn",
        "kind": "tense",
        "aliases": ("qua khu don", "past simple"),
        "keywords": ("qua khu don", "v2", "yesterday", "last"),
        "structure_patterns": (r"(?:V2|V-ed|did\s*\+\s*V)",),
    },
    "present_perfect": {
        "label": "hiện tại hoàn thành",
        "kind": "tense",
        "aliases": ("hien tai hoan thanh", "present perfect"),
        "keywords": ("have/has + v3", "have/has + v-ed", "hien tai hoan thanh", "has/have"),
        "structure_patterns": (r"(?:have/has|has/have|have\s*/\s*has)\s*\+\s*(?:V3|V-ed|past participle)(?:/V-ed)?",),
    },
    "passive": {
        "label": "bị động",
        "kind": "structure",
        "aliases": ("bi dong", "passive", "cau bi dong"),
        "keywords": ("be + v3", "be + v-ed", "bi dong", "passive"),
        "structure_patterns": (r"(?:be|am/is/are|was/were)\s*\+\s*(?:V3|V-ed|past participle)(?:/V-ed)?",),
    },
    "v_ing": {
        "label": "V-ing",
        "kind": "structure",
        "aliases": ("v-ing", "gerund", "danh dong tu"),
        "keywords": ("v-ing", "gerund", "danh dong tu", "phan tu"),
        "structure_patterns": (r"V-ing(?:\s+[^:：.。\n;]+)?",),
    },
    "to_v": {
        "label": "to V",
        "kind": "structure",
        "aliases": ("to v", "infinitive", "nguyen mau"),
        "keywords": ("to v", "dong tu nguyen mau", "infinitive"),
        "structure_patterns": (r"to\s+V(?:\s+[^:：.。\n;]+)?",),
    },
    "adverb": {
        "label": "trạng từ",
        "kind": "part_of_speech",
        "aliases": ("trang tu", "adverb"),
        "keywords": ("trang tu", "bo nghia cho dong tu", "adverb"),
        "structure_patterns": (r"trạng\s+từ[^.。;\n]*|trang\s+tu[^.。;\n]*",),
    },
    "adjective": {
        "label": "tính từ",
        "kind": "part_of_speech",
        "aliases": ("tinh tu", "adjective"),
        "keywords": ("tinh tu", "bo nghia cho danh tu", "adjective"),
        "structure_patterns": (r"tính\s+từ[^.。;\n]*|tinh\s+tu[^.。;\n]*",),
    },
    "noun": {
        "label": "danh từ",
        "kind": "part_of_speech",
        "aliases": ("danh tu", "noun"),
        "keywords": ("danh tu", "noun"),
        "structure_patterns": (r"danh\s+từ[^.。;\n]*|danh\s+tu[^.。;\n]*",),
    },
    "preposition": {
        "label": "giới từ",
        "kind": "part_of_speech",
        "aliases": ("gioi tu", "preposition"),
        "keywords": ("gioi tu", "preposition"),
        "structure_patterns": (r"giới\s+từ[^.。;\n]*|gioi\s+tu[^.。;\n]*",),
    },
    "relative_pronoun": {
        "label": "đại từ quan hệ",
        "kind": "structure",
        "aliases": ("dai tu quan he", "relative pronoun", "who", "which", "that", "where"),
        "keywords": ("dai tu quan he", "relative pronoun", "who", "which", "that", "where"),
        "structure_patterns": (r"(?:who|which|that|where)(?:\s*/\s*(?:who|which|that|where))*",),
    },
}


def answer_grammar_structure_definition(message: str, context: dict[str, Any]) -> AnswerMatch:
    normalized_message = normalize_text(message)
    concept = _detect_grammar_concept(normalized_message)
    if _asks_current_sentence_grammar(normalized_message):
        concept = concept or _infer_grammar_concept_from_context(context)
        current = _answer_current_sentence_grammar(concept, context)
        if current.text:
            return current

    if not concept:
        concept = _infer_grammar_concept_from_context(context)

    if not concept:
        return AnswerMatch()

    result = _find_structure_definition_for_concept(concept, context)
    if result.text:
        return result
    return AnswerMatch(concept=concept, aliases=_concept_aliases(concept))


def _is_grammar_structure_definition_intent(normalized_message: str) -> bool:
    if _asks_current_sentence_grammar(normalized_message):
        return True
    concept = _detect_grammar_concept(normalized_message)
    if not concept:
        return False
    return _has_any(
        normalized_message,
        "cau truc",
        "cong thuc",
        "la gi",
        "dung sao",
        "dung nhu the nao",
        "dung khi nao",
        "thi",
        "ngu phap",
        "formula",
        "structure",
    )


def _asks_current_sentence_grammar(normalized_message: str) -> bool:
    return _has_any(
        normalized_message,
        "cau nay dung thi gi",
        "cau nay hoi thi gi",
        "cau nay dung cau truc gi",
        "ngu phap cau nay la gi",
        "ngu phap cua cau nay la gi",
        "cau nay hoi ngu phap gi",
    )


def _detect_grammar_concept(normalized_text: str) -> str:
    for concept, spec in GRAMMAR_CONCEPTS.items():
        for alias in spec["aliases"]:
            alias_norm = normalize_text(alias)
            if not alias_norm:
                continue
            if alias_norm == "will" and not _has_any(normalized_text, "cau truc will", "cong thuc will", "will + v"):
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(alias_norm)}(?![a-z0-9])", normalized_text):
                return concept
    return ""


def _infer_grammar_concept_from_context(context: dict[str, Any]) -> str:
    joined = normalize_text(" ".join(_compact(value) for _field, value in _context_sources(context)))
    for concept, spec in GRAMMAR_CONCEPTS.items():
        for keyword in spec["keywords"]:
            keyword_norm = normalize_text(keyword)
            if keyword_norm and keyword_norm in joined:
                return concept
    return ""


def _answer_current_sentence_grammar(concept: str, context: dict[str, Any]) -> AnswerMatch:
    if not concept:
        return AnswerMatch()
    spec = GRAMMAR_CONCEPTS[concept]
    for source_field, source_text in [
        ("ExplanationDetail", context.get("explanation_detail") or context.get("explanation")),
        ("RawBlock", context.get("raw_block")),
        ("VocabularyNotes", context.get("vocabulary_notes") or context.get("vocabulary")),
    ]:
        sentence = _find_sentence_for_concept(source_text, concept)
        if not sentence:
            continue
        signal = _extract_time_or_grammar_signal(sentence) or _find_time_or_grammar_signal_for_concept(source_text, concept)
        label = spec["label"]
        if spec.get("kind") == "tense":
            answer = f"Câu này dùng thì {label}"
        else:
            answer = f"Câu này dùng cấu trúc {label}"
        if signal:
            answer += f" vì có dấu hiệu thời gian {_quote(signal)}"
        return AnswerMatch(
            _ensure_sentence(answer),
            source_field,
            label,
            None,
            sentence,
            concept=concept,
            aliases=_concept_aliases(concept),
        )
    return AnswerMatch()


def _find_structure_definition_for_concept(concept: str, context: dict[str, Any]) -> AnswerMatch:
    spec = GRAMMAR_CONCEPTS[concept]
    for source_field, source_text in _context_sources(context):
        for segment in _concept_candidate_segments(source_text, concept):
            structure = _extract_concept_structure(segment, spec)
            if not structure:
                continue
            base_structure = structure
            structure = _augment_concept_structure(structure, concept, context)
            meaning = _extract_definition_meaning(segment, structure) or _extract_definition_meaning(segment, base_structure)
            if not meaning and source_field != "VocabularyNotes":
                meaning = _find_concept_meaning_in_vocabulary(structure, concept, context)
            answer = _format_grammar_structure_definition(spec["label"], structure, meaning)
            return AnswerMatch(
                answer,
                source_field,
                spec["label"],
                None,
                segment,
                concept=concept,
                aliases=_concept_aliases(concept),
            )

        sentence = _find_sentence_for_concept(source_text, concept)
        if sentence:
            answer = _remove_answer_leaks(_ensure_sentence(sentence), context)
            return AnswerMatch(
                answer,
                source_field,
                spec["label"],
                None,
                sentence,
                concept=concept,
                aliases=_concept_aliases(concept),
            )
    return AnswerMatch(concept=concept, aliases=_concept_aliases(concept))


def _concept_candidate_segments(source: Any, concept: str) -> list[str]:
    text = _compact(source)
    if not text:
        return []
    pieces = _split_sentences(text)
    if ":" in text or "：" in text:
        pieces.extend(part.strip() for part in re.split(r"\n+|(?<=\.)\s+", text) if part.strip())
    return [piece for piece in pieces if _segment_matches_concept(piece, concept)]


def _segment_matches_concept(segment: str, concept: str) -> bool:
    normalized = normalize_text(segment)
    spec = GRAMMAR_CONCEPTS[concept]
    return any(normalize_text(item) in normalized for item in (*spec["aliases"], *spec["keywords"]))


def _find_sentence_for_concept(source: Any, concept: str) -> str:
    best = ""
    best_score = 0
    spec = GRAMMAR_CONCEPTS[concept]
    for sentence in _split_sentences(source):
        normalized = normalize_text(sentence)
        score = 0
        for keyword in (*spec["aliases"], *spec["keywords"]):
            if normalize_text(keyword) in normalized:
                score += 3
        if "cau truc" in normalized or "cong thuc" in normalized:
            score += 2
        if "dau hieu" in normalized or "can" in normalized:
            score += 3
        if score > best_score:
            best = sentence
            best_score = score
    return best


def _extract_concept_structure(segment: str, spec: dict[str, Any]) -> str:
    text = _compact(segment)
    structure_intro = re.search(
        r"(?:cấu\s+trúc\s+đúng\s+là|cau\s+truc\s+dung\s+la|cấu\s+trúc|cau\s+truc|công\s+thức|cong\s+thuc)\s*[:：]?\s*(?P<value>[^.。;\n]+)",
        text,
        flags=re.IGNORECASE,
    )
    if structure_intro:
        raw_value = _compact(structure_intro.group("value"))
        if ":" in raw_value or "：" in raw_value:
            left, right = re.split(r"[:：]", raw_value, maxsplit=1)
            if right.strip() and any(normalize_text(alias) in normalize_text(left) for alias in spec.get("aliases", ())):
                raw_value = right
        value = _clean_structure(raw_value)
        if value:
            return value
    for pattern in spec.get("structure_patterns", ()):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_structure(match.group(0))
    generic = re.search(r"(?P<value>[A-Za-z/]+\s*(?:\+\s*[A-Za-z0-9/.-]+(?:\s+[A-Za-zÀ-ỹ]+){0,3})?)\s*[:：]", text)
    if generic:
        return _clean_structure(generic.group("value"))
    return ""


def _augment_concept_structure(structure: str, concept: str, context: dict[str, Any]) -> str:
    clean = _clean_structure(structure)
    clean_norm = normalize_text(clean)
    for _source_field, source_text in _context_sources(context):
        for segment in _concept_candidate_segments(source_text, concept):
            candidate = _extract_concept_structure(segment, GRAMMAR_CONCEPTS[concept])
            if candidate and normalize_text(candidate).startswith(clean_norm) and len(candidate) > len(clean):
                return candidate
    return clean


def _extract_definition_meaning(segment: str, structure: str) -> str:
    text = _compact(segment)
    structure_pattern = re.escape(_clean_structure(structure))
    match = re.search(rf"{structure_pattern}\s*[:：]\s*(?P<meaning>[^.。;\n]+)", text, flags=re.IGNORECASE)
    if match:
        return _clean_meaning(match.group("meaning"))
    match = re.search(r"(?:nghĩa|nghia)\s+(?:là|la)\s*[\"“”]?(?P<meaning>[^.\"”;。]+)", text, flags=re.IGNORECASE)
    if match:
        return _clean_meaning(match.group("meaning"))
    return ""


def _find_concept_meaning_in_vocabulary(structure: str, concept: str, context: dict[str, Any]) -> str:
    vocab = context.get("vocabulary_notes") or context.get("vocabulary")
    if not vocab:
        return ""
    for segment in _concept_candidate_segments(vocab, concept):
        meaning = _extract_definition_meaning(segment, structure)
        if meaning:
            return meaning
    return ""


def _format_grammar_structure_definition(label: str, structure: str, meaning: str = "") -> str:
    answer = f"Cấu trúc {label}: {_clean_structure(structure)}."
    if meaning:
        answer += f"\nNghĩa là: {_ensure_sentence(_format_meaning_text(meaning))}"
    return answer


def _extract_time_or_grammar_signal(sentence: str) -> str:
    text = _compact(sentence)
    patterns = [
        r"dấu\s+hiệu\s+thời\s+gian\s+[\"“”]?(?P<signal>[^,\"”.;。]+)",
        r"dau\s+hieu\s+thoi\s+gian\s+[\"“”]?(?P<signal>[^,\"”.;。]+)",
        r"\b(?P<signal>next\s+\w+|last\s+\w+|yesterday|tomorrow|usually|often|already|since\s+[^,.;。]+|for\s+\d+\s+\w+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean_meaning(match.group("signal"))
    return ""


def _find_time_or_grammar_signal_for_concept(source: Any, concept: str) -> str:
    for sentence in _split_sentences(source):
        if _segment_matches_concept(sentence, concept):
            signal = _extract_time_or_grammar_signal(sentence)
            if signal:
                return signal
    for sentence in _split_sentences(source):
        signal = _extract_time_or_grammar_signal(sentence)
        if signal:
            return signal
    return ""


def _concept_aliases(concept: str) -> tuple[str, ...]:
    spec = GRAMMAR_CONCEPTS.get(concept, {})
    return tuple(spec.get("aliases", ()))


def _is_relative_pronoun_intent(normalized_message: str) -> bool:
    return _has_any(
        normalized_message,
        "dai tu quan he",
        "relative pronoun",
        "that hay where",
        "who hay which",
        "which hay that",
    )


def _is_collocation_preposition_intent(message: str, normalized_message: str) -> bool:
    if _is_blank_preposition_request(normalized_message):
        return True
    if _has_any(normalized_message, "gioi tu gi", "gioi tu nao", "dung voi gioi tu"):
        return True
    target = extract_word_or_phrase(message, [], "") or ""
    target_norm = normalize_text(target)
    if _has_any(normalized_message, "di voi gi", "dung voi gi"):
        return any(re.search(rf"\b{re.escape(prep)}\b", target_norm) for prep in PREPOSITIONS)
    return False


def _is_blank_preposition_request(normalized_message: str) -> bool:
    return (
        _has_any(normalized_message, "khoang trong", "cho trong", "cho nay", "o trong")
        and _has_any(normalized_message, "gioi tu", "dung gioi tu", "dung tu nao")
    )


def _is_target_completion_intent(normalized_message: str) -> bool:
    patterns = (
        r"\bdi voi tu gi\b",
        r"\bdi voi gi\b",
        r"\bdi voi gioi tu gi\b",
        r"\bdung voi gioi tu nao\b",
        r"\bra cum danh tu\b",
        r"\btao cum\b",
        r"\bcum danh tu cua\b",
        r"\bket hop voi tu nao\b",
        r"\bcollocation\b",
        r"\bsau .+ (?:can gi|la gi|can loai tu gi)\b",
        r"\btruoc .+ (?:can gi|la gi|can loai tu gi)\b",
        r"\bdi voi danh tu gi\b",
        r"\bdi voi tinh tu gi\b",
    )
    return any(re.search(pattern, normalized_message) for pattern in patterns)


def _target_blank_relation(target: str, context: dict[str, Any]) -> str:
    question = normalize_text(context.get("question_text_en") or context.get("question_text") or "")
    term = normalize_text(target)
    if not question or not term:
        return ""
    blank = r"(?:_{2,}|\[blank\]|blank)"
    target_pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
    if re.search(rf"{target_pattern}\s+{blank}", question):
        return "target_before_blank"
    if re.search(rf"{blank}\s+{target_pattern}", question):
        return "blank_before_target"
    return ""


def _is_preposition_word(value: str) -> bool:
    return normalize_text(value) in PREPOSITIONS


def _correct_completion_text(context: dict[str, Any]) -> str:
    answer = _strip_answer_label(context.get("correct_answer_text") or "")
    if answer:
        return answer
    label = str(context.get("correct_option_label") or context.get("correct_option_key") or "").strip().upper()
    if label:
        answer = _option_text(label, context)
        if answer:
            return answer
    for option in _get_options(context):
        if option.get("is_correct") is True:
            return _strip_answer_label(option.get("text"))
    correct = _format_correct_answer(context)
    return _strip_answer_label(correct.target or correct.completion or "")


def _option_label_for_message_target(message: str, context: dict[str, Any]) -> str | None:
    target = extract_word_or_phrase(message, _get_options(context), str(context.get("question_text_en") or context.get("question_text") or ""))
    target_norm = normalize_text(target or "")
    if not target_norm:
        normalized_message = normalize_text(message)
        for option in _get_options(context):
            option_text = normalize_text(_strip_answer_label(option.get("text")))
            if option_text and re.search(rf"(?<![a-z0-9]){re.escape(option_text)}(?![a-z0-9])", normalized_message):
                return str(option.get("label") or "").strip().upper() or None
        return None
    for option in _get_options(context):
        option_text = normalize_text(_strip_answer_label(option.get("text")))
        if option_text == target_norm:
            return str(option.get("label") or "").strip().upper() or None
    return None


def _completion_explanation_sentence(target: str, completion: str, context: dict[str, Any]) -> str:
    target_norm = normalize_text(target)
    completion_norm = normalize_text(completion)
    best = ""
    best_score = 0
    for source in [context.get("explanation_detail") or context.get("explanation"), context.get("raw_block")]:
        for sentence in _split_sentences(source):
            normalized = normalize_text(sentence)
            score = 0
            if target_norm and target_norm in normalized:
                score += 5
            if completion_norm and completion_norm in normalized:
                score += 4
            for keyword in ("can", "danh tu", "tinh tu", "trang tu", "dong tu", "cum dung", "cum danh tu", "phu hop", "nghia"):
                if keyword in normalized:
                    score += 1
            if score > best_score:
                best = sentence
                best_score = score
    return best


def _is_after_target_need_request(normalized_message: str) -> bool:
    return bool(re.search(r"\bsau .+ (?:can|la gi|dung gi)", normalized_message))


def _is_before_target_need_request(normalized_message: str) -> bool:
    return bool(re.search(r"\btruoc .+ (?:can|la gi|dung gi)", normalized_message))


def _asks_for_noun_phrase(normalized_message: str) -> bool:
    return _has_any(normalized_message, "cum danh tu", "ra cum", "tao cum")


def _extract_needed_after_target(target: str, source: Any) -> str:
    text = _compact(source)
    term = re.escape(_clean_target_phrase(target))
    patterns = [
        rf"(?:sau\s+(?:tính\s+từ|tinh\s+tu)?\s*{term})\s+(?:cần|can)\s+(?P<needed>[^.。;\n]+)",
        rf"{term}\s+(?:cần|can)\s+(?P<needed>[^.。;\n]+)",
    ]
    return _extract_needed_from_patterns(text, patterns)


def _extract_needed_before_target(target: str, source: Any) -> str:
    text = _compact(source)
    term = re.escape(_clean_target_phrase(target))
    patterns = [
        rf"(?:trước|truoc)\s+{term}\s+(?:cần|can)\s+(?P<needed>[^.。;\n]+)",
        rf"(?:chỗ|cho|khoảng|khoang|ô|o)\s+trống\s+đứng\s+trước\s+(?:danh\s+từ\s+)?{term}[^,.;。]*,?\s*(?:nên|nen)\s+(?:cần|can)\s+(?P<needed>[^.。;\n]+)",
    ]
    return _extract_needed_from_patterns(text, patterns)


def _extract_needed_from_patterns(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            needed = _trim_reason(match.group("needed"))
            needed = re.sub(r"\s*(?:\.|,?\s*cụm đúng.*|,?\s*cum dung.*)$", "", needed, flags=re.IGNORECASE)
            return needed.strip(" .")
    return ""


def _structure_from_explanation(target: str, completion: str, context: dict[str, Any]) -> str:
    phrase = f"{target} {completion}".strip()
    for source in [context.get("explanation_detail") or context.get("explanation"), context.get("vocabulary_notes"), context.get("raw_block")]:
        structure = _extract_structure_for_target(target, _compact(source))
        if structure and normalize_text(completion) in normalize_text(structure):
            return structure
        if normalize_text(phrase) in normalize_text(source):
            return phrase
    return phrase


def _find_structure_for_completion_and_target(target: str, completion: str, context: dict[str, Any]) -> str:
    target_norm = normalize_text(target)
    completion_norm = normalize_text(completion)
    best = ""
    for source_field, source_text in [
        ("VocabularyNotes", context.get("vocabulary_notes") or context.get("vocabulary")),
        ("ExplanationDetail", context.get("explanation_detail") or context.get("explanation")),
        ("OptionAnalysis", context.get("option_analysis")),
        ("RawBlock", context.get("raw_block")),
    ]:
        for sentence in _split_sentences(source_text):
            normalized = normalize_text(sentence)
            if target_norm and target_norm not in normalized:
                continue
            if completion_norm and completion_norm not in normalized:
                continue
            structure = _extract_structure_for_target(target, sentence) if target else ""
            if not structure and ":" in sentence:
                structure = _clean_structure(sentence.split(":", 1)[0])
            if structure:
                return _localize_structure_terms(structure)
            best = sentence
    return _localize_structure_terms(_clean_structure(best))


def _completion_after_target(target: str, structure: str) -> str:
    target_norm = normalize_text(target)
    structure_clean = _clean_structure(structure)
    structure_norm = normalize_text(structure_clean)
    if not target_norm or not structure_norm.startswith(target_norm):
        return ""
    rest = structure_clean[len(target) :].strip()
    rest = re.sub(r"^\s+", "", rest)
    rest = re.split(r"\s*\+\s*|[,.;。]", rest, maxsplit=1)[0].strip()
    return rest


def _infer_collocation_target_from_blank(context: dict[str, Any], completion: str) -> str:
    before_blank, _after_blank = _blank_neighbor_pair(context)
    question = str(context.get("question_text") or context.get("question_text_en") or "")
    if not before_blank:
        return ""
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", question.split("____", 1)[0])
    if not tokens:
        return before_blank
    tail = tokens[-3:]
    for size in range(min(3, len(tail)), 0, -1):
        candidate = " ".join(tail[-size:])
        structure = _find_structure_for_completion_and_target(candidate, completion, context)
        if structure and normalize_text(candidate) in normalize_text(structure):
            return candidate
    return before_blank


def _localize_structure_terms(value: str) -> str:
    text = _clean_structure(value)
    text = re.sub(r"\bplace\b", "địa điểm", text, flags=re.IGNORECASE)
    return text


def _completion_reason(completion: str, option_entry: dict[str, str], explanation_sentence: str) -> str:
    body = _clean_option_body(option_entry.get("body")) if option_entry else ""
    if body:
        body = _quote_meaning_tail(body)
        if normalize_text(completion) in normalize_text(body):
            return _ensure_sentence(body)
        return _ensure_sentence(f"{_quote(completion)} {_lower_first(body)}")
    if explanation_sentence:
        reason = _extract_reason_after_phrase(explanation_sentence)
        if reason:
            return _ensure_sentence(reason)
    return ""


def _answer_completion_neighbor_request(completion: str, context: dict[str, Any], normalized_message: str) -> AnswerMatch:
    before_blank, after_blank = _blank_neighbor_pair(context)
    completion_display = _lower_first(completion)
    if _is_before_target_need_request(normalized_message) and before_blank:
        phrase = f"{before_blank} {completion}".strip()
        return AnswerMatch(
            f"Trước {_quote(completion_display)} là {_quote(before_blank)} trong cụm {_quote(phrase)}.",
            "QuestionTextEn/CorrectAnswerText",
            completion,
            None,
            phrase,
            True,
            before_blank,
        )
    if _is_after_target_need_request(normalized_message) and after_blank:
        phrase = f"{completion} {after_blank}".strip()
        return AnswerMatch(
            f"Sau {_quote(completion_display)} là {_quote(after_blank)} trong cụm {_quote(phrase)}.",
            "QuestionTextEn/CorrectAnswerText",
            completion,
            None,
            phrase,
            True,
            after_blank,
        )
    if _has_any(normalized_message, "di voi danh tu", "di voi tu gi", "di voi gi") and after_blank:
        phrase = f"{completion} {after_blank}".strip()
        return AnswerMatch(
            f"{_quote(completion_display)} đi với {_quote(after_blank)} trong câu này: {phrase}.",
            "QuestionTextEn/CorrectAnswerText",
            completion,
            None,
            phrase,
            True,
            after_blank,
        )
    return AnswerMatch()


def _infer_relative_pronoun_antecedent(context: dict[str, Any]) -> str:
    question = str(context.get("question_text") or context.get("question_text_en") or "")
    match = re.search(r",\s*([^,]{1,80}?)\s+_{2,}", question)
    if match:
        return _clean_target_phrase(match.group(1))
    before_blank, _after_blank = _blank_neighbor_pair(context)
    return before_blank


def _relative_pronoun_sentence(source: Any, target: str, answer: str) -> str:
    target_norm = normalize_text(target)
    answer_norm = normalize_text(answer)
    best = ""
    best_score = 0
    for sentence in _split_sentences(source):
        normalized = normalize_text(sentence)
        score = 0
        if "dai tu quan he" in normalized or "relative pronoun" in normalized:
            score += 4
        if target_norm and target_norm in normalized:
            score += 3
        if answer_norm and re.search(rf"(?<![a-z0-9]){re.escape(answer_norm)}(?![a-z0-9])", normalized):
            score += 2
        if _has_any(normalized, "lam chu ngu", "thay the", "that", "where", "which", "who"):
            score += 1
        if score > best_score:
            best = sentence
            best_score = score
    return best


def _extract_relative_pronoun_role(sentence: str, context: dict[str, Any]) -> str:
    match = re.search(
        r"làm\s+chủ\s+ngữ\s+cho\s+động\s+từ\s+[\"“”]?([A-Za-z][A-Za-z'-]*)[\"“”]?",
        sentence,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"lam\s+chu\s+ngu\s+cho\s+dong\s+tu\s+[\"“”]?([A-Za-z][A-Za-z'-]*)[\"“”]?",
            normalize_text(sentence),
            flags=re.IGNORECASE,
        )
    if match:
        return f"làm chủ ngữ cho động từ {_quote(match.group(1))}"
    question = str(context.get("question_text") or context.get("question_text_en") or "")
    blank_match = re.search(r"_{2,}\s+([A-Za-z][A-Za-z'-]*)", question)
    if blank_match:
        return f"làm chủ ngữ cho động từ {_quote(blank_match.group(1))}"
    return ""


def _blank_neighbor_pair(context: dict[str, Any]) -> tuple[str, str]:
    question = str(context.get("question_text") or context.get("question_text_en") or "")
    match = re.search(r"([A-Za-z][A-Za-z'-]*)?\s*_{2,}\s*([A-Za-z][A-Za-z'-]*)?", question)
    if not match:
        return "", ""
    return (match.group(1) or "").strip(), (match.group(2) or "").strip()


def _quote_meaning_tail(value: str) -> str:
    return re.sub(
        r"(nghĩa|nghia)\s+([^“”\".,;。]+)",
        lambda match: f"{match.group(1)} “{match.group(2).strip()}”",
        value,
        flags=re.IGNORECASE,
    )


def _extract_reason_after_phrase(sentence: str) -> str:
    match = re.search(r"(?:nghĩa|nghia)\s+(?:là|la)\s*[\"“”]?(?P<meaning>[^.\"”;。]+)", sentence, flags=re.IGNORECASE)
    if match:
        return f"Nghĩa là “{_clean_meaning(match.group('meaning'))}”."
    return ""


def _is_gap_formula_request(normalized_message: str) -> bool:
    return _has_any(
        normalized_message,
        "khoang trong",
        "cho trong",
        "o trong",
        "can dang",
        "can loai tu",
        "cau nay can",
        "cau nay hoi ngu phap",
    )


def _is_part_of_speech_request(normalized_message: str) -> bool:
    return _has_any(
        normalized_message,
        "loai tu",
        "part of speech",
        "danh tu hay",
        "tinh tu hay",
        "trang tu hay",
        "dong tu hay",
        "la danh tu",
        "la tinh tu",
        "la trang tu",
        "la dong tu",
    )


def _is_preposition_request(normalized_message: str) -> bool:
    return _has_any(
        normalized_message,
        "gioi tu",
        "di voi",
        "dung voi",
        "sau ",
        "truoc ",
    )


def _find_formula_structure_for_target(
    target: str,
    context: dict[str, Any],
    prefer_preposition: bool = False,
) -> AnswerMatch:
    term = _clean_target_phrase(target)
    if not term:
        return AnswerMatch()

    for source_field, source_text in _context_sources(context):
        text = _compact(source_text)
        if not text:
            continue

        segments = []
        entry = _parse_option_entry_for_term(text, term)
        if entry:
            segments.append(f"{entry.get('term')}: {entry.get('body')}")
            segments.append(entry.get("body") or "")
        segments.append(text)

        for segment in segments:
            structure = _extract_structure_for_target(term, segment)
            if structure:
                meaning = _extract_meaning_for_structure_entry(segment, term, structure)
                answer = _format_formula_structure_answer(term, structure, meaning, prefer_preposition)
                return AnswerMatch(answer, source_field, term, None, structure)

        for segment in segments:
            sentence = _best_sentence_for_keywords(segment, FORMULA_KEYWORDS)
            if sentence and (entry or normalize_text(term) in normalize_text(sentence)):
                answer = _remove_answer_leaks(_ensure_sentence(sentence), context)
                return AnswerMatch(answer, source_field, term, None, sentence)

    return AnswerMatch()


def _find_part_of_speech_for_target(target: str, context: dict[str, Any]) -> AnswerMatch:
    term = _clean_target_phrase(target)
    if not term:
        return AnswerMatch()

    target_norm = normalize_text(term)
    for source_field, source_text in _context_sources(context):
        text = _compact(source_text)
        if not text:
            continue

        candidates = []
        entry = _parse_option_entry_for_term(text, term)
        if entry:
            candidates.append(f"{entry.get('term')}: {entry.get('body')}")
            candidates.extend(_split_sentences(entry.get("body") or ""))
        candidates.extend(sentence for sentence in _split_sentences(text) if target_norm in normalize_text(sentence))

        for candidate in candidates:
            part_of_speech = _extract_part_of_speech(candidate)
            if part_of_speech:
                return AnswerMatch(
                    f"{_capitalize_term(term)} là {part_of_speech}.",
                    source_field,
                    term,
                    None,
                    candidate,
                )

    return AnswerMatch()


def _find_general_formula_answer(context: dict[str, Any], normalized_message: str = "") -> AnswerMatch:
    if _is_gap_formula_request(normalized_message):
        gap = extract_gap_requirement(context)
        if gap.text:
            return gap

    for source_field, source_text in _context_sources(context):
        text = _compact(source_text)
        if not text:
            continue

        structure, meaning, snippet = _extract_first_structure_with_meaning(text)
        if structure:
            answer = _format_formula_structure_answer("", structure, meaning, False)
            return AnswerMatch(answer, source_field, "", None, snippet or structure)

        sentence = _best_sentence_for_keywords(text, FORMULA_KEYWORDS)
        if sentence:
            answer = _remove_answer_leaks(_ensure_sentence(sentence), context)
            return AnswerMatch(answer, source_field, "", None, sentence)

    return AnswerMatch()


def _infer_formula_target(context: dict[str, Any]) -> str:
    answer = _strip_answer_label(context.get("correct_answer_text") or context.get("correct_answer") or "")
    if answer:
        return answer
    for source_field, source_text in _context_sources(context):
        structure, _meaning, _snippet = _extract_first_structure_with_meaning(source_text)
        if structure:
            return _clean_target_phrase(re.split(r"\s*\+|\s+", structure, maxsplit=1)[0])
    return ""


def _parse_option_entry_for_term(source: Any, target: str) -> dict[str, str]:
    target_norm = normalize_text(target)
    if not target_norm:
        return {}
    for label in ("A", "B", "C", "D"):
        entry = _parse_option_entry(source, label)
        entry_term_norm = normalize_text(entry.get("term") if entry else "")
        if not entry_term_norm:
            continue
        if _normalized_terms_match(entry_term_norm, target_norm):
            return entry
    return {}


def _normalized_terms_match(entry_term_norm: str, target_norm: str) -> bool:
    if entry_term_norm == target_norm:
        return True
    return bool(
        re.search(rf"\b{re.escape(entry_term_norm)}\b", target_norm)
        or re.search(rf"\b{re.escape(target_norm)}\b", entry_term_norm)
    )


def _extract_meaning_for_structure_entry(source: Any, target: str, structure: str) -> str:
    text = _compact(source)
    for candidate in (structure, target):
        pattern = rf"{re.escape(candidate)}\s*[:：]\s*(?P<meaning>[^.。\n;]+)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            meaning = _clean_meaning(match.group("meaning"))
            if meaning and normalize_text(meaning) != normalize_text(candidate):
                return meaning
        parsed = _parse_meaning_from_text(text, candidate)
        if parsed.get("meaning"):
            return parsed["meaning"]
    return ""


def _extract_first_structure_with_meaning(source: Any) -> tuple[str, str, str]:
    text = _compact(source)
    if not text:
        return "", "", ""

    prep_union = "|".join(PREPOSITIONS)
    patterns = [
        r"(?:cấu\s*trúc\s*đúng\s*là|cau\s*truc\s*dung\s*la|cấu\s*trúc|cau\s*truc)\s*[:：]?\s*(?P<structure>[^.。\n;]+)",
        rf"(?P<structure>[A-Za-z][A-Za-z' -]{{0,90}}(?:\+\s*[^:：.。\n;]+|\s+(?:{prep_union})\b\s*\+\s*[^:：.。\n;]+))\s*[:：]\s*(?P<meaning>[^.。\n;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        structure = _clean_structure(match.group("structure"))
        meaning = _clean_meaning(match.groupdict().get("meaning") or "")
        if not meaning:
            meaning = _extract_meaning_for_structure_entry(text, structure, structure)
        return structure, meaning, match.group(0)
    return "", "", ""


def _format_formula_structure_answer(
    target: str,
    structure: str,
    meaning: str = "",
    prefer_preposition: bool = False,
) -> str:
    clean_structure = _clean_structure(structure)
    if prefer_preposition and target:
        preposition = _extract_preposition(target, clean_structure)
        if preposition:
            return f"{_quote(_lower_first(target))} đi với giới từ “{preposition}”.\nCấu trúc: {clean_structure}."

    if meaning:
        return f"Cấu trúc: {clean_structure}\nNghĩa là: {_ensure_sentence(_format_meaning_text(meaning))}"
    return f"Cấu trúc: {clean_structure}."


def _compact(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _ensure_sentence(value: Any) -> str:
    text = clean_response(value)
    if text and text[-1] not in ".!?。":
        return text + "."
    return text


def _strip_answer_label(value: Any) -> str:
    return re.sub(r"^\s*(?:\(?[A-D]\)?[.)]|[A-D]\s*[:\-])\s*", "", str(value or "").strip(), flags=re.IGNORECASE)


def _clean_target_phrase(value: str) -> str:
    text = str(value or "").strip(" \t\r\n\"'“”‘’`.,;:?!")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^(?:của|cua)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\s+(?:là|la|nghĩa|nghia|mean|means|meaning|đi với|di voi|dùng với|dung voi|cần|can)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    return text


def _is_useful_target(value: str | None) -> bool:
    target = normalize_text(value or "")
    return bool(target and target not in GENERIC_TARGETS and len(target) <= 80)


def _restore_phrase_case(target: str, options: list[dict[str, Any]], question_text: str) -> str:
    normalized_target = normalize_text(target)
    for option in options:
        option_text = _strip_answer_label(option.get("text"))
        if normalize_text(option_text) == normalized_target:
            return option_text
    for source in [question_text, " ".join(str(option.get("text") or "") for option in options)]:
        match = re.search(re.escape(target), source, flags=re.IGNORECASE)
        if match:
            return source[match.start() : match.end()]
    return target


def _find_option_by_label(context: dict[str, Any], label: str) -> dict[str, Any] | None:
    target = str(label or "").strip().upper()
    for option in _get_options(context):
        if str(option.get("label") or "").strip().upper() == target:
            return option
    return None


def _find_option_for_term(context: dict[str, Any], term: str) -> dict[str, Any] | None:
    target = normalize_text(term)
    if not target:
        return None
    for option in _get_options(context):
        option_text = normalize_text(_strip_answer_label(option.get("text")))
        if option_text == target:
            return option
    for option in _get_options(context):
        option_text = normalize_text(_strip_answer_label(option.get("text")))
        if re.search(rf"\b{re.escape(target)}\b", option_text):
            return option
    return None


def _option_text(label: str | None, context: dict[str, Any]) -> str:
    if not label:
        return ""
    option = _find_option_by_label(context, label)
    return _strip_answer_label(option.get("text")) if option else ""


def _parse_meaning_from_text(source: Any, target: str, option_label: str | None = None) -> dict[str, str]:
    text = _compact(source)
    term = _clean_target_phrase(target)
    if not text or not term:
        return {}

    entry = _parse_option_entry(text, option_label or "") if option_label else {}
    if entry and normalize_text(entry.get("term")) == normalize_text(term):
        parsed = _parse_meaning_from_body(entry.get("body"), entry.get("term") or term)
        if parsed.get("meaning"):
            parsed["snippet"] = entry.get("body", "")
            return parsed

    entry_pattern = (
        r"(?:\(\s*(?P<label>[A-D])\s*\)\s*)?"
        + rf"(?P<term>{re.escape(term)}(?:\s*\+\s*[^:：.。\n;]+)?)\s*[:：]\s*(?P<body>.*?)(?=(?:\(\s*[A-D]\s*\)\s*[^:：]{{0,80}}[:：])|(?:\n\s*\n)|$)"
    )
    match = re.search(entry_pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        body = match.group("body")
        parsed = _parse_meaning_from_body(body, match.group("term"))
        if parsed.get("meaning"):
            parsed["snippet"] = _compact(body)
            return parsed

    patterns = [
        rf"{re.escape(term)}\s+(?:có\s+)?(?:nghĩa|nghia)\s+(?:là|la)\s+[\"“”]?(?P<meaning>[^.\"”。;\n]+)",
        rf"{re.escape(term)}\s*=\s*(?P<meaning>[^.。;\n]+)",
        rf"{re.escape(term)}\s*/\s*(?:[^/]+/)?\s*(?P<meaning>[^.。;\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            meaning = _clean_meaning(match.group("meaning"))
            if meaning and normalize_text(meaning) != normalize_text(term):
                return {
                    "term": term,
                    "meaning": meaning,
                    "part_of_speech": _extract_part_of_speech(match.group(0)) or _infer_part_of_speech(term),
                    "snippet": match.group(0),
                }
    return {}


def _parse_meaning_from_body(body: Any, term: str) -> dict[str, str]:
    text = _compact(body)
    meaning_match = re.search(
        r"(?:có\s+)?(?:nghĩa|nghia)\s+(?:là|la)\s+[\"“”]?(?P<meaning>[^.\"”。;\n]+)",
        text,
        flags=re.IGNORECASE,
    )
    if meaning_match:
        return {
            "term": term,
            "meaning": _clean_meaning(meaning_match.group("meaning")),
            "part_of_speech": _extract_part_of_speech(text) or _infer_part_of_speech(term),
        }
    simple = re.sub(r"^(?:Sai|Đúng|Dap an dung|Đáp án đúng|Correct|Wrong)\s*[:.。-]?\s*", "", text, flags=re.IGNORECASE)
    if simple and not re.search(r"\b(?:sai|đúng|dung|đáp án|dap an)\b", normalize_text(simple)):
        first = _first_sentence(simple, 120)
        if first:
            return {
                "term": term,
                "meaning": _clean_meaning(first),
                "part_of_speech": _extract_part_of_speech(text) or _infer_part_of_speech(term),
            }
    return {"term": term}


def _parse_option_entry(source: Any, label: str) -> dict[str, str]:
    text = _compact(source)
    if not text or not label:
        return {}
    label = label.upper()
    marker = rf"(?:\(\s*{label}\s*\)|\b{label}\s*[.)])"
    next_marker = r"(?=(?:\(\s*[A-D]\s*\)|\b[A-D]\s*[.)])\s*[^:：]{0,100}[:：]|$)"
    pattern = marker + r"\s*(?P<term>[^:：()]{0,100}?)(?:[:：]\s*|\s+-\s*)(?P<body>.*?)" + next_marker
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return {}
    return {
        "term": _clean_target_phrase(match.group("term")),
        "body": _compact(match.group("body")),
        "label": label,
    }


def _clean_meaning(value: Any) -> str:
    text = _compact(value)
    text = re.sub(r"^[\"'“”]+|[\"'“”]+$", "", text)
    text = re.sub(r"\s*(?:\([A-D]\).*)$", "", text)
    return text.strip(" .;:")


def _format_meaning_text(value: str) -> str:
    text = _clean_meaning(value)
    parts = [part.strip() for part in re.split(r"\s*,\s*", text) if part.strip()]
    if 1 < len(parts) <= 3 and all(len(part.split()) <= 4 for part in parts):
        return "/".join(parts)
    return text


def _format_meaning_answer(term: str, meaning: str, part_of_speech: str | None) -> str:
    display = _capitalize_term(term)
    meaning_text = _format_meaning_text(meaning)
    if "+" in display:
        return f"{display} nghĩa là {meaning_text}."
    if part_of_speech:
        return f"{display} là {part_of_speech}, nghĩa là “{meaning_text}”."
    return f"{display} nghĩa là “{meaning_text}”."


def _capitalize_term(term: str) -> str:
    text = _clean_target_phrase(term)
    if " " in text or "+" in text:
        return text
    return text[:1].upper() + text[1:] if text else text


def _extract_part_of_speech(text: Any) -> str:
    normalized = normalize_text(text)
    if "danh tu" in normalized or "noun" in normalized:
        return "danh từ"
    if "tinh tu" in normalized or "adjective" in normalized:
        return "tính từ"
    if "trang tu" in normalized or "adverb" in normalized:
        return "trạng từ"
    if "dong tu" in normalized or "verb" in normalized:
        return "động từ"
    return ""


def _infer_part_of_speech(term: str) -> str:
    target = normalize_text(term)
    if target.endswith(("tion", "sion", "ment", "ness", "ity", "ance", "ence")):
        return "danh từ"
    if target.endswith("ly"):
        return "trạng từ"
    if target.endswith(("ive", "al", "ous", "ful", "less", "able", "ible")):
        return "tính từ"
    return ""


def _extract_structure_for_target(target: str, source: str) -> str:
    term = re.escape(_clean_target_phrase(target))
    structure_patterns = [
        rf"(?:cấu\s*trúc|cau\s*truc|cấu\s*trúc\s*đúng\s*là|cau\s*truc\s*dung\s*la)\s*[:：]?\s*(?P<structure>[^.。\n;]+{term}[^.。\n;]*)",
        rf"(?P<structure>{term}\s+(?:{'|'.join(PREPOSITIONS)})\b(?:\s*\+\s*[^.。\n;]+)?)",
        rf"(?P<structure>{term}\s*\+\s*[^.。\n;]+)",
        rf"(?P<structure>{term}\s+to\s+V\b[^.。\n;]*)",
        rf"(?P<structure>{term}\s+[^:：.。\n;]+)\s*[:：]",
    ]
    for pattern in structure_patterns:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match:
            return _clean_structure(match.group("structure"))
    return ""


def _clean_structure(value: Any) -> str:
    text = _compact(value)
    text = re.sub(r"^(?:đúng là|dung la)\s+", "", text, flags=re.IGNORECASE)
    text = re.split(r"[:：]", text, maxsplit=1)[0]
    return text.strip(" .;:")


def _extract_preposition(target: str, structure: str) -> str:
    target_norm = normalize_text(target)
    structure_norm = normalize_text(structure)
    if structure_norm.startswith(target_norm):
        rest = structure_norm[len(target_norm) :].strip()
        first = rest.split()[0] if rest.split() else ""
        if first in PREPOSITIONS:
            return first
    for prep in PREPOSITIONS:
        if re.search(rf"\b{re.escape(prep)}\b", structure_norm):
            return prep
    return ""


def _extract_meaning_near_structure(target: str, source: str, structure: str) -> str:
    for candidate in (structure, target):
        parsed = _parse_meaning_from_text(source, candidate)
        if parsed.get("meaning"):
            return parsed["meaning"]
    return ""


def _find_sentence_with_target_and_keywords(source: str, target: str, keywords: tuple[str, ...]) -> str:
    target_norm = normalize_text(target)
    for sentence in _split_sentences(source):
        normalized = normalize_text(sentence)
        if target_norm in normalized and any(keyword in normalized for keyword in keywords):
            return sentence
    return ""


def _split_sentences(value: Any) -> list[str]:
    text = str(value or "").replace("\r", "\n")
    chunks = re.split(r"(?<=[.!?。])\s+|\n+", text)
    return [_compact(chunk).strip(" -") for chunk in chunks if _compact(chunk)]


def _format_gap_requirement(sentence: str) -> str:
    source = _ensure_sentence(sentence)
    source = _remove_answer_words(source)

    before_noun = re.search(
        r"(?:chỗ|cho|khoảng|khoang|ô|o)\s+trống\s+đứng\s+trước\s+danh\s+từ\s+[\"“”]?([A-Za-z][A-Za-z'-]*)[\"“”]?,?\s*(?:nên|nen)\s+cần\s+(.+?)(?:\.|$)",
        source,
        flags=re.IGNORECASE,
    )
    if before_noun:
        noun = before_noun.group(1)
        needed = _trim_reason(before_noun.group(2))
        return f"Khoảng trống cần {needed}, vì nó đứng trước danh từ “{noun}”."

    after_verb = re.search(
        r"(?:sau\s+động\s+từ|sau\s+dong\s+tu)\s+[\"“”]?([A-Za-z']+)[\"“”]?,?\s*(?:cần|can)\s+(.+?)(?:\.|$)",
        source,
        flags=re.IGNORECASE,
    )
    if after_verb:
        verb = after_verb.group(1)
        needed = _trim_reason(after_verb.group(2))
        purpose_match = re.search(r"\s+(?:để|de)\s+", needed, flags=re.IGNORECASE)
        if purpose_match:
            purpose = needed[purpose_match.end() :]
            needed = needed[: purpose_match.start()]
            return f"Câu cần {needed} sau động từ “{verb}” để {purpose}."
        return f"Câu cần {needed} sau động từ “{verb}”."

    return source


def _trim_reason(value: str) -> str:
    text = _compact(value)
    text = re.sub(r"\s*(?:nên|do đó|vì vậy|vi vay)\s+.*$", "", text, flags=re.IGNORECASE)
    return text.strip(" .")


def _remove_answer_words(value: str) -> str:
    text = re.sub(r"\s*(?:Đáp án|Dap an)\s+(?:phù hợp|phu hop|đúng|dung)?\s*(?:là|la)\s+[A-D]?[.)]?\s*[A-Za-z'-]+.*$", "", value, flags=re.IGNORECASE)
    return _ensure_sentence(text)


def _format_option_reason(label: str, term: str, body: str, context: dict[str, Any]) -> str:
    status = normalize_text(body)
    clean = _clean_option_body(body)
    term = term or _option_text(label, context)
    if "sai" in status or "wrong" in status:
        if clean:
            return f"{label} sai vì {_quote_time_signals(_quote_question_terms(_ensure_term_in_reason(term, clean), context))}"
        return f"{label} sai theo phân tích đáp án trong dữ liệu."
    if "dap an dung" in status or re.search(r"\bdung\b", status):
        if clean:
            return f"{label} đúng vì {_quote_time_signals(_quote_question_terms(_ensure_term_in_reason(term, clean), context))}"
        return f"{label} là đáp án đúng."
    return f"{label}: {_quote_time_signals(_quote_question_terms(_ensure_term_in_reason(term, clean or body), context))}"


def _clean_option_body(body: Any) -> str:
    text = _compact(body)
    text = re.sub(r"^(?:Sai|Đúng|Dúng|Đáp án đúng|Dap an dung|Correct|Wrong)\s*[:.。-]?\s*", "", text, flags=re.IGNORECASE)
    return _ensure_sentence(text) if text else ""


def _ensure_term_in_reason(term: str, reason: str) -> str:
    clean = _ensure_sentence(reason)
    if not term:
        return _lower_first(clean)
    if normalize_text(term) in normalize_text(clean):
        return _lower_first(clean)
    return f"“{term}” {_lower_first(clean)}"


def _quote_question_terms(reason: str, context: dict[str, Any]) -> str:
    text = reason
    for term in _blank_neighbor_terms(context):
        text = re.sub(rf"(?<![“\"A-Za-z]){re.escape(term)}(?![”\"A-Za-z])", f"“{term}”", text)
    return text


def _quote_time_signals(value: str) -> str:
    text = value
    text = re.sub(
        r"(dấu\s+hiệu\s+thời\s+gian|dau\s+hieu\s+thoi\s+gian)\s+[\"“”]?(?P<signal>next\s+\w+|last\s+\w+|yesterday|tomorrow|usually|often|already)(?![”\"])",
        lambda match: f"{match.group(1)} “{match.group('signal')}”",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _blank_neighbor_terms(context: dict[str, Any]) -> list[str]:
    question = str(context.get("question_text") or context.get("question_text_en") or "")
    match = re.search(r"([A-Za-z][A-Za-z'-]*)?\s*_{2,}\s*([A-Za-z][A-Za-z'-]*)?", question)
    if not match:
        return []
    return [term for term in (match.group(1), match.group(2)) if term and normalize_text(term) not in {"the", "a", "an"}]


def _lower_first(value: str) -> str:
    text = str(value or "").strip()
    return text[:1].lower() + text[1:] if text else text


def _field_for_context_value(context: dict[str, Any], value: Any) -> str:
    for key, field in [
        ("explanation_detail", "ExplanationDetail"),
        ("explanation", "ExplanationDetail"),
        ("option_analysis", "OptionAnalysis"),
        ("vocabulary_notes", "VocabularyNotes"),
        ("raw_block", "RawBlock"),
    ]:
        if value and context.get(key) == value:
            return field
    return ""


def _correct_phrase_sentence(context: dict[str, Any]) -> str:
    _label, answer = _correct_label_and_text(context)
    if not answer:
        return ""
    question = str(context.get("question_text") or context.get("question_text_en") or "")
    match = re.search(r"(?P<before>(?:[A-Za-z][A-Za-z'-]*\s+){0,4})_{2,}(?P<after>(?:\s+[A-Za-z][A-Za-z'-]*){0,4})", question)
    if not match:
        return ""
    before_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", match.group("before"))
    after_tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", match.group("after"))
    before = " ".join(before_tokens[-3:])
    after_limit = 1 if after_tokens and normalize_text(after_tokens[0]) in {"for", "to", "of", "in", "on", "with"} else 2
    after = " ".join(after_tokens[:after_limit])
    phrase = " ".join(part for part in (before, answer, after) if part).strip()
    if not phrase or len(phrase.split()) > 9:
        return ""
    return f"Cụm đúng là “{phrase}”."


def _format_correct_answer(context: dict[str, Any]) -> AnswerMatch:
    label = str(context.get("correct_option_label") or context.get("correct_option_key") or "").strip().upper()
    text = _strip_answer_label(context.get("correct_answer_text") or "")
    if not text:
        correct_answer = _compact(context.get("correct_answer"))
        match = re.match(r"^([A-D])\s*[.)—-]?\s*(.+)$", correct_answer, flags=re.IGNORECASE)
        if match and not re.match(r"^\s*[A-D]\s*(?:[.)]|[:\-]|—)", correct_answer, flags=re.IGNORECASE):
            match = None
        if match:
            label = label or match.group(1).upper()
            text = _strip_answer_label(match.group(2))
        elif correct_answer:
            text = _strip_answer_label(correct_answer)
    if not text and label:
        text = _option_text(label, context)
    if not label:
        for option in _get_options(context):
            if option.get("is_correct") is True:
                label = str(option.get("label") or "").strip().upper()
                text = text or _strip_answer_label(option.get("text"))
                break
    if label and text:
        return AnswerMatch(f"Đáp án đúng là {label} — {text}.", "CorrectOptionLabel/CorrectAnswerText", text, label, text)
    if text:
        return AnswerMatch(f"Đáp án đúng là {text}.", "CorrectAnswerText", text, label or None, text)
    return AnswerMatch()


def _format_full_option_analysis(context: dict[str, Any]) -> AnswerMatch:
    value = _compact(context.get("option_analysis"))
    if not value:
        return AnswerMatch()
    lines = []
    for label in ("A", "B", "C", "D"):
        entry = _parse_option_entry(value, label)
        if entry:
            term = entry.get("term") or _option_text(label, context)
            body = _clean_option_body(entry.get("body"))
            lines.append(f"{label}. {term}: {body}".strip())
    answer = "\n".join(lines) if lines else value
    return AnswerMatch(answer, "OptionAnalysis", "", None, answer[:240])


def _format_explanation(context: dict[str, Any]) -> AnswerMatch:
    correct = _format_correct_answer(context).text
    explanation = _compact(context.get("explanation_detail") or context.get("explanation"))
    if not explanation and not correct:
        return AnswerMatch()
    short_explanation = _truncate(explanation, 650)
    if correct and short_explanation:
        return AnswerMatch(f"{correct}\nGiải thích: {short_explanation}", "ExplanationDetail", "", None, short_explanation)
    if short_explanation:
        return AnswerMatch(_ensure_sentence(short_explanation), "ExplanationDetail", "", None, short_explanation)
    return AnswerMatch(correct, "CorrectOptionLabel/CorrectAnswerText", "", None, correct)


def _remove_answer_leaks(value: str, context: dict[str, Any]) -> str:
    text = value
    label = str(context.get("correct_option_label") or context.get("correct_option_key") or "").strip()
    answer = _strip_answer_label(context.get("correct_answer_text") or context.get("correct_answer") or "")
    if label:
        text = re.sub(rf"\b{re.escape(label)}\b", "", text)
    if answer:
        text = re.sub(re.escape(answer), "từ phù hợp", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _best_sentence_for_keywords(source: Any, keywords: tuple[str, ...]) -> str:
    best = ""
    best_score = 0
    for sentence in _split_sentences(source):
        normalized = normalize_text(sentence)
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score > best_score:
            best = sentence
            best_score = score
    return best


def _first_sentence(value: Any, limit: int = 220) -> str:
    sentences = _split_sentences(value)
    if not sentences:
        return ""
    return _truncate(sentences[0], limit)


def _truncate(value: Any, limit: int) -> str:
    text = _compact(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _quote(value: str) -> str:
    return f"“{value}”"
