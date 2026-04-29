import os
import hashlib
import re
import time
import edge_tts
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

app = FastAPI(title="Dichteinganh TTS Server")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---
class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"

# --- UTILS ---
def normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text

def generate_hash(text: str, voice: str) -> str:
    normalized = normalize_text(text)
    key = f"{normalized}|{voice}"
    return hashlib.md5(key.encode('utf-8')).hexdigest()

# --- ROUTES ---

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    h = generate_hash(request.text, request.voice)
    filename = f"{h}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    
    cached = os.path.exists(filepath)
    if not cached:
        try:
            communicate = edge_tts.Communicate(request.text.strip(), voice=request.voice)
            await communicate.save(filepath)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS Error: {str(e)}")
    
    return {
        "url": f"/audio/{filename}",
        "cached": cached,
        "text": request.text.strip(),
        "hash": h
    }

@app.get("/api/voices")
async def get_voices():
    return {
        "voices": [
            {"id": "en-US-AriaNeural", "name": "Aria (US Female)", "lang": "en-US", "gender": "Female"},
            {"id": "en-US-GuyNeural", "name": "Guy (US Male)", "lang": "en-US", "gender": "Male"},
            {"id": "en-GB-SoniaNeural", "name": "Sonia (UK Female)", "lang": "en-GB", "gender": "Female"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (UK Male)", "lang": "en-GB", "gender": "Male"},
            {"id": "en-AU-NatashaNeural", "name": "Natasha (AU Female)", "lang": "en-AU", "gender": "Female"},
        ]
    }

@app.get("/api/sentences")
async def get_sentences():
    # Mock data for testing
    return {
        "sentences": [
            {"id": 1, "text": "A woman is watering the plants in the garden.", "part": 1},
            {"id": 2, "text": "Where can I find the quarterly report?", "part": 2},
            {"id": 3, "text": "The meeting has been rescheduled to Friday.", "part": 3},
            {"id": 4, "text": "Attention all passengers, flight 723 is delayed.", "part": 4},
        ],
        "total": 4,
        "page": 1,
        "pages": 1
    }

@app.get("/api/parts")
async def get_parts():
    return {"parts": [1, 2, 3, 4]}

@app.get("/health")
async def health():
    return {"status": "ok"}

# Static files
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    print("Starting Dichteinganh Server...")
    print("URL: http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
