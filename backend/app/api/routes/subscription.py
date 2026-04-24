from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User


router = APIRouter()


@router.get("/api/subscription/current")
def get_current_subscription(current_user: User = Depends(get_current_user)) -> dict:
    from app.services.entitlements import has_active_pro

    is_active_pro = has_active_pro(current_user)
    return {
        "plan": "pro" if is_active_pro else "free",
        "planExpiredAt": current_user.plan_expired_at if is_active_pro else None,
    }
