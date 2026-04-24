from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.settings import (
    DangerousActionResultDto,
    DeleteAccountRequest,
    ExperiencePreferencesDto,
    NotificationPreferencesDto,
    UpdateExperiencePreferencesRequest,
    UpdateNotificationPreferencesRequest,
)
from app.services.settings import (
    delete_attempt_history,
    get_experience_preferences,
    get_notification_preferences,
    reset_learning_progress,
    soft_delete_account,
    update_experience_preferences,
    update_notification_preferences,
)


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/preferences", response_model=ExperiencePreferencesDto)
def read_preferences(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return get_experience_preferences(db, user_id)


@router.put("/preferences", response_model=ExperiencePreferencesDto)
def save_preferences(
    payload: UpdateExperiencePreferencesRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return update_experience_preferences(db, user_id, payload)


@router.get("/notifications", response_model=NotificationPreferencesDto)
def read_notifications(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return get_notification_preferences(db, user_id)


@router.put("/notifications", response_model=NotificationPreferencesDto)
def save_notifications(
    payload: UpdateNotificationPreferencesRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return update_notification_preferences(db, user_id, payload)


@router.post("/reset-progress", response_model=DangerousActionResultDto)
def reset_progress(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return reset_learning_progress(db, user_id)


@router.post("/delete-history", response_model=DangerousActionResultDto)
def delete_history(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return delete_attempt_history(db, user_id)


@router.delete("/account", response_model=DangerousActionResultDto)
def delete_account(
    payload: DeleteAccountRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if payload.confirmText != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirmText must be DELETE",
        )

    return soft_delete_account(db, user_id)
