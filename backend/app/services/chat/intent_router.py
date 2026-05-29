from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from app.schemas.chat import ChatIntent, IntentResult
from app.services.chat.context_extractor import TutorContext, normalize_text
from app.services.chat.local_algorithm_provider import detect_intent, extract_option_label, extract_word_or_phrase


@dataclass
class TutorIntentResult:
    intent: str
    normalized_message: str
    target_option: str | None = None
    target_option_text: str | None = None
    target_text: str | None = None
    confidence: float = 0.9
    target_options: tuple[str, ...] = field(default_factory=tuple)


TEENCODE_TOKEN_MAP = {
    "k": "khong",
    "ko": "khong",
    "kh": "khong",
    "kg": "khong",
    "hok": "khong",
    "hong": "khong",
    "hông": "khong",
    "dc": "duoc",
    "đc": "duoc",
    "j": "gi",
    "z": "vay",
    "zay": "vay",
    "vay": "vay",
    "lm": "lam",
    "lms": "lam sao",
    "ntn": "nhu the nao",
    "gt": "giai thich",
    "gthich": "giai thich",
    "gthik": "giai thich",
    "da": "dap an",
    "ans": "dap an",
    "dapan": "dap an",
    "trans": "dich",
    "mean": "nghia",
    "cauu": "cau",
    "chon": "chon",
    "blank": "cho trong",
    "tsao": "tai sao",
    "vsao": "vi sao",
    "s": "sao",
    "saii": "sai",
    "dungg": "dung",
    "thigif": "thi gi",
    "ct": "cong thuc",
    "congthuc": "cong thuc",
    "cautruc": "cau truc",
    "nguphap": "ngu phap",
    "loaitu": "loai tu",
    "dangtu": "dang tu",
    "goiy": "goi y",
    "keyword": "keyword",
    "clue": "clue",
}

PHRASE_REPLACEMENTS = (
    (r"\bt\s+sao\b", "tai sao"),
    (r"\btai\s+s\b", "tai sao"),
    (r"\bvi\s+s\b", "vi sao"),
    (r"\blam\s+s\b", "lam sao"),
    (r"\bcau\s+nay\s+lam\s+s\b", "cau nay lam sao"),
    (r"\bcho\s+trong\b", "cho trong"),
    (r"\bdap\s+an\b", "dap an"),
    (r"\bcau\s+truc\b", "cau truc"),
    (r"\bcong\s+thuc\b", "cong thuc"),
    (r"\bngu\s+phap\b", "ngu phap"),
    (r"\bloai\s+tu\b", "loai tu"),
    (r"\bdang\s+tu\b", "dang tu"),
    (r"\bgoi\s+y\b", "goi y"),
)


def normalize_user_message(value: Any) -> str:
    text_value = str(value or "").strip().lower()
    text_value = unicodedata.normalize("NFD", text_value)
    text_value = "".join(char for char in text_value if unicodedata.category(char) != "Mn")
    text_value = text_value.replace("đ", "d")
    text_value = re.sub(r"([a-z])\1{2,}", r"\1", text_value)
    text_value = re.sub(r"[^a-z0-9\s/+']", " ", text_value)

    tokens: list[str] = []
    for token in re.sub(r"\s+", " ", text_value).strip().split():
        replacement = TEENCODE_TOKEN_MAP.get(token, token)
        tokens.extend(replacement.split())

    normalized = re.sub(r"\s+", " ", " ".join(tokens)).strip()
    for pattern, replacement in PHRASE_REPLACEMENTS:
        normalized = re.sub(pattern, replacement, normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_any(text_value: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text_value for phrase in phrases)


def _fuzzy_contains(text_value: str, phrase: str, threshold: float = 0.86) -> bool:
    if phrase in text_value:
        return True
    tokens = text_value.split()
    phrase_tokens = phrase.split()
    if not tokens or not phrase_tokens:
        return False
    min_size = max(1, len(phrase_tokens) - 1)
    max_size = min(len(tokens), len(phrase_tokens) + 1)
    for size in range(min_size, max_size + 1):
        for start in range(0, len(tokens) - size + 1):
            window = " ".join(tokens[start : start + size])
            if SequenceMatcher(None, window, phrase).ratio() >= threshold:
                return True
    return False


def _has_phrase(text_value: str, *phrases: str) -> bool:
    return any(_fuzzy_contains(text_value, phrase) for phrase in phrases)


def _option_by_label(context: TutorContext | None, label: str | None):
    if not context or not label:
        return None
    wanted = label.strip().upper()
    return next((option for option in context.options if option.label == wanted), None)


def _extract_option_label(text_value: str) -> str | None:
    patterns = (
        r"\b(?:co\s+phai|phai|is\s+it)\s+([abcd])\b",
        r"\bdap\s+an\s+(?:la\s+)?([abcd])\b",
        r"\b(?:option|opt|dap an|lua chon|chon)\s*([abcd])\b",
        r"\b(?:vi sao|tai sao|sao|why|giai thich|phan tich)\s+([abcd])\b",
        r"\b([abcd])\s+(?:nghia|dich)\b",
        r"\b([abcd])\s*(?:sai|dung|wrong|correct|khong|cho nao|o dau|vay|ha|hong|ok)\b",
        r"\b([abcd])\s+(?:la|co phai|phai)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text_value, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    if re.fullmatch(r"[abcd]", text_value):
        return text_value.upper()
    return None


def _extract_option_text_matches(text_value: str, context: TutorContext | None):
    if not context:
        return []
    matches = []
    for option in sorted(context.options, key=lambda item: len(item.text), reverse=True):
        option_norm = normalize_user_message(option.text)
        if option_norm and re.search(rf"\b{re.escape(option_norm)}\b", text_value):
            matches.append(option)
    return matches


def _extract_option_text_match(text_value: str, context: TutorContext | None):
    matches = _extract_option_text_matches(text_value, context)
    return matches[0] if matches else None


def _mentioned_labels(text_value: str) -> set[str]:
    return {match.group(1).upper() for match in re.finditer(r"\b([abcd])\b", text_value)}


def _extract_compare_labels(text_value: str, context: TutorContext | None) -> tuple[str, ...]:
    labels: list[str] = []
    for match in re.finditer(r"\b([abcd])\b", text_value):
        label = match.group(1).upper()
        if label not in labels:
            labels.append(label)
    for option in _extract_option_text_matches(text_value, context):
        if option.label not in labels:
            labels.append(option.label)
    return tuple(labels[:2])


def _extract_vocab_target(message: str, normalized: str) -> str:
    del message
    patterns = (
        r"^(?P<target>.+?)\s+(?:nghia\s+la\s+gi|nghia\s+sao|nghia\s+gi|la\s+gi|dich\s+sao)\b",
        r"^what\s+does\s+(?P<target>.+?)\s+mean\b",
        r"^dich\s+(?:phan\s+)?(?P<target>.+)$",
        r"^translate\s+(?P<target>.+)$",
    )
    ignored = {
        "",
        "nay",
        "day",
        "do",
        "cai nay",
        "tu nay",
        "cum nay",
        "phrase nay",
        "word nay",
        "cau nay",
        "doan nay",
        "dap an",
        "answer",
        "correct answer",
    }
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        target = match.group("target").strip(" \"'?.!,")
        target = re.sub(r"^(?:tu|cum|phrase|phan|dap an)\s+", "", target).strip()
        if target not in ignored:
            return target
    return ""


def _is_tense_requirement(text_value: str) -> bool:
    return bool(
        "tense" in text_value
        or re.search(r"\b(?:what|which)\s+tense\b", text_value)
        or re.search(r"\bthi\s+(?:gi|nao)\b", text_value)
        or re.search(r"\b(?:day|nay|cau nay|cai nay)\s+(?:la\s+)?thi\s+gi\b", text_value)
        or re.search(r"\b(?:can|dung|can dung)\s+thi\s+(?:gi|nao)\b", text_value)
        or "cho trong can thi gi" in text_value
        or "blank can thi gi" in text_value
        or "can dung tense nao" in text_value
        or re.search(r"\b(?:will have v3|will have \+ v3|had v3|v2|v3)\s+(?:la\s+)?thi\s+gi\b", text_value)
        or re.search(r"\bco phai\s+(?:tuong lai hoan thanh|qua khu hoan thanh|future perfect|past perfect)\s+(?:khong|ha|hong)?\b", text_value)
        or re.search(r"\b(?:sao|vi sao|tai sao)\s+dung\s+thi\s+nay\b", text_value)
        or "thi nay dung sao" in text_value
    )


def _is_word_form_requirement(text_value: str) -> bool:
    return bool(
        _contains_any(
            text_value,
            (
                "loai tu gi",
                "can loai tu",
                "cho trong can loai tu",
                "tu loai",
                "word form",
                "part of speech",
                "dang tu gi",
                "dien loai tu nao",
                "danh tu hay dong tu",
                "tinh tu hay trang tu",
                "noun verb adj adv",
                "can noun",
                "can verb",
                "can adj",
                "can adv",
            ),
        )
        or re.search(r"\b(?:cai nay|tu nay|option nay|dap an nay)\s+la\s+(?:noun|verb|adj|adv|danh tu|dong tu|tinh tu|trang tu)\s+(?:ha|khong|hong)?\b", text_value)
        or re.search(r"\b[a-z][a-z'\-]*\s+la\s+loai\s+tu\s+gi\b", text_value)
    )


def _is_grammar_explanation(text_value: str) -> bool:
    return bool(
        _contains_any(
            text_value,
            (
                "tai sao arrive",
                "vi sao arrive",
                "sao arrive khong chia will",
                "tai sao dung v3",
                "sao dung v3",
                "tai sao dung qua khu phan tu",
                "vi sao khong dung past perfect",
                "sao khong dung hien tai don",
                "tai sao la hien tai don",
                "tai sao la danh tu",
                "tai sao la dong tu",
                "sau by the time dung gi",
                "sau tu nay dung gi",
                "sau preposition dung gi",
            ),
        )
        or re.search(r"\bsau\s+[a-z][a-z'\-\s]{0,40}\s+dung\s+gi\b", text_value)
        or re.search(r"\b(?:sao|vi sao|tai sao)\s+dung\s+(?:ving|to v|noun|adj|adv|v3)\b", text_value)
    )


def _is_grammar_formula(text_value: str) -> bool:
    return bool(
        _contains_any(
            text_value,
            (
                "cau truc gi",
                "day la cau truc gi",
                "cau nay cau truc gi",
                "cong thuc gi",
                "formula gi",
                "grammar gi",
                "ngu phap gi",
                "day la ngu phap gi",
                "cau nay test ngu phap gi",
                "thuoc ngu phap",
                "by the time dung sao",
                "will have v3",
                "will have + v3",
                "had v3",
                "v3 la gi",
                "v2 la gi",
                "future perfect",
                "past perfect",
            ),
        )
    )


def _is_translation_request(text_value: str) -> bool:
    return bool(
        text_value in {"dich", "translate", "translate this"}
        or _contains_any(
            text_value,
            (
                "dich cau nay",
                "dich doan nay",
                "dich de",
                "chuyen sang tieng viet",
                "noi tieng viet",
                "translate this sentence",
                "translate the sentence",
                "cau nay nghia gi",
            ),
        )
    )


def _is_hint_request(text_value: str) -> bool:
    return bool(
        _contains_any(
            text_value,
            (
                "hint",
                "goi y",
                "dung noi dap an",
                "goi y thoi",
                "chi goi y",
                "chi dau hieu thoi",
                "cho tui tu lam",
                "cho toi tu lam",
                "noi nhe thoi",
                "cho clue thoi",
                "clue thoi",
                "chi clue thoi",
            ),
        )
    )


def _is_signal_request(text_value: str) -> bool:
    return bool(
        _contains_any(
            text_value,
            (
                "keyword",
                "dau hieu",
                "clue",
                "signal",
                "nhin cho nao",
                "nen nhin cho nao",
                "nhin dau",
                "dua vao dau",
                "can cu vao dau",
                "cho nao cho biet",
                "tu nao la dau hieu",
            ),
        )
    )


def _is_full_analysis_request(text_value: str) -> bool:
    return bool(
        _contains_any(
            text_value,
            (
                "phan tich tung dap an",
                "phan tich lua chon",
                "giai thich a b c d",
                "giai thich abcd",
                "giai het options",
                "giai het",
                "full loi giai",
                "giai ky",
                "phan tich chi tiet",
                "lam bai nay chi tiet",
                "giai nhu giao vien",
                "cho loi giai day du",
                "xem phan tich lua chon",
            ),
        )
    )


def _is_wrong_options_request(text_value: str) -> bool:
    return bool(
        _contains_any(
            text_value,
            (
                "dap an sai",
                "cac dap an sai",
                "may dap an sai",
                "may cai kia",
                "may cai sai",
                "cac cai sai",
                "dap an nao sai",
                "option nao sai",
                "wrong options",
                "which options are wrong",
                "why wrong options",
                "why are other options wrong",
                "dap an con lai sai",
                "cac dap an con lai sai",
                "cac dap an khac sai",
                "vi sao may dap an khac sai",
                "cau sai thoi",
                "cac cau sai thoi",
                "may cau kia sai",
            ),
        )
    )


def _is_explanation_simplify_request(text_value: str) -> bool:
    return bool(
        _contains_any(
            text_value,
            (
                "khong hieu",
                "chua hieu",
                "noi ro hon",
                "noi lai",
                "noi de hieu",
                "noi de hieu hon",
                "giai thich them",
                "giai thich don gian",
                "simplify",
                "con gi nua",
                "tiep di",
            ),
        )
    )


def _is_answer_check(text_value: str) -> bool:
    return bool(
        re.search(r"\b(?:co\s+phai|phai)\s+.+\s+(?:khong|ha|hong|ko|k)\b", text_value)
        or re.search(r"\b(?:is\s+it)\s+[abcd]\b", text_value)
        or re.search(r"\b[abcd]\s+dung\s+(?:khong|ha|hong|ko|k)\b", text_value)
        or re.search(r"\bdap an\s+la\s+[abcd]\s+(?:ha|khong|ko|k)\b", text_value)
    )


def _result(
    intent: str,
    normalized: str,
    label: str | None,
    option_text: str | None,
    target_text: str | None,
    confidence: float,
    target_options: tuple[str, ...] = (),
) -> TutorIntentResult:
    return TutorIntentResult(intent, normalized, label, option_text, target_text, confidence, target_options)


def route_tutor_intent(message: str, context: TutorContext | None = None) -> TutorIntentResult:
    normalized = normalize_user_message(message)
    label = _extract_option_label(normalized)
    option = _option_by_label(context, label) or _extract_option_text_match(normalized, context)
    if option:
        label = option.label
    target_text = _extract_vocab_target(message, normalized)
    labels = _mentioned_labels(normalized)
    compare_labels = _extract_compare_labels(normalized, context)
    option_text = option.text if option else None

    selected_self = bool(
        re.search(r"\b(?:toi|tui|minh|em|mk|m)\s+(?:chon|pick|selected)\s+[abcd]\b", normalized)
        or re.search(r"\b(?:toi|tui|minh|em|mk|m)\s+chon\s+.+\s+(?:sai|dung)\b", normalized)
        or re.search(r"\b(?:sao|vi sao|tai sao)\s+(?:toi|tui|minh|em|mk|m)\s+sai\b", normalized)
        or _contains_any(
            normalized,
            (
                "dap an em chon sai",
                "dap an minh chon sai",
                "dap an toi chon sai",
                "dap an tui chon sai",
                "sao toi sai",
                "minh sai gi",
                "tui sai dau",
                "why am i wrong",
                "my answer wrong why",
            ),
        )
        or (not option and _contains_any(normalized, ("sai cho nao", "sao toi sai")))
    )

    if selected_self:
        return _result("selected_wrong_reason", normalized, label, option_text, target_text, 0.97)
    if len(compare_labels) >= 2 or _contains_any(normalized, ("so sanh", "khac gi", "khac nhau", "phan biet")):
        first = compare_labels[0] if compare_labels else label
        first_option = _option_by_label(context, first)
        return _result("compare_options", normalized, first, first_option.text if first_option else option_text, target_text, 0.94, compare_labels)
    if option and (
        _contains_any(normalized, ("sai", "khong chon", "khong dung", "wrong", "vi sao", "tai sao", "sao", "cho nao", "o dau", "dung cho nao", "dung sao"))
        or re.search(r"\b(?:dung|correct)\b", normalized)
    ):
        return _result("option_reason", normalized, label, option_text, target_text, 0.98)
    if option and _is_answer_check(normalized) and not _contains_any(normalized, ("vi sao", "tai sao", "sao lai", "why")):
        return _result("correct_answer_check", normalized, label, option_text, target_text, 0.94)
    if _is_hint_request(normalized):
        return _result("hint", normalized, label, option_text, target_text, 0.96)
    if _is_tense_requirement(normalized):
        return _result("tense_requirement", normalized, label, option_text, target_text, 0.98)
    if _is_word_form_requirement(normalized):
        return _result("word_form_requirement", normalized, label, option_text, target_text, 0.95)
    if _is_grammar_explanation(normalized):
        return _result("grammar_explanation", normalized, label, option_text, target_text, 0.92)
    if _is_grammar_formula(normalized):
        grammar_target = normalize_text(target_text)
        if target_text and "nghia" in normalized and grammar_target not in {"will have v3", "will have + v3"}:
            return _result("vocabulary_meaning", normalized, label, option_text, target_text, 0.94)
        return _result("grammar_formula", normalized, label, option_text, target_text, 0.93)
    if option and _contains_any(normalized, ("dich", "translate", "nghia sao", "nghia gi", "nghia la gi", "la gi")):
        return _result("option_translation", normalized, label, option_text, target_text, 0.94)
    if target_text and _contains_any(normalized, ("dich", "translate")):
        return _result("translation_piece", normalized, label, option_text, target_text, 0.94)
    if _is_translation_request(normalized):
        return _result("translation", normalized, label, option_text, target_text, 0.94)
    if _is_signal_request(normalized):
        return _result("signal", normalized, label, option_text, target_text, 0.91)
    if _is_full_analysis_request(normalized):
        return _result("full_option_analysis", normalized, label, option_text, target_text, 0.95)
    if _is_wrong_options_request(normalized):
        return _result("wrong_options_analysis", normalized, label, option_text, target_text, 0.95)
    if target_text or _contains_any(normalized, ("tu nay nghia", "cum nay nghia", "phrase nay", "word nay", "nghia la gi", "what does", "mean")):
        return _result("vocabulary_meaning", normalized, label, option_text, target_text, 0.92)
    if _contains_any(normalized, ("cau nay lam sao", "cau nay lam kieu gi", "cach lam", "chi tui cach lam", "huong giai", "bat dau tu dau", "lam sao", "giai cau nay")):
        return _result("how_to_solve", normalized, label, option_text, target_text, 0.9)
    if _contains_any(normalized, ("vi sao no dung", "sao lai dung", "dap an dung vi sao", "sao lai chon", "tai sao dap an dung")):
        return _result("why_correct", normalized, label, option_text, target_text, 0.9)
    if _is_answer_check(normalized) or _contains_any(normalized, ("dung khong", "co dung khong", "kiem tra dap an")):
        return _result("correct_answer_check", normalized, label, option_text, target_text, 0.86)
    if _contains_any(normalized, ("dap an la gi", "dap an dau", "dap an dung la cau nao", "chon gi", "chon dum", "chon gi vay", "answer", "correct answer")):
        return _result("correct_answer", normalized, label, option_text, target_text, 0.92)
    if _contains_any(normalized, ("bay", "trap", "de nham", "distractor")):
        return _result("trap_explanation", normalized, label, option_text, target_text, 0.91)
    if _contains_any(normalized, ("test gi", "kiem tra gi", "trong tam", "tested point", "bai nay test")):
        return _result("tested_point", normalized, label, option_text, target_text, 0.86)
    if _contains_any(normalized, ("ngan gon", "tom tat loi giai", "short explanation")):
        return _result("explanation_short", normalized, label, option_text, target_text, 0.84)
    if _contains_any(normalized, ("cho vi du", "vi du khac", "example")):
        return _result("example_request", normalized, label, option_text, target_text, 0.84)
    if _is_explanation_simplify_request(normalized):
        return _result("explanation_simplify", normalized, label, option_text, target_text, 0.84)
    if _contains_any(normalized, ("giai thich", "vi sao", "tai sao", "sao vay", "la sao", "cai nay la gi", "day la gi", "nay la gi", "why", "explain")) or normalized in {"ha", "sao", "vi sao", "tai sao", "why"}:
        return _result("explanation", normalized, label, option_text, target_text, 0.82)
    if _has_phrase(normalized, "dap an la gi", "cau nay lam sao", "cho trong can thi gi"):
        return _result("explanation", normalized, label, option_text, target_text, 0.78)
    return _result("general", normalized, label, option_text, target_text, 0.7)


class IntentRouter:
    grammar_signals = (
        "grammar",
        "ngu phap",
        "cau truc",
        "tense",
        "part of speech",
        "why is",
        "vi sao",
        "giai thich",
        "explain",
    )
    vocabulary_signals = (
        "vocabulary",
        "word",
        "phrase",
        "idiom",
        "meaning",
        "mean",
        "tu vung",
        "nghia",
        "cum tu",
    )
    translate_signals = (
        "translate",
        "translation",
        "dich",
        "sang tieng anh",
        "sang tieng viet",
    )
    fix_sentence_signals = (
        "fix",
        "correct",
        "rewrite",
        "natural",
        "sua cau",
        "sua loi",
        "dung khong",
        "check my sentence",
    )
    example_signals = (
        "example",
        "examples",
        "practice sentence",
        "similar",
        "tuong tu",
        "vi du",
        "luyen them",
    )
    study_plan_signals = (
        "study plan",
        "roadmap",
        "schedule",
        "plan",
        "ke hoach",
        "lo trinh",
        "hoc nhu the nao",
    )
    weak_skill_signals = (
        "weak",
        "weakness",
        "analyze my mistakes",
        "loi sai",
        "diem yeu",
        "ky nang yeu",
        "phan tich loi",
    )
    mock_test_signals = (
        "mock test",
        "full test",
        "test result",
        "review my test",
        "de thi",
        "bai test",
    )
    weekly_signals = (
        "weekly check",
        "this week",
        "tuan nay",
        "kiem tra tuan",
    )

    def classify(
        self,
        message: str,
        context_type: str | None = None,
        question_id: int | None = None,
        attempt_id: int | None = None,
    ) -> IntentResult:
        normalized = self._normalize(message)
        context = self._normalize(context_type or "")
        target_text = self._extract_target_text(message)

        if question_id or "practice_runner" in context or "practice_review" in context or "review" in context:
            local_intent = detect_intent(message)
            return self._result(
                local_intent,
                0.95 if local_intent != "general" else 0.72,
                "Detected local TOEIC question intent.",
                extract_word_or_phrase(message, [], "") or target_text,
                extract_option_label(message),
            )

        vocabulary_lookup = self._extract_vocabulary_lookup(message)
        if vocabulary_lookup["target_text"] or vocabulary_lookup["target_option_label"]:
            return self._result(
                "word_meaning",
                0.96,
                "Detected direct vocabulary definition request.",
                vocabulary_lookup["target_text"],
                vocabulary_lookup["target_option_label"],
            )

        if "weekly" in context or self._has_signal(normalized, self.weekly_signals):
            return self._result("weekly_check_advice", 0.9, "Detected weekly-check advice request.", target_text)
        if "mock" in context or self._has_signal(normalized, self.mock_test_signals):
            return self._result("mock_test_review", 0.9, "Detected mock-test review request.", target_text)
        if "weak" in context or self._has_signal(normalized, self.weak_skill_signals):
            return self._result("weak_skill_analysis", 0.88, "Detected weak-skill analysis request.", target_text)
        if "roadmap" in context or self._has_signal(normalized, self.study_plan_signals):
            return self._result("study_plan", 0.86, "Detected study-plan request.", target_text)
        if question_id or "question" in context or "review" in context:
            return self._result("explain_question", 0.92, "Question context was supplied.", target_text)
        if attempt_id and ("practice" in context or "attempt" in context):
            return self._result("mock_test_review", 0.82, "Attempt context was supplied.", target_text)
        if self._has_signal(normalized, self.translate_signals):
            return self._result("translate", 0.94, "Detected translation wording.", target_text)
        if self._has_signal(normalized, self.fix_sentence_signals) or self._looks_like_standalone_sentence(message):
            return self._result("fix_sentence", 0.88, "Detected sentence correction wording.", target_text)
        if self._has_signal(normalized, self.example_signals):
            return self._result("generate_examples", 0.84, "Detected example-generation request.", target_text)
        if self._has_signal(normalized, self.grammar_signals):
            return self._result("grammar_help", 0.82, "Detected grammar help request.", target_text)
        if self._has_signal(normalized, self.vocabulary_signals) or self._looks_like_short_term(message):
            return self._result("vocabulary_help", 0.8, "Detected vocabulary help request.", target_text)
        return self._result("general_chat", 0.72, "Defaulted to general TOEIC tutor chat.", target_text)

    def _result(
        self,
        intent: ChatIntent | str,
        confidence: float,
        reason: str,
        target_text: str | None,
        target_option_label: str | None = None,
    ) -> IntentResult:
        return IntentResult(
            intent=intent,
            confidence=confidence,
            reason=reason,
            target_text=target_text,
            target_option_label=target_option_label,
        )

    def _normalize(self, value: str) -> str:
        return normalize_user_message(value)

    def _has_signal(self, normalized: str, signals: tuple[str, ...]) -> bool:
        return any(signal in normalized for signal in signals)

    def _extract_target_text(self, message: str) -> str | None:
        quoted = re.findall(r"[\"']([^\"']+)[\"']", message)
        if quoted:
            return quoted[0].strip()
        if ":" in message:
            possible_target = message.split(":", 1)[1].strip()
            if possible_target:
                return possible_target
        return None

    def _extract_vocabulary_lookup(self, message: str) -> dict[str, str | None]:
        normalized = self._normalize(message)
        normalized = re.sub(r"[?!.]+$", "", normalized).strip()

        option_patterns = [
            r"\boption\s+([a-d])\s+(?:la\s+gi|nghia\s+la\s+gi|co\s+nghia\s+la\s+gi)\b",
            r"\b(?:dap\s+an|lua\s+chon)\s+([a-d])\s+(?:la\s+gi|nghia\s+la\s+gi|co\s+nghia\s+la\s+gi)\b",
            r"^([a-d])\s+(?:la\s+gi|nghia\s+la\s+gi|co\s+nghia\s+la\s+gi)$",
        ]
        for pattern in option_patterns:
            match = re.search(pattern, normalized)
            if match:
                return {"target_text": None, "target_option_label": match.group(1).upper()}

        term_patterns = [
            r"^(?:tu\s+)?([a-z][a-z'-]{0,})\s+(?:la\s+gi|nghia\s+la\s+gi|co\s+nghia\s+la\s+gi)$",
            r"^nghia\s+(?:cua|tu)\s+([a-z][a-z'-]{0,})$",
            r"^dich\s+(?:tu\s+)?([a-z][a-z'-]{0,})$",
            r"^what\s+does\s+([a-z][a-z'-]{0,})\s+mean$",
        ]
        for pattern in term_patterns:
            match = re.search(pattern, normalized)
            if match:
                return {"target_text": match.group(1).strip("'"), "target_option_label": None}

        return {"target_text": None, "target_option_label": None}

    def _looks_like_short_term(self, message: str) -> bool:
        text = message.strip()
        words = text.split()
        return "?" not in text and 1 <= len(words) <= 5

    def _looks_like_standalone_sentence(self, message: str) -> bool:
        text = message.strip().strip("'\"")
        words = text.split()
        if len(words) < 3 or "?" in text:
            return False
        first_word = re.sub(r"[^a-zA-Z]", "", words[0]).lower()
        return first_word in {"i", "you", "he", "she", "we", "they", "it"}
