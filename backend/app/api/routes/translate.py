import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.translator import Translator

router = APIRouter()
logger = logging.getLogger(__name__)

class TranslationRequest(BaseModel):
    text: str

class TranslationResponse(BaseModel):
    text: str
    translated_text: str
    source: Literal["cache", "model"]

# Singleton cho Translator
_translator = None

def get_translator():
    global _translator
    if _translator is None:
        try:
            _translator = Translator()
        except Exception as e:
            logger.exception("[Translate API] Error initializing Translator: %s", e)
            return None
    return _translator

@router.post("/api/translate")
async def translate_text(request: TranslationRequest):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    translator = get_translator()
    if translator is None:
        raise HTTPException(status_code=500, detail="AI Translation service is not available")

    try:
        text = request.text
        result = translator.translate_with_source(text)
        response = TranslationResponse(
            text=result["text"],
            translated_text=result["translated_text"],
            source=result["source"],
        )
        content = response.model_dump() if hasattr(response, "model_dump") else response.dict()
        return JSONResponse(
            content=content,
            media_type="application/json; charset=utf-8",
        )
    except Exception as e:
        logger.exception("[Translate API] Translation error: %s", e)
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")
