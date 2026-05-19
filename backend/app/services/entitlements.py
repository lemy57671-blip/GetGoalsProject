from __future__ import annotations

from datetime import datetime

from app.models import User


def has_active_pro(user: User | None) -> bool:
    if user is None:
        return False
    plan = (user.plan or "").strip().lower()
    return plan == "pro" and user.plan_expired_at is not None and user.plan_expired_at > datetime.utcnow()


def active_plan_name(user: User | None) -> str:
    return "pro" if has_active_pro(user) else "free"


def subscription_status(user: User | None) -> str:
    if user is None:
        return "free"
    if has_active_pro(user):
        return "active"
    plan = (user.plan or "").strip().lower()
    if plan == "pro" and user.plan_expired_at is not None and user.plan_expired_at <= datetime.utcnow():
        return "expired"
    return "free"


def build_entitlement_fields(user: User | None) -> dict:
    is_pro = has_active_pro(user)
    plan_name = active_plan_name(user)
    status = subscription_status(user)
    expires_at = user.plan_expired_at if user is not None and is_pro else None
    return {
        "plan": plan_name,
        "planName": plan_name,
        "plan_name": plan_name,
        "isPro": is_pro,
        "is_pro": is_pro,
        "subscriptionStatus": status,
        "subscription_status": status,
        "planExpiredAt": expires_at,
        "plan_expired_at": expires_at,
    }


def build_entitlements(user: User) -> dict:
    is_pro = has_active_pro(user)
    plan_name = active_plan_name(user)
    status = subscription_status(user)
    return {
        "plan": plan_name,
        "planName": plan_name,
        "plan_name": plan_name,
        "isPro": is_pro,
        "is_pro": is_pro,
        "subscriptionStatus": status,
        "subscription_status": status,
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
