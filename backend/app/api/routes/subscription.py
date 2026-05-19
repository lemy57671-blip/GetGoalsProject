from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User


router = APIRouter()


@router.get("/api/subscription/current")
def get_current_subscription(current_user: User = Depends(get_current_user)) -> dict:
    from app.services.entitlements import build_entitlement_fields

    return build_entitlement_fields(current_user)
