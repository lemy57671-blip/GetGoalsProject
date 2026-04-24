from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.services.entitlements import build_entitlements
from app.services.learning_analytics import get_profile_summary


router = APIRouter()


@router.get("/api/me/entitlements")
def get_entitlements(current_user: User = Depends(get_current_user)) -> dict:
    return build_entitlements(current_user)


@router.get("/api/me/profile-summary")
def get_profile_summary_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary = get_profile_summary(db, current_user.id)
    if summary is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    return summary
