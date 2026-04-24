from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user_id
from app.db.session import get_db
from app.schemas.weekly_check import WeeklyCheckSubmitRequest
from app.services.weekly_check import get_current_weekly_check, get_weekly_check_result, submit_weekly_check


router = APIRouter()


@router.get("/api/weekly-check/current")
def get_current(userId: int | None = Query(default=None), db: Session = Depends(get_db), claim_user_id: int | None = Depends(get_optional_current_user_id)):
    resolved_user_id = claim_user_id or userId or 0
    if resolved_user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is required for weekly check."})
    return get_current_weekly_check(db, resolved_user_id)


@router.post("/api/weekly-check/submit")
def submit(payload: WeeklyCheckSubmitRequest, db: Session = Depends(get_db), claim_user_id: int | None = Depends(get_optional_current_user_id)):
    resolved_user_id = claim_user_id or payload.userId or 0
    if resolved_user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is required for weekly check submit."})
    return submit_weekly_check(db, resolved_user_id, payload)


@router.get("/api/weekly-check/result/{attempt_id}")
def get_result(attempt_id: int, userId: int | None = Query(default=None), db: Session = Depends(get_db), claim_user_id: int | None = Depends(get_optional_current_user_id)):
    resolved_user_id = claim_user_id or userId or 0
    if resolved_user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is required for weekly check result."})
    result = get_weekly_check_result(db, resolved_user_id, attempt_id)
    if result is None:
        return JSONResponse(status_code=404, content={"message": "Weekly check result was not found."})
    return result
