from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.errors import pro_required_error, unauthorized_error
from app.core.security import bearer_scheme, decode_access_token, extract_bearer_token
from app.db.session import get_db
from app.models import User


def get_optional_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any] | None:
    if credentials is None:
        return None
    try:
        token = extract_bearer_token(credentials)
        return decode_access_token(token)
    except HTTPException:
        return None


def get_optional_current_user_id(
    payload: dict[str, Any] | None = Depends(get_optional_token_payload),
) -> int | None:
    if not payload:
        return None
    sub = payload.get("sub")
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def get_current_user_id(user_id: int | None = Depends(get_optional_current_user_id)) -> int:
    if not user_id:
        raise unauthorized_error()
    return user_id


def get_current_user(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized_error()
    return user


def require_pro_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.plan == "pro" and current_user.plan_expired_at and current_user.plan_expired_at > datetime.utcnow():
        return current_user
    raise pro_required_error()
