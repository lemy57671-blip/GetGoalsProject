from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import ChatConversation, ChatMessage, User
from app.schemas.chat import ChatRequest
from app.services.chat.answer_builder import AnswerBuilder
from app.services.chat.context_service import ChatContextService
from app.services.chat.conversation_service import ConversationService
from app.services.chat.intent_router import IntentRouter
from app.services.chat.provider_factory import get_tutor_provider
from app.services.chat.quality_guard import QualityGuard


@dataclass
class ChatServiceResult:
    status_code: int
    payload: dict


@dataclass
class PreparedChat:
    conversation: ChatConversation
    user_message: ChatMessage
    assistant_message: ChatMessage
    intent_result: object
    context: object


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.guard = QualityGuard()
        self.intent_router = IntentRouter()
        self.context_service = ChatContextService(db)
        self.conversation_service = ConversationService(db)
        self.provider = get_tutor_provider()
        self.answer_builder = AnswerBuilder()

    async def send_message(self, request: ChatRequest, user: User) -> ChatServiceResult:
        guard_result = self.guard.check_user_message(request.message)
        if not guard_result.allowed:
            return ChatServiceResult(status_code=200, payload={"reply": guard_result.reply})

        prepared = self._prepare(request, user, guard_result.message or "")
        provider_result = await self.provider.generate(prepared.intent_result, prepared.context, prepared.user_message.content)
        reply = self.guard.clean_reply(provider_result.reply)

        if provider_result.status_code != 200:
            self.conversation_service.update_message(
                prepared.assistant_message,
                reply,
                prepared.intent_result.intent,
            )
            return ChatServiceResult(
                status_code=provider_result.status_code,
                payload={
                    "reply": reply,
                    "conversation_id": prepared.conversation.id,
                    "intent": prepared.intent_result.intent,
                    "suggestions": [],
                    "provider_error": provider_result.raw_error,
                },
            )

        assistant_message = self.conversation_service.update_message(
            prepared.assistant_message,
            reply,
            prepared.intent_result.intent,
        )
        response = self.answer_builder.build(
            reply=reply,
            conversation_id=prepared.conversation.id,
            user_message=self.conversation_service.to_dto(prepared.user_message),
            assistant_message=self.conversation_service.to_dto(assistant_message),
            intent_result=prepared.intent_result,
            context=prepared.context,
        )
        return ChatServiceResult(status_code=200, payload=response.model_dump(mode="json"))

    async def stream_events(self, request: ChatRequest, user: User) -> AsyncIterator[str]:
        guard_result = self.guard.check_user_message(request.message)
        if not guard_result.allowed:
            yield self._sse("error", {"message": guard_result.reply or "Invalid chat request."})
            return

        prepared = self._prepare(request, user, guard_result.message or "")
        created_payload = {
            "conversation_id": prepared.conversation.id,
            "user_message": self.conversation_service.to_dto(prepared.user_message).model_dump(mode="json"),
            "assistant_message": self.conversation_service.to_dto(
                prepared.assistant_message,
                status="created",
            ).model_dump(mode="json"),
            "intent": prepared.intent_result.intent,
            "intent_confidence": prepared.intent_result.confidence,
            "intent_reason": prepared.intent_result.reason,
            "suggestions": self.answer_builder._suggestions(prepared.intent_result.intent, prepared.context),
        }
        yield self._sse("created", created_payload)
        yield self._sse(
            "status",
            {
                "assistant_message": self.conversation_service.to_dto(
                    prepared.assistant_message,
                    status="streaming",
                ).model_dump(mode="json")
            },
        )

        provider_result = await self.provider.generate(prepared.intent_result, prepared.context, prepared.user_message.content)
        reply = self.guard.clean_reply(provider_result.reply)
        if provider_result.status_code != 200:
            failed = self.conversation_service.update_message(
                prepared.assistant_message,
                reply,
                prepared.intent_result.intent,
            )
            yield self._sse(
                "error",
                {
                    "message": reply,
                    "provider_error": provider_result.raw_error,
                    "assistant_message": self.conversation_service.to_dto(
                        failed,
                        status="failed",
                    ).model_dump(mode="json"),
                },
            )
            return

        current_content = ""
        for chunk in self._chunk_text(reply):
            current_content += chunk
            self.conversation_service.update_message(
                prepared.assistant_message,
                current_content,
                prepared.intent_result.intent,
            )
            yield self._sse(
                "chunk",
                {
                    "assistant_message_id": prepared.assistant_message.id,
                    "content_delta": chunk,
                    "content": current_content,
                },
            )

        completed = self.conversation_service.update_message(
            prepared.assistant_message,
            reply,
            prepared.intent_result.intent,
        )
        response = self.answer_builder.build(
            reply=reply,
            conversation_id=prepared.conversation.id,
            user_message=self.conversation_service.to_dto(prepared.user_message),
            assistant_message=self.conversation_service.to_dto(completed),
            intent_result=prepared.intent_result,
            context=prepared.context,
        )
        yield self._sse("completed", response.model_dump(mode="json"))

    def _prepare(self, request: ChatRequest, user: User, message: str) -> PreparedChat:
        conversation = self.conversation_service.get_or_create_conversation(
            user_id=user.id,
            conversation_id=request.conversation_id,
            first_message=message,
        )
        intent_result = self.intent_router.classify(
            message,
            context_type=request.context_type,
            question_id=request.question_id,
            attempt_id=request.attempt_id,
        )
        context = self.context_service.build_context(user, request, intent_result.intent)
        user_message = self.conversation_service.add_message(
            conversation=conversation,
            user_id=user.id,
            role="user",
            content=message,
            intent=intent_result.intent,
        )
        assistant_message = self.conversation_service.add_message(
            conversation=conversation,
            user_id=user.id,
            role="assistant",
            content="",
            intent=intent_result.intent,
        )
        return PreparedChat(
            conversation=conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            intent_result=intent_result,
            context=context,
        )

    def _sse(self, event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _chunk_text(self, content: str, target_size: int = 100) -> Iterator[str]:
        if len(content) <= target_size:
            yield content
            return

        buffer = ""
        for token in content.split(" "):
            next_buffer = f"{buffer} {token}" if buffer else token
            if len(next_buffer) >= target_size:
                yield next_buffer + " "
                buffer = ""
            else:
                buffer = next_buffer
        if buffer:
            yield buffer
