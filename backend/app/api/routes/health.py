from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter


router = APIRouter()


@router.get("/api/health")
def get_health() -> dict:
    return {"status": "ok", "time": datetime.now()}
