from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_id
from app.core.errors import pro_required_error
from app.db.session import get_db
from app.models import User
from app.schemas.attempts import (
    AttemptQuestionStartRequest,
    SaveDiagnosticAttemptRequest,
    SaveMockTestAttemptRequest,
    SavePracticeAttemptRequest,
)
from app.services.entitlements import has_active_pro
from app.services.attempts import (
    get_mock_test_attempt_result,
    get_practice_attempt_result,
    save_diagnostic_attempt,
    save_mock_test_attempt,
    save_practice_attempt,
)
from app.services.attempt_snapshots import resume_attempt_snapshot, start_attempt_snapshot


router = APIRouter()


@router.post("/api/practice/attempts/start")
@router.post("/api/attempts/questions/start")
def start_question_attempt(
    payload: AttemptQuestionStartRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is invalid."})
    return start_attempt_snapshot(db, user_id, payload)


@router.get("/api/practice/attempts/{attempt_id}/questions")
@router.get("/api/attempts/questions/{attempt_id}")
def resume_question_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = resume_attempt_snapshot(db, user_id, attempt_id)
    if result is None:
        return JSONResponse(status_code=404, content={"message": "Attempt question snapshot was not found."})
    return result


@router.post("/api/attempts/practice")
@router.post("/api/Attempts/practice")
def save_practice(
    payload: SavePracticeAttemptRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is invalid."})
    return save_practice_attempt(db, user_id, payload)


@router.post("/api/attempts/mock-test")
@router.post("/api/Attempts/mock-test")
def save_mock_test(
    payload: SaveMockTestAttemptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id
    if user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is invalid."})
    if _requires_pro_attempt(payload.attemptType, payload.source) and not has_active_pro(current_user):
        raise pro_required_error()
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
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id
    result = get_mock_test_attempt_result(db, user_id, attempt_id)
    if result is None:
        return JSONResponse(status_code=404, content={"message": "Mock test result was not found."})
    if _requires_pro_attempt(result.attemptType, None) and not has_active_pro(current_user):
        raise pro_required_error()
    return result


@router.post("/api/attempts/diagnostic")
@router.post("/api/Attempts/diagnostic")
def save_diagnostic(
    payload: SaveDiagnosticAttemptRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if user_id <= 0:
        return JSONResponse(status_code=400, content={"message": "UserId is invalid."})
    return save_diagnostic_attempt(db, user_id, payload)


def _requires_pro_attempt(attempt_type: str | None, source: str | None) -> bool:
    normalized = (attempt_type or source or "").strip().lower().replace("_", "-")
    return normalized in {
        "mini",
        "mini-test",
        "minitest",
        "full",
        "full-test",
        "fulltest",
        "mock",
        "mock-test",
        "mocktest",
    }
