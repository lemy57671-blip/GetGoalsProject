from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_optional_current_user_id
from app.db.session import get_db
from app.services import toeic as toeic_service


router = APIRouter()


@router.get("/api/toeic/import-status")
def get_import_status(db: Session = Depends(get_db)):
    return toeic_service.get_import_status(db)


@router.get("/api/toeic/summary")
def get_summary(db: Session = Depends(get_db)):
    summary = toeic_service.get_bundle_summary(db)
    if summary is None:
        return JSONResponse(status_code=404, content={"message": "TOEIC question bank has not been imported into SQL Server yet."})
    return summary


@router.get("/api/toeic/recommendations")
def get_recommendations(
    userId: int | None = Query(default=None),
    db: Session = Depends(get_db),
    claim_user_id: int | None = Depends(get_optional_current_user_id),
):
    resolved_user_id = claim_user_id or userId or 0
    if resolved_user_id <= 0:
        return JSONResponse(status_code=401, content={"message": "Authentication is required for TOEIC recommendations."})
    return toeic_service.build_recommendations(db, resolved_user_id)


@router.get("/api/toeic/runner/part/{part}")
def get_runner_by_part(part: int, limit: int = 30, difficulty: str | None = None, currentScore: int | None = None, db: Session = Depends(get_db)):
    if part < 1 or part > 7:
        return JSONResponse(status_code=400, content={"message": "part must be between 1 and 7."})
    if limit <= 0:
        return JSONResponse(status_code=400, content={"message": "limit must be greater than 0."})
    if difficulty and difficulty.strip().lower() not in {"easy", "medium", "hard", "mixed"}:
        return JSONResponse(status_code=400, content={"message": "difficulty must be easy, medium, hard, or mixed."})
    return toeic_service.get_part_runner_questions(db, part, limit, difficulty, currentScore)


@router.get("/api/toeic/runner/mixed")
def get_runner_mixed(parts: str | None = None, count: int = 30, difficulty: str | None = None, currentScore: int | None = None, db: Session = Depends(get_db)):
    if count <= 0:
        return JSONResponse(status_code=400, content={"message": "count must be greater than 0."})
    if difficulty and difficulty.strip().lower() not in {"easy", "medium", "hard", "mixed"}:
        return JSONResponse(status_code=400, content={"message": "difficulty must be easy, medium, hard, or mixed."})
    selected_parts = _parse_parts(parts)
    if not selected_parts:
        return JSONResponse(status_code=400, content={"message": "parts must contain at least one valid part between 1 and 7."})
    return toeic_service.get_mixed_runner_questions(db, selected_parts, count, difficulty, currentScore)


@router.get("/api/toeic/runner/review-focus")
def get_runner_review_focus(
    reviewItemId: int = Query(...),
    count: int = 15,
    difficulty: str | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if reviewItemId <= 0:
        return JSONResponse(status_code=400, content={"message": "reviewItemId must be greater than 0."})
    if count <= 0:
        return JSONResponse(status_code=400, content={"message": "count must be greater than 0."})
    if difficulty and difficulty.strip().lower() not in {"easy", "medium", "hard", "mixed"}:
        return JSONResponse(status_code=400, content={"message": "difficulty must be easy, medium, hard, or mixed."})

    questions = toeic_service.get_review_focus_runner_questions(db, user_id, reviewItemId, count, difficulty)
    if questions is None:
        return JSONResponse(status_code=404, content={"message": "Review item not found."})
    return questions


@router.get("/api/toeic/runner/minitest")
def get_minitest_runner(test: int = 1, parts: str | None = None, count: int | None = None, db: Session = Depends(get_db)):
    if test <= 0:
        return JSONResponse(status_code=400, content={"message": "test must be greater than 0."})
    if count is not None and count <= 0:
        return JSONResponse(status_code=400, content={"message": "count must be greater than 0."})
    selected_parts = _parse_parts(parts)
    if parts and not selected_parts:
        return JSONResponse(status_code=400, content={"message": "parts must contain at least one valid part between 1 and 7."})
    return toeic_service.get_minitest_runner_questions(db, test, selected_parts if parts else None, count)


@router.get("/api/toeic/runner/fulltest")
def get_fulltest_runner(test: int = 1, db: Session = Depends(get_db)):
    if test <= 0:
        return JSONResponse(status_code=400, content={"message": "test must be greater than 0."})
    return toeic_service.get_fulltest_runner_questions(db, test)


def _parse_parts(parts: str | None) -> list[int]:
    if not parts or not parts.strip():
        return [1]
    values = []
    for item in parts.split(","):
        item = item.strip()
        if item.isdigit():
            part = int(item)
            if 1 <= part <= 7 and part not in values:
                values.append(part)
    return values
