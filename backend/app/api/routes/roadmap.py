from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.services.attempt_snapshots import create_attempt_snapshot_for_questions
from app.services.roadmap import complete_week, generate_for_user, get_current_roadmap, get_roadmap_evidence, get_set_questions, get_week_sets, start_week


router = APIRouter()


@router.post("/api/roadmap/generate")
def generate_for_current_user(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    roadmap = generate_for_user(db, user_id)
    if roadmap is None:
        return JSONResponse(
            status_code=409,
            content={
                "message": "Please complete the Placement Test first so we can build your personalized roadmap.",
                "code": "PLACEMENT_TEST_REQUIRED",
            },
        )
    return roadmap


@router.post("/api/roadmap/generate/{user_id}")
def generate(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if user_id != current_user_id:
        return JSONResponse(status_code=403, content={"message": "Roadmap user scope is invalid."})
    roadmap = generate_for_user(db, user_id)
    if roadmap is None:
        return JSONResponse(
            status_code=409,
            content={
                "message": "Please complete the Placement Test first so we can build your personalized roadmap.",
                "code": "PLACEMENT_TEST_REQUIRED",
            },
        )
    return roadmap


@router.get("/api/roadmap/current")
def current_for_current_user(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    roadmap = get_current_roadmap(db, user_id)
    if roadmap is None:
        return JSONResponse(status_code=404, content={"message": "Active roadmap not found."})
    return roadmap


@router.get("/api/roadmap/current/{user_id}")
def current(
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if user_id != current_user_id:
        return JSONResponse(status_code=403, content={"message": "Roadmap user scope is invalid."})
    roadmap = get_current_roadmap(db, user_id)
    if roadmap is None:
        return JSONResponse(status_code=404, content={"message": "Active roadmap not found."})
    return roadmap


@router.get("/api/roadmap/evidence")
def evidence(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return get_roadmap_evidence(db, user_id, limit)


@router.get("/api/roadmap/week/{week_id}/sets")
def week_sets(
    week_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    week = get_week_sets(db, week_id, user_id)
    if week is None:
        return JSONResponse(status_code=404, content={"message": "Roadmap week not found."})
    return week


@router.get("/api/roadmap/week/{week_id}/set/{set_id}")
def set_questions(
    week_id: int,
    set_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    payload = get_set_questions(db, week_id, set_id, user_id)
    if payload is None:
        return JSONResponse(status_code=404, content={"message": "Suggested set not found."})
    snapshot = create_attempt_snapshot_for_questions(
        db,
        user_id=user_id,
        source_type="roadmap",
        source_key=f"roadmap:{week_id}:{set_id}:{payload.setKey}",
        questions=payload.questions,
    )
    payload.attemptId = snapshot.attemptId
    payload.questions = snapshot.questions
    return payload


@router.post("/api/roadmap/week/{week_id}/start")
def start_week_route(
    week_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    week = start_week(db, week_id, user_id)
    if week is None:
        return JSONResponse(status_code=404, content={"message": "Roadmap week not found."})
    return week


@router.post("/api/roadmap/week/{week_id}/complete")
def complete_week_route(
    week_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    week = complete_week(db, week_id, user_id)
    if week is None:
        return JSONResponse(status_code=404, content={"message": "Roadmap week not found."})
    return week
