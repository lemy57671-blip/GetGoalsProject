import edge_tts
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import io
from app.core.config import settings
import hashlib

router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"

@router.post("/api/tts/tts")
async def text_to_speech(request: TTSRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        communicate = edge_tts.Communicate(request.text.strip(), voice=request.voice)
        async def audio_generator():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        return StreamingResponse(audio_generator(), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS Error: {str(e)}")

@router.post("/api/tts/flashcard")
async def flashcard_tts(request: TTSRequest):
    """
    Endpoint dành riêng cho Flashcards: Lưu file trên server nhưng trả về FileResponse
    để tương thích tốt như Voice Reader.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    audio_dir = settings.AUDIO_STATIC_ROOT / "flashcards"
    audio_dir.mkdir(parents=True, exist_ok=True)

    h = hashlib.md5(f"{request.text.strip().lower()}|{request.voice}".encode()).hexdigest()
    filename = f"fc_{h}.mp3"
    filepath = audio_dir / filename

    if not filepath.exists():
        try:
            communicate = edge_tts.Communicate(request.text.strip(), voice=request.voice)
            await communicate.save(str(filepath))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS Error: {str(e)}")

    return FileResponse(filepath, media_type="audio/mpeg")

@router.get("/api/tts/voices")
async def get_voices():
    return {
        "voices": [
            {"id": "en-US-AriaNeural", "name": "Aria (US Female)", "lang": "en-US", "gender": "Female"},
            {"id": "en-US-GuyNeural", "name": "Guy (US Male)", "lang": "en-US", "gender": "Male"},
            {"id": "en-GB-SoniaNeural", "name": "Sonia (UK Female)", "lang": "en-GB", "gender": "Female"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (UK Male)", "lang": "en-GB", "gender": "Male"},
            {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My (VN Female)", "lang": "vi-VN", "gender": "Female"},
            {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh (VN Male)", "lang": "vi-VN", "gender": "Male"},
        ]
    }
