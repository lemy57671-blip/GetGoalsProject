from __future__ import annotations

import json
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import AuthResponse, AuthUserDto, CompleteOnboardingRequest, GoogleExchangeRequest
from app.utils.json_helpers import parse_string_list

GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def map_user(user: User) -> AuthUserDto:
    return AuthUserDto(
        id=user.id,
        name=user.name,
        email=user.email,
        avatarUrl=user.avatar_url,
        provider=user.provider,
        plan=user.plan,
        planExpiredAt=user.plan_expired_at,
        onboardingCompleted=user.onboarding_completed,
        currentScore=user.current_score,
        targetScore=user.target_score,
        examDate=user.exam_date,
        studyMinutesPerDay=user.study_minutes_per_day,
        weakSkills=parse_string_list(user.weak_skills_json),
        createdAtUtc=user.created_at_utc,
    )


def build_auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        token=create_access_token(
            subject=str(user.id),
            email=user.email,
            name=user.name,
            provider=user.provider,
            onboarding_completed=user.onboarding_completed,
        ),
        user=map_user(user),
    )


def register_user(db: Session, name: str, email: str, password: str) -> AuthResponse:
    user = User(
        name=name,
        email=email,
        provider="local",
        created_at_utc=datetime.utcnow(),
        onboarding_completed=False,
        password_hash=hash_password(password),
        avatar_url="",
        weak_skills_json="[]",
        plan="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return build_auth_response(user)


def login_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        return None
    if user.provider != "local":
        raise ValueError("This account uses Google sign-in")
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at_utc = datetime.utcnow()
    db.commit()
    return user


def update_onboarding(db: Session, user: User, request: CompleteOnboardingRequest) -> AuthResponse:
    user.current_score = request.currentScore
    user.target_score = request.targetScore
    user.exam_date = request.examDate
    user.study_minutes_per_day = request.studyMinutesPerDay
    user.weak_skills_json = json.dumps(list(dict.fromkeys(item.strip() for item in (request.weakSkills or []) if item and item.strip())))
    user.onboarding_completed = True
    db.commit()
    db.refresh(user)
    return build_auth_response(user)


def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
    if user.provider != "local":
        raise ValueError("Google account cannot change password here")
    if not verify_password(current_password, user.password_hash):
        return False
    user.password_hash = hash_password(new_password)
    db.commit()
    return True


def upsert_google_user(db: Session, request: GoogleExchangeRequest) -> User:
    provider_id = (request.providerId or "").strip()
    email = (request.email or "").strip().lower()
    user = db.scalar(select(User).where(User.provider_id == provider_id)) if provider_id else None

    if user is None and email:
        user = db.scalar(select(User).where(User.email == email))
        if user and user.provider_id and user.provider_id != provider_id:
            raise ValueError("Email is already linked to a different Google account")

    if user is None:
        user = User(
            email=email,
            name=request.name.strip() if request.name.strip() else email.split("@")[0],
            avatar_url=request.avatarUrl.strip(),
            provider="google",
            provider_id=provider_id or None,
            onboarding_completed=False,
            created_at_utc=datetime.utcnow(),
            password_hash="",
            weak_skills_json="[]",
            plan="free",
        )
        db.add(user)
    else:
        if email and not user.email:
            user.email = email
        user.name = request.name.strip() if request.name.strip() else user.name
        user.avatar_url = request.avatarUrl.strip() or user.avatar_url
        if provider_id:
            user.provider_id = provider_id
        if user.provider != "local" or not user.password_hash:
            user.provider = "google"
    user.last_login_at_utc = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def _google_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


async def verify_google_token(id_token: str) -> dict:
    credential = (id_token or "").strip()
    client_id = settings.AUTH_GOOGLE_CLIENT_ID.strip()

    if not client_id:
        raise RuntimeError("Google sign-in is not configured")

    if not credential:
        raise PermissionError("Missing Google credential")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": credential},
            )
            payload = response.text
            if response.status_code >= 400:
                raise PermissionError(payload)
    except httpx.HTTPError as exc:
        raise RuntimeError("Google token verification is temporarily unavailable") from exc

    try:
        token_payload = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PermissionError("Google token verification failed") from exc
    issuer = str(token_payload.get("iss", "")).strip()
    audience = str(token_payload.get("aud", "")).strip()
    subject = str(token_payload.get("sub", "")).strip()
    email = str(token_payload.get("email", "")).strip().lower()
    expires_at = str(token_payload.get("exp", "")).strip()

    if audience != client_id:
        raise PermissionError("Google token audience mismatch")

    if issuer not in GOOGLE_ISSUERS:
        raise PermissionError("Google token issuer mismatch")

    if expires_at.isdigit() and int(expires_at) <= int(datetime.utcnow().timestamp()):
        raise PermissionError("Google token has expired")

    if not subject:
        raise PermissionError("Google token missing subject")

    if not email or not _google_bool(token_payload.get("email_verified")):
        raise PermissionError("Google account email is not verified")

    return {
        "sub": subject,
        "email": email,
        "name": str(token_payload.get("name", "")).strip(),
        "picture": str(token_payload.get("picture", "")).strip(),
        "given_name": str(token_payload.get("given_name", "")).strip(),
        "family_name": str(token_payload.get("family_name", "")).strip(),
        "issuer": issuer,
    }
