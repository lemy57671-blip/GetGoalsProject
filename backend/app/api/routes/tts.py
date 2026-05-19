import hashlib
import importlib.util
import logging
import re
from pathlib import Path

import edge_tts
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

TTS_VOICES = [
    {"id": "en-US-AriaNeural", "name": "Aria (US Female)", "lang": "en-US", "gender": "Female"},
    {"id": "en-US-GuyNeural", "name": "Guy (US Male)", "lang": "en-US", "gender": "Male"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (UK Female)", "lang": "en-GB", "gender": "Female"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (UK Male)", "lang": "en-GB", "gender": "Male"},
    {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My (VN Female)", "lang": "vi-VN", "gender": "Female"},
    {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh (VN Male)", "lang": "vi-VN", "gender": "Male"},
]

VOICE_ALIASES = {
    voice["id"].lower(): voice["id"]
    for voice in TTS_VOICES
}
VOICE_ALIASES.update(
    {
        voice["name"].lower(): voice["id"]
        for voice in TTS_VOICES
    }
)
VOICE_ALIASES.update(
    {
        "aria": "en-US-AriaNeural",
        "aria us female": "en-US-AriaNeural",
        "guy": "en-US-GuyNeural",
        "guy us male": "en-US-GuyNeural",
        "sonia": "en-GB-SoniaNeural",
        "ryan": "en-GB-RyanNeural",
        "hoai my": "vi-VN-HoaiMyNeural",
        "hoài my": "vi-VN-HoaiMyNeural",
        "nam minh": "vi-VN-NamMinhNeural",
    }
)


class TTSRequest(BaseModel):
    text: str | None = None
    word: str | None = None
    voice: str = "en-US-AriaNeural"

    def normalized_text(self) -> str:
        value = self.word if self.word is not None else self.text
        return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_voice(value: str | None) -> str:
    voice = str(value or "").strip()
    if not voice:
        return "en-US-AriaNeural"

    key = re.sub(r"\s+", " ", voice).strip().lower()
    key_without_punctuation = re.sub(r"[()]", "", key)
    normalized = VOICE_ALIASES.get(key) or VOICE_ALIASES.get(key_without_punctuation)
    if normalized:
        return normalized

    valid_voices = ", ".join(voice_item["id"] for voice_item in TTS_VOICES)
    raise HTTPException(
        status_code=400,
        detail={
            "message": "Unsupported voice selected.",
            "voice": voice,
            "valid_voices": valid_voices,
        },
    )


def _tts_provider_error(provider_error: str, message: str = "Unable to generate voice. Please try again.") -> HTTPException:
    return HTTPException(
        status_code=502,
        detail={
            "message": message,
            "provider": "edge_tts",
            "provider_error": provider_error,
            "source": "failed",
        },
    )


def _flashcard_audio_url(filename: str) -> str:
    return f"/audio/flashcards/{filename}"


def _is_valid_audio_file(path: Path) -> bool:
    try:
        return path.exists() and path.is_file() and path.stat().st_size > 128
    except OSError:
        return False


def _audio_url_to_local_path(value: str) -> Path | None:
    audio_url = str(value or "").strip().replace("\\", "/")
    if not audio_url:
        return None
    if audio_url.startswith("/audio/"):
        relative = audio_url[len("/audio/") :].lstrip("/")
        return settings.AUDIO_STATIC_ROOT / relative
    if audio_url.startswith("audio/"):
        return settings.AUDIO_STATIC_ROOT / audio_url[len("audio/") :].lstrip("/")
    candidate = Path(audio_url)
    if candidate.is_absolute():
        return candidate
    return None


def _normalize_db_audio_url(value: str) -> str | None:
    audio_url = str(value or "").strip().replace("\\", "/")
    if not audio_url:
        return None
    if audio_url.lower().startswith(("http://", "https://", "data:")):
        return audio_url
    if audio_url.startswith("/audio/"):
        return audio_url
    if audio_url.startswith("audio/"):
        return f"/{audio_url}"
    local_path = Path(audio_url)
    if local_path.is_absolute():
        try:
            relative = local_path.resolve().relative_to(settings.AUDIO_STATIC_ROOT.resolve()).as_posix()
            return f"/audio/{relative}"
        except Exception:
            return None
    return f"/audio/flashcards/{audio_url.lstrip('/')}"


def _db_audio_exists(value: str) -> bool:
    audio_url = str(value or "").strip()
    if audio_url.lower().startswith(("http://", "https://", "data:")):
        return True
    local_path = _audio_url_to_local_path(audio_url)
    return _is_valid_audio_file(local_path) if local_path else False


def _load_flashcard_db_audio(db: Session, word: str) -> str | None:
    try:
        column_rows = db.execute(
            sql_text(
                """
                SELECT c.name AS ColumnName
                FROM sys.columns c
                JOIN sys.objects o ON o.object_id = c.object_id
                WHERE o.object_id = OBJECT_ID(N'dbo.Flashcards')
                  AND c.name IN (N'AudioUrl', N'AudioURL', N'AudioPath', N'AudioFile', N'AudioFilePath')
                """
            )
        ).mappings().all()
    except Exception:
        logger.debug("Could not inspect Flashcards audio columns.", exc_info=True)
        return None

    columns = [str(row["ColumnName"]) for row in column_rows if row.get("ColumnName")]
    if not columns:
        return None

    select_parts = ", ".join(f"[{column}] AS [{column}]" for column in columns)
    try:
        row = db.execute(
            sql_text(
                f"""
                SELECT TOP 1 {select_parts}
                FROM dbo.Flashcards
                WHERE LOWER(LTRIM(RTRIM(Word))) = LOWER(:word)
                ORDER BY Id
                """
            ),
            {"word": word.strip()},
        ).mappings().first()
    except Exception:
        logger.debug("Could not query Flashcards audio columns for word=%r.", word, exc_info=True)
        return None

    if not row:
        return None

    for column in columns:
        audio_url = _normalize_db_audio_url(str(row.get(column) or ""))
        if audio_url and _db_audio_exists(audio_url):
            return audio_url
    return None


async def _generate_with_edge_tts(text: str, voice: str, filepath: Path) -> None:
    communicate = edge_tts.Communicate(text, voice=voice)
    await communicate.save(str(filepath))


def _generate_with_pyttsx3_if_available(text: str, filepath: Path) -> bool:
    if importlib.util.find_spec("pyttsx3") is None:
        return False
    try:
        import pyttsx3  # type: ignore

        engine = pyttsx3.init()
        engine.save_to_file(text, str(filepath))
        engine.runAndWait()
        return _is_valid_audio_file(filepath)
    except Exception:
        logger.info("Local pyttsx3 fallback failed for flashcard TTS.", exc_info=True)
        return False

@router.post("/api/tts/tts")
async def text_to_speech(request: TTSRequest):
    text = request.normalized_text()
    voice = _normalize_voice(request.voice)
    logger.info(
        "[TTS] text length=%s requested voice=%s normalized voice=%s",
        len(text),
        request.voice,
        voice,
    )

    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Text is too long. Maximum length is 500 characters.")

    try:
        communicate = edge_tts.Communicate(text, voice=voice)
        audio_bytes = bytearray()

        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                audio_bytes.extend(chunk["data"])

        if not audio_bytes:
            raise _tts_provider_error("empty audio output", "TTS service did not return usable audio data.")

        logger.info("[TTS] provider=edge_tts success bytes=%s voice=%s", len(audio_bytes), voice)
        return Response(content=bytes(audio_bytes), media_type="audio/mpeg")
    except HTTPException:
        raise
    except Exception as e:
        provider_error = str(e)
        logger.warning(
            "[TTS] provider=edge_tts failure voice=%s error=%s",
            voice,
            provider_error,
            exc_info=True,
        )
        raise _tts_provider_error(provider_error) from e

@router.post("/api/tts/flashcard")
async def flashcard_tts(request: TTSRequest, db: Session = Depends(get_db)):
    """
    Endpoint dành riêng cho Flashcards.

    Trả JSON chứa URL file tĩnh thay vì stream blob trực tiếp để frontend có thể
    cache/reuse audio ổn định và tránh lỗi blob range khi đổi từ liên tục.
    """
    text = request.normalized_text()
    voice = _normalize_voice(request.voice)
    logger.info(
        "[TTS] flashcard text length=%s requested voice=%s normalized voice=%s",
        len(text),
        request.voice,
        voice,
    )

    if not text:
        raise HTTPException(status_code=400, detail="Word cannot be empty")

    if len(text) > 120:
        raise HTTPException(status_code=400, detail="Flashcard word is too long. Maximum length is 120 characters.")

    db_audio_url = _load_flashcard_db_audio(db, text)
    if db_audio_url:
        logger.info("Flashcard TTS source=db_audio word=%r", text)
        return {
            "audio_url": db_audio_url,
            "source": "db_audio",
            "cached": True,
            "content_type": "audio/mpeg",
        }

    audio_dir = settings.AUDIO_STATIC_ROOT / "flashcards"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Keep the legacy md5 filename scheme so existing flashcard audio cache is reused.
    h = hashlib.md5(f"{text.lower()}|{voice}".encode("utf-8")).hexdigest()
    filename = f"fc_{h}.mp3"
    filepath = audio_dir / filename

    if filepath.exists() and filepath.stat().st_size > 128:
        logger.info("Flashcard TTS source=cache word=%r", text)
        return {
            "audio_url": _flashcard_audio_url(filename),
            "source": "cache",
            "cached": True,
            "content_type": "audio/mpeg",
        }

    if filepath.exists():
        try:
            filepath.unlink()
        except OSError:
            logger.warning("Could not remove invalid flashcard TTS cache file: %s", filepath, exc_info=True)

    provider_error = ""
    try:
        await _generate_with_edge_tts(text, voice, filepath)
    except Exception as exc:
        provider_error = str(exc)
        logger.warning("Flashcard TTS provider=edge_tts failed word=%r voice=%s error=%s", text, voice, provider_error, exc_info=True)

        local_filename = f"fc_{h}_local.wav"
        local_path = audio_dir / local_filename
        if _generate_with_pyttsx3_if_available(text, local_path):
            logger.info("Flashcard TTS source=generated provider=pyttsx3 word=%r", text)
            return {
                "audio_url": _flashcard_audio_url(local_filename),
                "source": "generated",
                "provider": "pyttsx3",
                "cached": False,
                "content_type": "audio/wav",
            }

        raise HTTPException(
            status_code=502,
            detail={
                "message": "Unable to generate voice. Please try again.",
                "provider": "edge_tts",
                "provider_error": provider_error,
                "source": "failed",
            },
        ) from exc

    if not filepath.exists() or filepath.stat().st_size <= 128:
        try:
            filepath.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove empty flashcard TTS output: %s", filepath, exc_info=True)
        logger.error("Flashcard TTS generated empty audio word=%r voice=%s", text, voice)
        raise HTTPException(
            status_code=502,
            detail={
                "message": "TTS service did not return usable audio data.",
                "provider": "edge_tts",
                "provider_error": provider_error or "empty audio output",
                "source": "failed",
            },
        )

    logger.info("Flashcard TTS source=generated provider=edge_tts word=%r", text)
    return {
        "audio_url": _flashcard_audio_url(filename),
        "source": "generated",
        "provider": "edge_tts",
        "cached": False,
        "content_type": "audio/mpeg",
    }

@router.get("/api/tts/voices")
async def get_voices():
    return {"voices": TTS_VOICES}
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
