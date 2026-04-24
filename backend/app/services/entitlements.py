from __future__ import annotations

from datetime import datetime

from app.models import User


def has_active_pro(user: User | None) -> bool:
    if user is None:
        return False
    return user.plan == "pro" and user.plan_expired_at is not None and user.plan_expired_at > datetime.utcnow()


def build_entitlements(user: User) -> dict:
    is_pro = has_active_pro(user)
    return {
        "plan": "pro" if is_pro else "free",
        "isPro": is_pro,
        "expiresAt": user.plan_expired_at if is_pro else None,
        "features": {
            "aiChatUnlimited": is_pro,
            "mockTestUnlimited": is_pro,
            "analyticsAdvanced": is_pro,
            "roadmapAdvanced": is_pro,
            "reviewNotebook": is_pro,
            "freeQuotaEnabled": not is_pro,
        },
    }
