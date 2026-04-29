from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.translator import Translator

router = APIRouter()

class TranslationRequest(BaseModel):
    text: str

class TranslationResponse(BaseModel):
    translated_text: str

# Singleton cho Translator
_translator = None

def get_translator():
    global _translator
    if _translator is None:
        try:
            _translator = Translator()
        except Exception as e:
            print(f"[Translate API] Error initializing Translator: {e}")
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
        result = translator.translate(request.text.strip())
        return TranslationResponse(translated_text=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation error: {str(e)}")
