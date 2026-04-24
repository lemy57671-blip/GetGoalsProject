from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


ThemeMode = Literal["system", "light", "dark"]
LanguageCode = Literal["vi", "en"]


class ExperiencePreferencesDto(BaseModel):
    themeMode: ThemeMode = "system"
    language: LanguageCode = "vi"
    notificationSoundEnabled: bool = True
    autoPlayAudio: bool = True
    autoAiExplanation: bool = True
    updatedAtUtc: datetime | None = None


class UpdateExperiencePreferencesRequest(BaseModel):
    themeMode: ThemeMode
    language: LanguageCode
    notificationSoundEnabled: bool
    autoPlayAudio: bool
    autoAiExplanation: bool


class NotificationPreferencesDto(BaseModel):
    dailyReminderEnabled: bool = True
    weeklyCheckReminderEnabled: bool = True
    emailNotificationsEnabled: bool = False
    reminderTimeLocal: str = "20:00"
    timezone: str = "Asia/Bangkok"
    updatedAtUtc: datetime | None = None


class UpdateNotificationPreferencesRequest(BaseModel):
    dailyReminderEnabled: bool
    weeklyCheckReminderEnabled: bool
    emailNotificationsEnabled: bool
    reminderTimeLocal: str = "20:00"
    timezone: str = "Asia/Bangkok"

    @field_validator("reminderTimeLocal")
    @classmethod
    def validate_time(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("reminderTimeLocal must use HH:MM format")
        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except ValueError as exc:
            raise ValueError("reminderTimeLocal must use HH:MM format") from exc
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("reminderTimeLocal must use HH:MM format")
        return f"{hour:02d}:{minute:02d}"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        cleaned = value.strip() or "Asia/Bangkok"
        if len(cleaned) > 100:
            raise ValueError("timezone is too long")
        return cleaned


class DangerousActionSummaryDto(BaseModel):
    deleted: dict[str, int] = Field(default_factory=dict)
    updated: dict[str, int] = Field(default_factory=dict)
    skipped: list[str] = Field(default_factory=list)


class DangerousActionResultDto(BaseModel):
    success: bool = True
    message: str
    summary: DangerousActionSummaryDto = Field(default_factory=DangerousActionSummaryDto)


class DeleteAccountRequest(BaseModel):
    confirmText: str = ""
