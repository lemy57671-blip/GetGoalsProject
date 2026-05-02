from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChatConversation, ChatMessage
from app.schemas.chat import ChatIntent, ChatMessageDto, ChatMessageStatus


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_conversation(
        self,
        user_id: int,
        conversation_id: int | None,
        first_message: str,
    ) -> ChatConversation:
        conversation = None
        if conversation_id:
            conversation = self.db.scalar(
                select(ChatConversation).where(
                    ChatConversation.id == conversation_id,
                    ChatConversation.user_id == user_id,
                )
            )
        if conversation is not None:
            return conversation

        now = datetime.utcnow()
        conversation = ChatConversation(
            user_id=user_id,
            title=self._build_title(first_message),
            created_at=now,
            updated_at=now,
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def add_message(
        self,
        conversation: ChatConversation,
        user_id: int,
        role: str,
        content: str,
        intent: ChatIntent | None = None,
    ) -> ChatMessage:
        now = datetime.utcnow()
        message = ChatMessage(
            conversation_id=conversation.id,
            user_id=user_id,
            role=role,
            content=content,
            intent=intent,
            created_at=now,
        )
        conversation.updated_at = now
        if role == "user" and not (conversation.title or "").strip():
            conversation.title = self._build_title(content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def update_message(
        self,
        message: ChatMessage,
        content: str,
        intent: ChatIntent | None,
    ) -> ChatMessage:
        message.content = content
        message.intent = intent
        conversation = self.db.get(ChatConversation, message.conversation_id)
        if conversation is not None:
            conversation.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_recent_messages(
        self,
        user_id: int,
        conversation_id: int,
        limit: int = 8,
    ) -> list[ChatMessage]:
        rows = self.db.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.conversation_id == conversation_id,
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        ).all()
        return list(reversed(rows))

    def to_dto(
        self,
        message: ChatMessage,
        status: ChatMessageStatus = "completed",
        metadata: dict | None = None,
    ) -> ChatMessageDto:
        return ChatMessageDto(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            intent=message.intent,
            status=status,
            created_at=message.created_at,
            metadata=metadata or {},
        )

    def _build_title(self, message: str) -> str:
        title = " ".join(message.strip().split())
        if not title:
            return "AI Tutor chat"
        return title[:80]
