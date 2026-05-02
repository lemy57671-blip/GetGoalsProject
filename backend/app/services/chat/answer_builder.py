from __future__ import annotations

from app.schemas.chat import ChatContextBundle, ChatIntent, ChatMessageDto, ChatResponse, IntentResult


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
