from __future__ import annotations

import logging
import calendar
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PaymentOrder, User


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
    year = base_time.year + (base_time.month - 1 + months) // 12
    month = (base_time.month - 1 + months) % 12 + 1
    day = min(base_time.day, calendar.monthrange(year, month)[1])
    user.plan = "pro"
    user.plan_expired_at = base_time.replace(year=year, month=month, day=day)
    db.commit()


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
