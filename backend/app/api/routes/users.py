from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User


router = APIRouter()


@router.get("/api/users")
def get_users(db: Session = Depends(get_db)) -> list[dict]:
    users = db.scalars(select(User)).all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "plan": user.plan,
            "onboardingCompleted": user.onboarding_completed,
        }
        for user in users
    ]
