from __future__ import annotations

import logging
import calendar
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PaymentOrder, User
from app.services.entitlements import has_active_pro


logger = logging.getLogger(__name__)


def normalize_plan_code(plan_code: str | None) -> str:
    value = (plan_code or "").strip().upper()
    return {
        "PRO_MONTHLY": "PRO_MONTHLY",
        "PRO_QUARTERLY": "PRO_QUARTERLY",
        "PRO_YEAR": "PRO_YEARLY",
        "PRO_ANNUAL": "PRO_YEARLY",
        "PRO_YEARLY": "PRO_YEARLY",
    }.get(value, "")


def get_amount_by_plan_code(plan_code: str) -> Decimal:
    return {
        "PRO_MONTHLY": Decimal("99000"),
        "PRO_QUARTERLY": Decimal("249000"),
        "PRO_YEARLY": Decimal("899000"),
    }.get(normalize_plan_code(plan_code), Decimal("0"))


def get_duration_months_by_plan_code(plan_code: str) -> int:
    return {
        "PRO_MONTHLY": 1,
        "PRO_QUARTERLY": 3,
        "PRO_YEARLY": 12,
    }.get(normalize_plan_code(plan_code), 0)


def _add_months(value: datetime, months: int) -> datetime:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def activate_paid_subscription(db: Session, order: PaymentOrder | None) -> None:
    if order is None or order.user_id <= 0:
        logger.warning("PaymentOrder is invalid for subscription activation.")
        return

    user = db.scalar(select(User).where(User.id == order.user_id))
    if user is None:
        logger.warning("User not found for subscription activation. userId=%s orderCode=%s", order.user_id, order.order_code)
        return

    months = get_duration_months_by_plan_code(order.plan_code)
    if months <= 0:
        logger.warning("Invalid plan code for activation. planCode=%s orderCode=%s", order.plan_code, order.order_code)
        return

    now = datetime.utcnow()
    base_time = user.plan_expired_at if user.plan == "pro" and user.plan_expired_at and user.plan_expired_at > now else now
    user.plan = "pro"
    user.plan_expired_at = _add_months(base_time, months)
    db.commit()


def reconcile_paid_order_subscription(db: Session, order: PaymentOrder | None) -> User | None:
    """Repair the user subscription for a paid order without re-extending old orders."""
    if order is None or order.user_id <= 0:
        return None

    user = db.scalar(select(User).where(User.id == order.user_id))
    if user is None:
        return None

    if (order.status or "").strip().lower() != "paid":
        return user

    if has_active_pro(user):
        return user

    months = get_duration_months_by_plan_code(order.plan_code)
    if months <= 0:
        return user

    paid_at = order.paid_at or order.created_at or datetime.utcnow()
    expires_at = _add_months(paid_at, months)
    if expires_at <= datetime.utcnow():
        logger.info(
            "Paid order is outside its entitlement window. orderCode=%s paidAt=%s expiresAt=%s",
            order.order_code,
            paid_at.isoformat() if paid_at else None,
            expires_at.isoformat(),
        )
        return user

    user.plan = "pro"
    user.plan_expired_at = expires_at
    db.commit()
    db.refresh(user)
    logger.info(
        "Reconciled paid order subscription. orderCode=%s userId=%s expiresAt=%s",
        order.order_code,
        user.id,
        expires_at.isoformat(),
    )
    return user


def revoke_expired_subscriptions(db: Session) -> int:
    now = datetime.utcnow()
    expired_users = db.scalars(
        select(User).where(
            User.plan == "pro",
            User.plan_expired_at.is_not(None),
            User.plan_expired_at <= now,
        )
    ).all()
    for user in expired_users:
        user.plan = "free"
    if expired_users:
        db.commit()
    return len(expired_users)
