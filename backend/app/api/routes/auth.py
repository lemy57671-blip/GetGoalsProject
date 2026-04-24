import json
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.entities import User
from app.schemas.auth import GoogleConfigResponse, GoogleExchangeRequest, GoogleVerifyRequest
from app.services.auth import upsert_google_user, verify_google_token

router = APIRouter(prefix="/api/auth", tags=["default"])


# =========================
# Schemas
# =========================
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember: bool = True


class OnboardingRequest(BaseModel):
    currentScore: Optional[int] = None
    targetScore: Optional[int] = None
    examDate: Optional[str] = None
    studyMinutesPerDay: Optional[int] = None
    weakSkills: Optional[list[str]] = None


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


class ForgotPasswordRequest(BaseModel):
    email: Optional[EmailStr] = None
    emailOrUsername: Optional[str] = None


class ResetPasswordDirectRequest(BaseModel):
    email: Optional[EmailStr] = None
    emailOrUsername: Optional[str] = None
    newPassword: str


# =========================
# Helpers
# =========================
def parse_weak_skills(raw_value) -> list:
    if raw_value is None:
        return []

    if isinstance(raw_value, list):
        return raw_value

    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []

    return []


def serialize_user(user: User) -> dict:
    return {
        "id": user.Id,
        "name": user.Name,
        "email": user.Email,
        "avatarUrl": getattr(user, "AvatarUrl", "") or "",
        "provider": getattr(user, "Provider", "local") or "local",
        "plan": getattr(user, "SubscriptionPlan", "free") or "free",
        "planExpiredAt": getattr(user, "PlanExpiredAt", None),
        "onboardingCompleted": getattr(user, "OnboardingCompleted", False),
        "currentScore": getattr(user, "CurrentScore", None),
        "targetScore": getattr(user, "TargetScore", None),
        "examDate": getattr(user, "ExamDate", None),
        "studyMinutesPerDay": getattr(user, "StudyMinutesPerDay", None),
        "weakSkills": parse_weak_skills(getattr(user, "WeakSkillsJson", "[]")),
        "createdAtUtc": getattr(user, "CreatedAtUtc", None),
    }


def build_auth_response(user: User, remember: bool = True) -> dict:
    expires = timedelta(days=30) if remember else timedelta(days=7)

    token = create_access_token(
        subject=str(user.Id),
        email=user.Email,
        name=user.Name,
        provider=getattr(user, "Provider", "local") or "local",
        onboarding_completed=getattr(user, "OnboardingCompleted", False),
        expires_delta=expires,
    )

    return {
        "token": token,
        "user": serialize_user(user),
    }


# =========================
# Routes
# =========================
@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User)
        .filter(User.Email == payload.email.strip().lower())
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    new_user = User(
        Name=payload.name.strip(),
        Email=payload.email.strip().lower(),
        PasswordHash=hash_password(payload.password),
        AvatarUrl="",
        Provider="local",
        ProviderId=None,
        OnboardingCompleted=False,
        CurrentScore=None,
        TargetScore=None,
        ExamDate=None,
        StudyMinutesPerDay=None,
        WeakSkillsJson="[]",
        SubscriptionPlan="free",
        PlanExpiredAt=None,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return build_auth_response(new_user, remember=True)


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.Email == payload.email.strip().lower())
        .first()
    )

    if not user or not getattr(user, "PasswordHash", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect",
        )

    if not verify_password(payload.password, user.PasswordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect",
        )

    return build_auth_response(user, remember=payload.remember)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return serialize_user(current_user)


@router.post("/onboarding")
def complete_onboarding(
    payload: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.CurrentScore = payload.currentScore
    current_user.TargetScore = payload.targetScore
    current_user.ExamDate = payload.examDate
    current_user.StudyMinutesPerDay = payload.studyMinutesPerDay
    current_user.WeakSkillsJson = json.dumps(payload.weakSkills or [])
    current_user.OnboardingCompleted = True

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {
        "message": "Onboarding completed successfully",
        "user": serialize_user(current_user),
    }


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not getattr(current_user, "PasswordHash", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account does not support password change",
        )

    if not verify_password(payload.currentPassword, current_user.PasswordHash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.PasswordHash = hash_password(payload.newPassword)
    db.add(current_user)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email_or_username = (payload.emailOrUsername or str(payload.email or "")).strip().lower()
    user = (
        db.query(User)
        .filter(User.Email == email_or_username)
        .first()
    )

    # Tạm thời trả message thành công để test UI
    if user:
        return {"message": "Password reset request accepted"}
    return {"message": "Password reset request accepted"}


@router.post("/reset-password-direct")
def reset_password_direct(
    payload: ResetPasswordDirectRequest,
    db: Session = Depends(get_db),
):
    email_or_username = (payload.emailOrUsername or str(payload.email or "")).strip().lower()
    user = (
        db.query(User)
        .filter(User.Email == email_or_username)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.PasswordHash = hash_password(payload.newPassword)
    db.add(user)
    db.commit()

    return {"message": "Password reset successfully"}


@router.get("/google/config", response_model=GoogleConfigResponse)
def google_config():
    client_id = settings.AUTH_GOOGLE_CLIENT_ID.strip()
    return GoogleConfigResponse(
        enabled=bool(client_id),
        clientId=client_id,
    )


@router.post("/google/verify")
async def google_verify(
    payload: GoogleVerifyRequest,
    db: Session = Depends(get_db),
):
    # Chưa verify Google thật, chỉ trả placeholder
    try:
        google_profile = await verify_google_token(payload.credential)
        user = upsert_google_user(
            db,
            GoogleExchangeRequest(
                email=google_profile["email"],
                name=google_profile["name"],
                avatarUrl=google_profile["picture"],
                provider="google",
                providerId=google_profile["sub"],
            ),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google credential is invalid or expired",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return build_auth_response(user, remember=True)
