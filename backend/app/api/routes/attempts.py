from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_optional_current_user_id, require_pro_user
from app.db.session import get_db
from app.schemas.attempts import SaveDiagnosticAttemptRequest, SaveMockTestAttemptRequest, SavePracticeAttemptRequest
from app.services.attempts import (
    get_mock_test_attempt_result,
    get_practice_attempt_result,
    save_diagnostic_attempt,
    save_mock_test_attempt,
    save_practice_attempt,
)


router = APIRouter()


@router.post("/api/attempts/practice")
@router.post("/api/Attempts/practice")
def save_practice(
    payload: SavePracticeAttemptRequest,
    db: Session = Depends(get_db),
    claim_user_id: int | None = Depends(get_optional_current_user_id),
):
    user_id = claim_user_id or payload.userId or 0
    if user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is invalid."})
    return save_practice_attempt(db, user_id, payload)


@router.post("/api/attempts/mock-test")
@router.post("/api/Attempts/mock-test")
def save_mock_test(
    payload: SaveMockTestAttemptRequest,
    db: Session = Depends(get_db),
    claim_user_id: int | None = Depends(get_optional_current_user_id),
    _=Depends(require_pro_user),
):
    user_id = claim_user_id or payload.userId or 0
    if user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is invalid."})
    return save_mock_test_attempt(db, user_id, payload)


@router.get("/api/attempts/practice/{attempt_id}")
@router.get("/api/Attempts/practice/{attempt_id}")
def get_practice_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = get_practice_attempt_result(db, user_id, attempt_id)
    if result is None:
        return JSONResponse(status_code=404, content={"message": "Practice attempt result was not found."})
    return result


@router.get("/api/attempts/mock-test/{attempt_id}")
@router.get("/api/Attempts/mock-test/{attempt_id}")
def get_mock_test_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    _=Depends(require_pro_user),
):
    result = get_mock_test_attempt_result(db, user_id, attempt_id)
    if result is None:
        return JSONResponse(status_code=404, content={"message": "Mock test result was not found."})
    return result


@router.post("/api/attempts/diagnostic")
@router.post("/api/Attempts/diagnostic")
def save_diagnostic(
    payload: SaveDiagnosticAttemptRequest,
    db: Session = Depends(get_db),
    claim_user_id: int | None = Depends(get_optional_current_user_id),
):
    user_id = claim_user_id or payload.userId or 0
    if user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is invalid."})
    return save_diagnostic_attempt(db, user_id, payload)
