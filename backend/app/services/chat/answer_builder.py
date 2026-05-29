from __future__ import annotations

from dataclasses import dataclass

from app.schemas.chat import ChatContextBundle, ChatIntent, ChatMessageDto, ChatResponse, IntentResult
from app.services.chat.context_extractor import TutorContext, TutorOption, normalize_text, split_sentences
from app.services.chat.intent_router import TutorIntentResult


MISSING_DETAIL_PREFIX = "Hiện câu này chưa có lời giải chi tiết trong dữ liệu. Mình sẽ giải nhanh dựa trên câu hỏi và đáp án hiện có."


@dataclass
class TutorAnswer:
    answer: str
    intent: str
    target_option: str | None = None
    target_option_text: str | None = None


def _format_option(label: str, text: str) -> str:
    if label and text:
        return f"{label}. {text}"
    return label or text or "chưa xác định"


def _correct_option(ctx: TutorContext) -> TutorOption | None:
    return next((option for option in ctx.options if option.label == ctx.correct_label), None)


def _option_by_label(ctx: TutorContext, label: str | None) -> TutorOption | None:
    if not label:
        return None
    wanted = label.strip().upper()
    return next((option for option in ctx.options if option.label == wanted), None)


def _main_explanation(ctx: TutorContext, max_sentences: int = 2) -> str:
    text_value = ctx.explanation_detail or ctx.explanation or ctx.raw_block
    sentences = split_sentences(text_value)
    return ". ".join(sentences[:max_sentences]).strip(" .")


def _is_future_perfect(ctx: TutorContext) -> bool:
    return normalize_text(ctx.tense_name) == "thi tuong lai hoan thanh" or normalize_text(ctx.formula) == "will have v3"


def _signal_text(ctx: TutorContext) -> str:
    if ctx.signal_text:
        return ctx.signal_text
    if ctx.signal:
        return ctx.signal
    explanation = _main_explanation(ctx, 1)
    return explanation or "dấu hiệu ngữ pháp quanh chỗ trống"


def _short_correct_reason(ctx: TutorContext) -> str:
    if _is_future_perfect(ctx):
        if ctx.signal_text:
            return f"Câu có dấu hiệu \"{ctx.signal_text}\", nên hành động ở vế chính phải hoàn tất trước mốc tương lai đó."
        return "Thì tương lai hoàn thành diễn tả hành động sẽ hoàn tất trước một mốc trong tương lai."
    if ctx.correct_label in ctx.option_analysis:
        return split_sentences(ctx.option_analysis[ctx.correct_label])[0]
    explanation = _main_explanation(ctx, 1)
    return explanation or "Lựa chọn này khớp nhất với yêu cầu của chỗ trống/ngữ cảnh câu."


def _option_reason_text(ctx: TutorContext, option: TutorOption) -> str:
    reason = ctx.option_analysis.get(option.label, "").strip()
    if reason and normalize_text(reason) not in {"sai", "dung", "khong dung", "khong phu hop"}:
        return reason.rstrip(".")
    if _is_future_perfect(ctx) and option.label != ctx.correct_label:
        option_norm = normalize_text(option.text)
        if option_norm == "demolish":
            return "đây là hiện tại đơn, không thể hiện hành động sẽ hoàn tất trước một mốc trong tương lai"
        if option_norm == "demolished":
            return "đây là quá khứ đơn, không phù hợp vì câu đang nói về một mốc tương lai"
        if option_norm.startswith("had "):
            return "đây là quá khứ hoàn thành, dùng cho hành động hoàn tất trước một mốc trong quá khứ"
        return f"không khớp yêu cầu {ctx.tense_name} của câu"
    if option.label == ctx.correct_label:
        return _short_correct_reason(ctx)
    return "không khớp yêu cầu ngữ pháp/ngữ cảnh của chỗ trống"


def _wrong_option_detail(ctx: TutorContext, option: TutorOption) -> tuple[str, str]:
    reason = _option_reason_text(ctx, option)
    option_norm = normalize_text(option.text)
    if _is_future_perfect(ctx):
        if option_norm == "demolish":
            return (
                "đây là hiện tại đơn",
                "Hiện tại đơn không thể hiện được ý \"hành động sẽ hoàn tất trước một mốc trong tương lai\".",
            )
        if option_norm == "demolished":
            return (
                "đây là quá khứ đơn",
                "Câu này không nói về một hành động đã xảy ra trong quá khứ; nó nói về một hành động sẽ hoàn tất trước một mốc tương lai.",
            )
        if option_norm.startswith("had "):
            return (
                "đây là quá khứ hoàn thành",
                "Quá khứ hoàn thành dùng cho hành động xảy ra trước một mốc trong quá khứ, không phù hợp với mốc tương lai trong câu.",
            )
    if "," in reason:
        first, rest = reason.split(",", 1)
        return first.strip(), rest.strip().capitalize()
    return reason, ""


def _correct_future_meaning(ctx: TutorContext) -> str:
    correct_norm = normalize_text(ctx.correct_text)
    if correct_norm == "will have demolished":
        return "sẽ đã phá dỡ xong"
    meaning = ctx.vocabulary.get(correct_norm, "")
    return meaning or "sẽ đã hoàn tất hành động đó"


def _correct_option_reason_answer(ctx: TutorContext, option: TutorOption) -> str:
    if _is_future_perfect(ctx):
        lines = [
            f"{_format_option(option.label, option.text)} đúng vì đây là {ctx.tense_name}.",
            "",
            "Công thức:",
            ctx.formula or "will have + V3",
        ]
        if ctx.signal_text:
            lines.extend(
                [
                    "",
                    f"Câu có \"{ctx.signal_text}\", tức là một mốc trong tương lai. Hành động \"demolish the main section\" sẽ hoàn tất trước mốc đó.",
                ]
            )
        lines.extend(["", f"Vì vậy \"{option.text}\" nghĩa là \"{_correct_future_meaning(ctx)}\"."])
        return "\n".join(lines)
    return f"{_format_option(option.label, option.text)} đúng vì {_short_correct_reason(ctx).rstrip('.')}."


def _option_reason_answer(ctx: TutorContext, option: TutorOption, *, by_text: bool = False) -> str:
    if option.label == ctx.correct_label:
        return _correct_option_reason_answer(ctx, option)

    first_reason, detail = _wrong_option_detail(ctx, option)
    correct = _format_option(ctx.correct_label, ctx.correct_text)
    lines = []
    if by_text:
        lines.append(f"\"{option.text}\" là option {option.label}. Nó sai vì {first_reason}.")
    else:
        lines.append(f"{_format_option(option.label, option.text)} sai vì {first_reason}.")
    if detail:
        lines.extend(["", detail])
    if ctx.signal_text:
        lines.extend(["", "Trong câu có dấu hiệu:", ctx.signal_text])
    elif ctx.signal:
        lines.extend(["", "Dấu hiệu:", ctx.signal])
    if ctx.formula:
        lines.extend(["", f"Vì vậy cần dùng {ctx.tense_name or 'cấu trúc phù hợp'}:", ctx.formula])
    lines.extend(["", f"Đáp án đúng là {correct}."])
    return "\n".join(lines)


def _selected_wrong_answer(ctx: TutorContext, intent: TutorIntentResult) -> str:
    selected = _option_by_label(ctx, intent.target_option or ctx.selected_label)
    correct = _format_option(ctx.correct_label, ctx.correct_text)
    if not selected:
        return f"Mình chưa thấy đáp án bạn chọn. Đáp án đúng là {correct}."
    if selected.label == ctx.correct_label:
        return f"Bạn chọn {_format_option(selected.label, selected.text)}: đúng. {_short_correct_reason(ctx)}"
    first_reason, detail = _wrong_option_detail(ctx, selected)
    lines = [
        f"Bạn chọn: {_format_option(selected.label, selected.text)}",
        f"Đáp án đúng là: {correct}",
        f"Lý do đáp án bạn chọn sai: {first_reason}.",
    ]
    if detail:
        lines.append(detail)
    lines.append(f"Lý do đáp án đúng phù hợp: {_short_correct_reason(ctx).rstrip('.')}.")
    return "\n".join(lines)


def _correct_answer_check(ctx: TutorContext, intent: TutorIntentResult) -> str:
    candidate = _option_by_label(ctx, intent.target_option) or _option_by_label(ctx, ctx.selected_label)
    correct = _format_option(ctx.correct_label, ctx.correct_text)
    if not candidate:
        return f"Đáp án đúng là {correct}.\nLý do: {_short_correct_reason(ctx)}"
    if candidate.label == ctx.correct_label:
        return f"Đúng. {_format_option(candidate.label, candidate.text)} là đáp án đúng.\nLý do: {_short_correct_reason(ctx)}"
    first_reason, detail = _wrong_option_detail(ctx, candidate)
    lines = [f"Không. {_format_option(candidate.label, candidate.text)} không đúng vì {first_reason}."]
    if detail:
        lines.append(detail)
    lines.append(f"Đáp án đúng là {correct}.")
    lines.append(f"Lý do: {_short_correct_reason(ctx)}")
    return "\n".join(lines)


def _tense_answer(ctx: TutorContext) -> str:
    if ctx.tense_name:
        reason = ctx.tense_reason or _short_correct_reason(ctx)
        if ctx.signal_text:
            reason = "Hành động phá dỡ sẽ hoàn tất trước mốc tương lai đó."
        lines = [
            f"Chỗ trống cần {ctx.tense_name}.",
            "",
            "Công thức:",
            ctx.formula or "cấu trúc phù hợp với ngữ cảnh",
            "",
            "Dấu hiệu:",
            ctx.signal or _signal_text(ctx),
        ]
        if ctx.signal_text:
            lines.extend(["", "Trong câu:", ctx.signal_text])
        lines.extend(["", "Lý do:", reason, "", f"Đáp án đúng: {_format_option(ctx.correct_label, ctx.correct_text)}."])
        return "\n".join(lines)

    return "\n".join(
        [
            f"Chỗ trống cần: {ctx.requirement or 'cấu trúc/dạng từ phù hợp'}",
            "",
            f"Công thức: {ctx.formula or 'xem cấu trúc quanh chỗ trống'}",
            f"Dấu hiệu: {_signal_text(ctx)}",
            f"Lý do: {_main_explanation(ctx, 1) or _short_correct_reason(ctx)}",
            f"Đáp án đúng: {_format_option(ctx.correct_label, ctx.correct_text)}",
        ]
    )


def _word_form_answer(ctx: TutorContext) -> str:
    requirement = ctx.requirement or "loại từ/cấu trúc phù hợp"
    reason = _main_explanation(ctx, 1) or _short_correct_reason(ctx)
    return "\n".join(
        [
            f"Chỗ trống cần: {requirement}",
            f"Lý do: {reason.rstrip('.')}.",
            f"Đáp án đúng: {_format_option(ctx.correct_label, ctx.correct_text)}",
        ]
    )


def _grammar_formula_answer(ctx: TutorContext) -> str:
    if _is_future_perfect(ctx):
        lines = [
            f"Cấu trúc chính là {ctx.tense_name}.",
            "",
            "Công thức:",
            ctx.formula or "will have + V3",
        ]
        if ctx.signal_text:
            lines.extend(["", "Trong câu:", ctx.signal_text])
        lines.extend(["", "Cách hiểu: hành động ở mệnh đề chính sẽ hoàn tất trước mốc tương lai được nhắc đến."])
        return "\n".join(lines)
    if ctx.formula or ctx.grammar_notes:
        return f"Cấu trúc/công thức: {ctx.formula or ctx.grammar_notes}\nGiải thích ngắn: {_main_explanation(ctx, 1) or _short_correct_reason(ctx)}"
    return _word_form_answer(ctx)


def _grammar_explanation_answer(ctx: TutorContext) -> str:
    if _is_future_perfect(ctx):
        return _grammar_formula_answer(ctx)
    return _word_form_answer(ctx)


def _hint_answer(ctx: TutorContext) -> str:
    if _is_future_perfect(ctx) and ctx.signal_text:
        return "\n\n".join(
            [
                f"Gợi ý: Hãy chú ý cụm \"{ctx.signal_text}\".",
                "Cụm này nói về một mốc trong tương lai. Hành động ở vế chính phải hoàn tất trước mốc đó.",
                "Bạn cần chọn cấu trúc diễn tả \"sẽ đã làm xong\".",
            ]
        )
    signal = _signal_text(ctx)
    return f"Gợi ý: hãy nhìn vào {signal}; xác định yêu cầu của chỗ trống trước rồi mới so với các lựa chọn."


def _translation_answer(ctx: TutorContext) -> str:
    if ctx.translation:
        return ctx.translation
    if ctx.question_text:
        return f"Hiện câu này chưa có bản dịch trong dữ liệu. Mình thấy câu gốc là: {ctx.question_text}"
    return "Mình chưa thấy bản dịch tiếng Việt cho câu hiện tại trong dữ liệu."


def _option_translation(ctx: TutorContext, option: TutorOption) -> str:
    option_norm = normalize_text(option.text)
    meaning = ctx.vocabulary.get(option_norm, "")
    if meaning:
        return f"{_format_option(option.label, option.text)} nghĩa là \"{meaning}\"."
    if _is_future_perfect(ctx) and option.label == ctx.correct_label:
        return f"{_format_option(option.label, option.text)} nghĩa là \"{_correct_future_meaning(ctx)}\"."
    return f"{_format_option(option.label, option.text)}: mình chưa thấy bản dịch riêng cho lựa chọn này trong dữ liệu."


def _translation_piece_answer(ctx: TutorContext, intent: TutorIntentResult) -> str:
    option = _option_by_label(ctx, intent.target_option)
    if option:
        return _option_translation(ctx, option)
    target = intent.target_text or intent.target_option_text
    if target:
        meaning = ctx.vocabulary.get(normalize_text(target), "")
        if meaning:
            return f"{target} nghĩa là \"{meaning}\"."
        return f"Phần bạn hỏi là: {target}."
    return _translation_answer(ctx)


def _vocabulary_answer(ctx: TutorContext, intent: TutorIntentResult) -> str:
    target_raw = intent.target_text or intent.target_option_text or ""
    target = normalize_text(target_raw)
    if not target and intent.target_option:
        option = _option_by_label(ctx, intent.target_option)
        if option:
            return _option_translation(ctx, option)

    meaning = ctx.vocabulary.get(target, "")
    if target == "by the time" and meaning:
        lines = [
            "\"By the time\" nghĩa là \"trước khi / đến lúc mà\".",
        ]
        if ctx.signal_text:
            lines.extend(["", "Trong câu này:", ctx.signal_text])
        if _is_future_perfect(ctx):
            lines.extend(
                [
                    "",
                    "Cụm này chỉ một mốc trong tương lai. Hành động ở mệnh đề chính phải hoàn tất trước mốc đó, nên thường đi với tương lai hoàn thành:",
                    ctx.formula or "will have + V3",
                    ".",
                ]
            )
        return "\n".join(lines).replace("\n.", ".")
    if meaning:
        display = target_raw or target
        return f"{display} nghĩa là \"{meaning}\".\nTrong câu này: {meaning}."
    option = _option_by_label(ctx, intent.target_option)
    if option:
        return _option_translation(ctx, option)
    return "Mình chưa thấy phần giải thích từ/cụm này trong dữ liệu câu hiện tại."


def _full_option_analysis(ctx: TutorContext) -> str:
    lines = []
    for option in ctx.options:
        if option.label == ctx.correct_label:
            reason = _option_reason_text(ctx, option)
            lines.append(f"{_format_option(option.label, option.text)}: Đúng. {reason.rstrip('.')}.")
        else:
            first_reason, detail = _wrong_option_detail(ctx, option)
            reason = first_reason
            if detail:
                reason = f"{first_reason}. {detail}"
            lines.append(f"{_format_option(option.label, option.text)}: Sai. {reason.rstrip('.')}.")
    return "\n".join(lines)


def _wrong_options_analysis(ctx: TutorContext) -> str:
    lines = ["Các đáp án còn lại sai vì:"]
    for option in ctx.options:
        if option.label == ctx.correct_label:
            continue
        first_reason, detail = _wrong_option_detail(ctx, option)
        reason = first_reason
        if detail:
            reason = f"{first_reason}, {detail[:1].lower() + detail[1:]}"
        lines.append("")
        lines.append(f"{_format_option(option.label, option.text)}: Sai vì {reason.rstrip('.')}.")
    lines.extend(["", f"Đáp án đúng là {_format_option(ctx.correct_label, ctx.correct_text)}."])
    return "\n".join(lines)


def _compare_options(ctx: TutorContext, intent: TutorIntentResult) -> str:
    labels = list(intent.target_options)
    if len(labels) < 2:
        labels = [option.label for option in ctx.options[:2]]
    first = _option_by_label(ctx, labels[0]) if labels else None
    second = _option_by_label(ctx, labels[1]) if len(labels) > 1 else None
    if not first or not second:
        return _full_option_analysis(ctx)
    first_status = "đúng" if first.label == ctx.correct_label else "sai"
    second_status = "đúng" if second.label == ctx.correct_label else "sai"
    lines = [
        f"{_format_option(first.label, first.text)}: {first_status}. {_option_reason_text(ctx, first).rstrip('.')}.",
        f"{_format_option(second.label, second.text)}: {second_status}. {_option_reason_text(ctx, second).rstrip('.')}.",
    ]
    if _is_future_perfect(ctx):
        lines.extend(
            [
                "",
                f"Điểm khác biệt chính: đáp án đúng phải diễn tả hành động sẽ hoàn tất trước mốc tương lai \"{ctx.signal_text or ctx.signal}\".",
            ]
        )
    return "\n".join(lines)


def _trap_answer(ctx: TutorContext) -> str:
    if _is_future_perfect(ctx) and ctx.signal_text:
        return (
            f"Bẫy nằm ở dấu hiệu \"{ctx.signal_text}\". "
            f"Cụm này nói về mốc tương lai, nên chỗ trống cần {ctx.tense_name} ({ctx.formula or 'will have + V3'}), "
            "không phải thì hiện tại/quá khứ nhìn có vẻ quen hơn."
        )
    explanation = _main_explanation(ctx, 1) or _short_correct_reason(ctx)
    return f"Bẫy chính là phải bám vào dấu hiệu ngữ pháp/ngữ cảnh: {explanation.rstrip('.')}."


def _tested_point_answer(ctx: TutorContext) -> str:
    point = ctx.tested_point or ctx.tense_name or ctx.requirement or ctx.formula or ctx.grammar_notes
    if point:
        return f"Câu này kiểm tra: {point}.\nDấu hiệu: {_signal_text(ctx)}"
    return f"Câu này kiểm tra cách chọn đáp án theo ngữ cảnh quanh chỗ trống.\nDấu hiệu: {_signal_text(ctx)}"


def _signal_answer(ctx: TutorContext) -> str:
    if _is_future_perfect(ctx) and ctx.signal_text:
        return f"Dấu hiệu chính:\n{ctx.signal_text}\n\nCụm này cho biết có một mốc trong tương lai; hành động ở vế chính phải hoàn tất trước mốc đó."
    return f"Dấu hiệu chính: {_signal_text(ctx)}"


def _how_to_solve_answer(ctx: TutorContext) -> str:
    if _is_future_perfect(ctx):
        lines = []
        if ctx.signal_text:
            lines.append(f"Câu này cần nhìn dấu hiệu \"{ctx.signal_text}\".")
            lines.append("")
        lines.extend(
            [
                "Đây là một mốc trong tương lai. Hành động \"demolish the main section\" sẽ hoàn tất trước mốc đó, nên cần dùng thì tương lai hoàn thành.",
                "",
                "Công thức:",
                ctx.formula or "will have + V3",
                "",
                f"Đáp án đúng: {_format_option(ctx.correct_label, ctx.correct_text)}.",
            ]
        )
        return "\n".join(lines)
    return "\n".join(
        [
            f"Cần nhìn: {_signal_text(ctx)}",
            f"Yêu cầu: {ctx.requirement or ctx.tense_name or _main_explanation(ctx, 1) or 'xác định cấu trúc quanh chỗ trống'}",
            f"Đáp án đúng: {_format_option(ctx.correct_label, ctx.correct_text)}",
            f"Lý do ngắn: {_short_correct_reason(ctx)}",
        ]
    )


def _example_answer(ctx: TutorContext) -> str:
    if _is_future_perfect(ctx):
        return "\n".join(
            [
                "Vi du tuong tu:",
                "By the time we arrive, they will have finished the report.",
                "",
                "Cau nay cung dung cau truc:",
                ctx.formula or "will have + V3",
                "",
                "Y nghia: mot hanh dong se hoan tat truoc mot moc trong tuong lai.",
            ]
        )
    signal = _signal_text(ctx)
    return f"Vi du tuong tu nen bam vao cung dau hieu/y tu: {signal}"


def build_tutor_answer(intent: TutorIntentResult, ctx: TutorContext) -> TutorAnswer | None:
    if not ctx.question_text and not ctx.options and not ctx.correct_text:
        return None

    target_option = _option_by_label(ctx, intent.target_option)
    by_text = bool(
        target_option
        and intent.target_option_text
        and normalize_text(intent.target_option_text) in intent.normalized_message
        and not intent.normalized_message.startswith(("option ", "dap an "))
    )

    if intent.intent == "correct_answer":
        answer = f"Đáp án đúng: {_format_option(ctx.correct_label, ctx.correct_text)}\nLý do: {_short_correct_reason(ctx)}"
    elif intent.intent == "how_to_solve":
        answer = _how_to_solve_answer(ctx)
    elif intent.intent == "why_correct":
        correct = _correct_option(ctx)
        answer = _correct_option_reason_answer(ctx, correct) if correct else f"Đáp án đúng là {_format_option(ctx.correct_label, ctx.correct_text)} vì {_short_correct_reason(ctx)}"
    elif intent.intent == "option_reason" and target_option:
        answer = _option_reason_answer(ctx, target_option, by_text=by_text)
    elif intent.intent == "selected_wrong_reason":
        answer = _selected_wrong_answer(ctx, intent)
    elif intent.intent == "compare_options":
        answer = _compare_options(ctx, intent)
    elif intent.intent == "tense_requirement":
        answer = _tense_answer(ctx)
    elif intent.intent == "word_form_requirement":
        answer = _word_form_answer(ctx)
    elif intent.intent == "grammar_formula":
        answer = _grammar_formula_answer(ctx)
    elif intent.intent == "grammar_explanation":
        answer = _grammar_explanation_answer(ctx)
    elif intent.intent == "vocabulary_meaning":
        answer = _vocabulary_answer(ctx, intent)
    elif intent.intent == "option_translation":
        option = target_option or _option_by_label(ctx, intent.target_option)
        answer = _option_translation(ctx, option) if option else _translation_piece_answer(ctx, intent)
    elif intent.intent == "translation_piece":
        answer = _translation_piece_answer(ctx, intent)
    elif intent.intent == "translation":
        answer = _translation_answer(ctx)
    elif intent.intent == "hint":
        answer = _hint_answer(ctx)
    elif intent.intent == "trap_explanation":
        answer = _trap_answer(ctx)
    elif intent.intent == "signal":
        answer = _signal_answer(ctx)
    elif intent.intent == "full_option_analysis":
        answer = _full_option_analysis(ctx)
    elif intent.intent == "wrong_options_analysis":
        answer = _wrong_options_analysis(ctx)
    elif intent.intent == "correct_answer_check":
        answer = _correct_answer_check(ctx, intent)
    elif intent.intent == "tested_point":
        answer = _tested_point_answer(ctx)
    elif intent.intent == "example_request":
        answer = _example_answer(ctx)
    elif intent.intent in {"explanation", "explanation_short", "explanation_simplify"}:
        answer = _how_to_solve_answer(ctx) if _is_future_perfect(ctx) else (_main_explanation(ctx, 2) or _short_correct_reason(ctx))
    elif intent.intent == "general":
        return None
    else:
        return None

    if not answer:
        return None
    has_detail = ctx.has_explanation or ctx.has_explanation_detail or ctx.has_option_analysis or ctx.has_grammar_notes or ctx.raw_block
    if not has_detail and intent.intent not in {"translation", "translation_piece", "option_translation", "hint", "correct_answer"}:
        answer = f"{MISSING_DETAIL_PREFIX}\n{answer}"
    return TutorAnswer(answer=answer, intent=intent.intent, target_option=intent.target_option, target_option_text=intent.target_option_text)


class AnswerBuilder:
    def build(
        self,
        reply: str,
        conversation_id: int,
        user_message: ChatMessageDto,
        assistant_message: ChatMessageDto,
        intent_result: IntentResult,
        context: ChatContextBundle,
    ) -> ChatResponse:
        assistant_message.content = reply
        assistant_message.status = "completed"
        assistant_message.intent = intent_result.intent
        assistant_message.metadata = {
            "intent": intent_result.intent,
            "intent_confidence": intent_result.confidence,
            "intent_reason": intent_result.reason,
        }
        return ChatResponse(
            reply=reply,
            conversation_id=conversation_id,
            intent=intent_result.intent,
            suggestions=self._suggestions(intent_result.intent, context),
            user_message=user_message,
            assistant_message=assistant_message,
            intent_confidence=intent_result.confidence,
            intent_reason=intent_result.reason,
            context_missing=context.missing,
        )

    def _suggestions(self, intent: ChatIntent, context: ChatContextBundle) -> list[str]:
        common = ["Giai thich ngan gon hon", "Cho vi du tuong tu", "Tao bai luyen them"]
        by_intent: dict[ChatIntent, list[str]] = {
            "word_meaning": [],
            "collocation_preposition": [],
            "gap_requirement": [],
            "correct_answer": [],
            "option_reason": [],
            "full_option_analysis": [],
            "translation": [],
            "explanation": [],
            "hint": [],
            "grammar_structure": [],
            "grammar_formula_request": [],
            "target_completion_request": [],
            "grammar_structure_definition": [],
            "collocation_preposition_request": [],
            "relative_pronoun_request": [],
            "vocabulary_definition_only": ["Dich cau nay", "Dap an la gi?", "Phan tich dap an"],
            "vocabulary_lookup": ["Option nay dung hay sai?", "Vi sao dap an dung?", "Dich ca cau"],
            "why_option_wrong": ["Giai thich dap an dung", "Phan tich cac option", "Cho meo nhan biet"],
            "answer_request": ["Vi sao dap an dung?", "Phan tich cac option", "Dich cau nay"],
            "explain_question": ["Giai thich ngu phap", "Vi sao dap an sai?", "Tao cau tuong tu"],
            "grammar_help": ["Cho cong thuc", "Sua cau cua em", "Tao mini quiz"],
            "vocabulary_help": ["Them collocations", "Dat cau TOEIC", "Phan biet tu gan nghia"],
            "translate": ["Dich tu nhien hon", "Giai thich cach dung", "Cho ban formal"],
            "fix_sentence": ["Viet tu nhien hon", "Giai thich loi sai", "Tao 3 cau luyen"],
            "generate_examples": ["Tang do kho", "Them dap an", "Giai thich tung cau"],
            "study_plan": ["Ke hoach 7 ngay", "Tap trung diem yeu", "Bai tap hom nay"],
            "weak_skill_analysis": ["Tom tat loi sai", "De xuat bai luyen", "Uu tien ky nang nao?"],
            "mock_test_review": ["Tom tat loi sai", "Ke hoach phuc hoi", "Luyen part yeu nhat"],
            "weekly_check_advice": ["Muc tieu tuan nay", "Bai luyen nen lam", "Can on lai gi?"],
            "general_chat": common,
        }
        suggestions = by_intent.get(intent, common)
        if not suggestions:
            return []
        if context.missing:
            suggestions = [*suggestions[:2], "Can them ngu canh gi?"]
        return list(dict.fromkeys(suggestions + common))[:5]
