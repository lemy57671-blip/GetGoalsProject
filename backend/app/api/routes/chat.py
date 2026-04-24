from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import require_pro_user
from app.models import User
from app.schemas.payments import ChatBody
from app.services.chat import send_chat_message


router = APIRouter()


@router.post("/api/chat")
async def post_chat(payload: ChatBody, _: User = Depends(require_pro_user)):
    if payload.message is None:
        return {"reply": "Please enter a message first."}
    result = await send_chat_message(payload.message)
    if result.status_code == 200:
        return result.payload
    return JSONResponse(status_code=result.status_code, content=result.payload)
