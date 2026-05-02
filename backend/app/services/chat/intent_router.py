from __future__ import annotations

import re
import unicodedata

from app.schemas.chat import ChatIntent, IntentResult
from app.services.chat.local_algorithm_provider import detect_intent, extract_option_label, extract_word_or_phrase


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
        lowered = re.sub(r"\s+", " ", value.strip().lower())
        ascii_fallback = "".join(
            ch for ch in unicodedata.normalize("NFD", lowered) if unicodedata.category(ch) != "Mn"
        )
        ascii_fallback = ascii_fallback.replace("đ", "d")
        return f"{lowered} {ascii_fallback}"

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
