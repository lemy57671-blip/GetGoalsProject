from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.services.learning_analytics import get_review_item_detail, get_review_summary, mark_review_item_reviewed


router = APIRouter()


@router.get("/api/review/summary")
def get_review_summary_route(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if not user_id:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    return get_review_summary(db, user_id)


@router.get("/api/review/item/{review_item_id}")
def get_review_item_route(
    review_item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    item = get_review_item_detail(db, user_id, review_item_id)
    if item is None:
        return JSONResponse(status_code=404, content={"message": "Review item not found."})
    return item


@router.post("/api/review/item/{review_item_id}/mark-reviewed")
def mark_review_item_route(
    review_item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    item = mark_review_item_reviewed(db, user_id, review_item_id)
    if item is None:
        return JSONResponse(status_code=404, content={"message": "Review item not found."})
    return item
