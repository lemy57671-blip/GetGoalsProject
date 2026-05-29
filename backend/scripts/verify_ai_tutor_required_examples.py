from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import pydantic  # noqa: F401
except ModuleNotFoundError:
    import types

    schemas = types.ModuleType("app.schemas.chat")

    class _Dto:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    schemas.ChatContextBundle = _Dto
    schemas.ChatIntent = str
    schemas.ChatMessageDto = _Dto
    schemas.ChatResponse = _Dto
    schemas.IntentResult = _Dto
    sys.modules["app.schemas.chat"] = schemas

    local_provider = types.ModuleType("app.services.chat.local_algorithm_provider")
    local_provider.detect_intent = lambda message: "general"
    local_provider.extract_option_label = lambda message: None
    local_provider.extract_word_or_phrase = lambda message, *_args: ""
    sys.modules["app.services.chat.local_algorithm_provider"] = local_provider

from app.services.chat.answer_builder import build_tutor_answer  # noqa: E402
from app.services.chat.context_extractor import extract_tutor_context  # noqa: E402
from app.services.chat.intent_router import route_tutor_intent  # noqa: E402


QUESTION_CONTEXT = {
    "questionId": 999001,
    "questionText": "The crew members ____ the main section of the building by the time the waste removal trucks arrive at 3:30.",
    "options": [
        {"label": "A", "text": "demolish"},
        {"label": "B", "text": "will have demolished"},
        {"label": "C", "text": "demolished"},
        {"label": "D", "text": "had demolished"},
    ],
    "correctAnswer": "B",
    "explanation": "Cụm by the time ... arrive at 3:30 chỉ một thời điểm trong tương lai mà hành động sẽ hoàn tất trước đó. Vì vậy cần dùng thì tương lai hoàn thành will have + V3.",
    "rawBlock": """
Giải thích chi tiết:
Cụm by the time ... arrive at 3:30 chỉ một thời điểm trong tương lai mà hành động sẽ hoàn tất trước đó. Vì vậy cần dùng thì tương lai hoàn thành will have + V3.

Phân tích lựa chọn:
(A) demolish: Sai. Hiện tại đơn, không thể hiện hành động hoàn tất trước thời điểm tương lai.
(B) will have demolished: Đáp án đúng. Nghĩa là sẽ đã phá dỡ xong.
(C) demolished: Sai. Quá khứ đơn.
(D) had demolished: Sai. Quá khứ hoàn thành, không phù hợp với mốc tương lai.

Cấu trúc và từ vựng mở rộng:
will have + V3 by the time + S + V: sẽ đã làm xong gì trước khi...
by the time: trước khi / đến lúc mà

Bản dịch tiếng Việt:
Các thành viên đội thi công sẽ phá dỡ xong phần chính của tòa nhà trước khi xe chở rác đến lúc 3:30.
""",
}


CASES = [
    (
        "thi gi",
        "tense_requirement",
        ("will have + V3", "by the time the waste removal trucks arrive at 3:30", "B. will have demolished"),
        (),
    ),
    (
        "day la thi gi",
        "tense_requirement",
        ("will have + V3", "B. will have demolished"),
        (),
    ),
    (
        "can thi j",
        "tense_requirement",
        ("will have + V3", "B. will have demolished"),
        (),
    ),
    (
        "tense gi",
        "tense_requirement",
        ("will have + V3", "B. will have demolished"),
        (),
    ),
    (
        "cau truc gi",
        "grammar_formula",
        ("will have + V3", "by the time the waste removal trucks arrive at 3:30"),
        (),
    ),
    (
        "ct gi",
        "grammar_formula",
        ("will have + V3",),
        (),
    ),
    (
        "sau by the time dung gi",
        "grammar_explanation",
        ("will have + V3", "by the time the waste removal trucks arrive at 3:30"),
        (),
    ),
    (
        "dap an sai",
        "wrong_options_analysis",
        ("A. demolish", "C. demolished", "D. had demolished", "B. will have demolished"),
        ("No explanation is available",),
    ),
    (
        "dap an sai la gi",
        "wrong_options_analysis",
        ("A. demolish", "C. demolished", "D. had demolished", "B. will have demolished"),
        ("No explanation is available",),
    ),
    (
        "cac dap an sai tai sao",
        "wrong_options_analysis",
        ("A. demolish", "C. demolished", "D. had demolished", "B. will have demolished"),
        (),
    ),
    (
        "may cai kia sai sao",
        "wrong_options_analysis",
        ("A. demolish", "C. demolished", "D. had demolished", "B. will have demolished"),
        (),
    ),
    (
        "A sai sao",
        "option_reason",
        ("A. demolish sai", "B. will have demolished"),
        ("C. demolished", "D. had demolished"),
    ),
    (
        "hint",
        "hint",
        ("by the time the waste removal trucks arrive at 3:30",),
        ("B.", "will have demolished"),
    ),
    (
        "dau hieu dau",
        "signal",
        ("by the time the waste removal trucks arrive at 3:30",),
        ("B. will have demolished",),
    ),
    (
        "sao vay",
        "explanation",
        ("will have + V3", "B. will have demolished"),
        ("A. demolish: Sai", "C. demolished: Sai", "D. had demolished: Sai"),
    ),
    (
        "khong hieu",
        "explanation_simplify",
        ("will have + V3", "B. will have demolished"),
        ("A. demolish: Sai", "C. demolished: Sai", "D. had demolished: Sai"),
    ),
    (
        "noi de hieu hon",
        "explanation_simplify",
        ("will have + V3", "B. will have demolished"),
        ("A. demolish: Sai", "C. demolished: Sai", "D. had demolished: Sai"),
    ),
    (
        "giai ky",
        "full_option_analysis",
        ("A. demolish", "B. will have demolished", "C. demolished", "D. had demolished"),
        (),
    ),
    (
        "A nghia la gi",
        "option_translation",
        ("A. demolish",),
        ("No explanation is available",),
    ),
    (
        "cai nay la gi",
        "explanation",
        ("will have + V3", "B. will have demolished"),
        ("No explanation is available",),
    ),
    (
        "chỗ trống cần thì gì",
        "tense_requirement",
        ("Chỗ trống cần thì tương lai hoàn thành", "will have + V3", "by the time + S + V hiện tại đơn", "B. will have demolished"),
        (),
    ),
    (
        "tại sao A sai",
        "option_reason",
        ("A. demolish sai", "hiện tại đơn", "by the time the waste removal trucks arrive at 3:30", "will have + V3", "B. will have demolished"),
        ("C. demolished", "D. had demolished"),
    ),
    (
        "demolish sai ở đâu",
        "option_reason",
        ("\"demolish\" là option A", "hiện tại đơn", "will have + V3", "B. will have demolished"),
        ("C. demolished", "D. had demolished"),
    ),
    (
        "tại sao B đúng",
        "option_reason",
        ("B. will have demolished đúng", "thì tương lai hoàn thành", "will have + V3", "sẽ đã phá dỡ xong"),
        ("A. demolish sai", "C. demolished sai", "D. had demolished sai"),
    ),
    (
        "tại sao C sai",
        "option_reason",
        ("C. demolished sai", "quá khứ đơn", "mốc tương lai", "will have + V3", "B. will have demolished"),
        ("A. demolish sai", "D. had demolished sai"),
    ),
    (
        "tại sao D sai",
        "option_reason",
        ("D. had demolished sai", "quá khứ hoàn thành", "mốc tương lai", "will have + V3", "B. will have demolished"),
        ("A. demolish sai", "C. demolished sai"),
    ),
    (
        "tại sao mấy cái kia sai",
        "wrong_options_analysis",
        ("Các đáp án còn lại sai", "A. demolish", "C. demolished", "D. had demolished", "B. will have demolished"),
        (),
    ),
    (
        "by the time là gì",
        "vocabulary_meaning",
        ("\"By the time\" nghĩa là", "trước khi / đến lúc mà", "by the time the waste removal trucks arrive at 3:30", "will have + V3"),
        ("Đáp án đúng",),
    ),
    (
        "dịch câu này",
        "translation",
        ("Các thành viên đội thi công sẽ phá dỡ xong phần chính của tòa nhà trước khi xe chở rác đến lúc 3:30.",),
        ("will have + V3",),
    ),
    (
        "hint thôi đừng nói đáp án",
        "hint",
        ("Gợi ý", "by the time the waste removal trucks arrive at 3:30", "sẽ đã làm xong"),
        ("Đáp án", "B.", "will have demolished"),
    ),
    (
        "phân tích từng đáp án",
        "full_option_analysis",
        ("A. demolish", "B. will have demolished", "C. demolished", "D. had demolished"),
        (),
    ),
    (
        "câu này làm sao",
        "how_to_solve",
        ("by the time the waste removal trucks arrive at 3:30", "tương lai hoàn thành", "will have + V3", "B. will have demolished"),
        ("A. demolish: Sai", "C. demolished: Sai", "D. had demolished: Sai"),
    ),
    (
        "có phải B không",
        "correct_answer_check",
        ("Đúng", "B. will have demolished", "by the time the waste removal trucks arrive at 3:30"),
        (),
    ),
    (
        "B với D khác gì",
        "compare_options",
        ("B. will have demolished", "D. had demolished", "mốc tương lai"),
        ("A. demolish", "C. demolished"),
    ),
    (
        "will have demolished khác had demolished sao",
        "compare_options",
        ("B. will have demolished", "D. had demolished", "mốc tương lai"),
        ("A. demolish", "C. demolished"),
    ),
    (
        "chỉ dấu hiệu thôi",
        "hint",
        ("Gợi ý", "by the time the waste removal trucks arrive at 3:30"),
        ("Đáp án", "B.", "will have demolished"),
    ),
    (
        "will have V3 là gì",
        "grammar_formula",
        ("thì tương lai hoàn thành", "will have + V3"),
        (),
    ),
]


def main() -> int:
    ctx = extract_tutor_context(QUESTION_CONTEXT)
    failures: list[str] = []
    for message, expected_intent, required, forbidden in CASES:
        intent = route_tutor_intent(message, ctx)
        answer = build_tutor_answer(intent, ctx)
        text = answer.answer if answer else ""
        if intent.intent != expected_intent:
            failures.append(f"{message}: expected intent {expected_intent}, got {intent.intent}")
        for fragment in required:
            if fragment not in text:
                failures.append(f"{message}: missing fragment {fragment!r}\n{text}")
        for fragment in forbidden:
            if fragment in text:
                failures.append(f"{message}: forbidden fragment {fragment!r}\n{text}")
        if "No explanation is available" in text or "sai vì sai" in text:
            failures.append(f"{message}: weak fallback leaked\n{text}")
        if not text:
            failures.append(f"{message}: empty answer")

    if failures:
        print("\n\n".join(failures))
        return 1
    print("All required AI Tutor example checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
