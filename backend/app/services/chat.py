from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass
class ChatServiceResult:
    status_code: int
    payload: dict


async def send_chat_message(message: str) -> ChatServiceResult:
    if not message.strip():
        return ChatServiceResult(status_code=200, payload={"reply": "Please enter a message first."})
    if not settings.gemini_api_key:
        return ChatServiceResult(status_code=503, payload={"reply": "GEMINI_API_KEY is missing from the environment."})

    system_instruction = (
        "You are an English teacher inside a TOEIC learning app. "
        "Reply in a friendly, concise, conversational way without numbered lists by default. "
        "If the user asks something unrelated to English learning, gently steer the conversation back."
    )
    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": message.strip()}]}],
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": settings.gemini_api_key},
                json=payload,
            )
            response_text = response.text
            if response.status_code >= 400:
                logger.error("Gemini error: %s %s", response.status_code, response_text)
                return ChatServiceResult(
                    status_code=502,
                    payload={
                        "reply": "Gemini request failed on the backend.",
                        "status": response.status_code,
                        "gemini": response_text,
                    },
                )
            data = json.loads(response_text)
    except Exception as exc:  # pragma: no cover
        logger.exception("Chat service crash: %s", exc)
        return ChatServiceResult(
            status_code=502,
            payload={
                "reply": "Backend failed while handling chat.",
                "error": str(exc),
            },
        )

    reply = "No reply was generated. Please try again."
    candidates = data.get("candidates") or []
    if candidates:
        parts = (candidates[0].get("content") or {}).get("parts") or []
        if parts:
            reply = parts[0].get("text") or reply
    return ChatServiceResult(status_code=200, payload={"reply": reply})
