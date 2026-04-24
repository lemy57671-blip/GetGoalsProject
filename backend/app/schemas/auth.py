from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""


class LoginRequest(BaseModel):
    email: str = ""
    password: str = ""
    remember: bool = True


class ForgotPasswordRequest(BaseModel):
    emailOrUsername: str = ""


class ResetPasswordDirectRequest(BaseModel):
    emailOrUsername: str = ""
    newPassword: str = ""
    confirmPassword: str = ""


class ChangePasswordRequest(BaseModel):
    currentPassword: str = ""
    newPassword: str = ""


class CompleteOnboardingRequest(BaseModel):
    currentScore: int | None = None
    targetScore: int | None = None
    examDate: date | None = None
    studyMinutesPerDay: int | None = None
    weakSkills: list[str] | None = None


class GoogleExchangeRequest(BaseModel):
    email: str = ""
    name: str = ""
    avatarUrl: str = ""
    provider: str = "google"
    providerId: str = ""


class GoogleVerifyRequest(BaseModel):
    credential: str = ""
    device: str = "web"


class GoogleConfigResponse(BaseModel):
    enabled: bool = False
    clientId: str = ""


class AuthUserDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = ""
    email: str = ""
    avatarUrl: str = ""
    provider: str = "local"
    plan: str = "free"
    planExpiredAt: datetime | None = None
    onboardingCompleted: bool = False
    currentScore: int | None = None
    targetScore: int | None = None
    examDate: date | None = None
    studyMinutesPerDay: int | None = None
    weakSkills: list[str] = Field(default_factory=list)
    createdAtUtc: datetime


class AuthResponse(BaseModel):
    token: str
    user: AuthUserDto
