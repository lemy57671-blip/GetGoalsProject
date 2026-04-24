from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.schemas.settings import (
    DangerousActionResultDto,
    DangerousActionSummaryDto,
    ExperiencePreferencesDto,
    NotificationPreferencesDto,
    UpdateExperiencePreferencesRequest,
    UpdateNotificationPreferencesRequest,
)

logger = logging.getLogger(__name__)


DEFAULT_PREFERENCES = {
    "themeMode": "system",
    "language": "vi",
    "notificationSoundEnabled": True,
    "autoPlayAudio": True,
    "autoAiExplanation": True,
    "dailyReminderEnabled": True,
    "weeklyCheckReminderEnabled": True,
    "emailNotificationsEnabled": False,
    "reminderTimeLocal": "20:00",
    "timezone": "Asia/Bangkok",
}


def ensure_settings_schema(db: Session) -> None:
    statements = [
        """
        IF OBJECT_ID(N'dbo.UserPreferences', N'U') IS NULL
        BEGIN
            CREATE TABLE dbo.UserPreferences (
                Id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
                UserId INT NOT NULL UNIQUE,
                ThemeMode NVARCHAR(20) NOT NULL CONSTRAINT DF_UserPreferences_ThemeMode DEFAULT N'system',
                Language NVARCHAR(10) NOT NULL CONSTRAINT DF_UserPreferences_Language DEFAULT N'vi',
                NotificationSoundEnabled BIT NOT NULL CONSTRAINT DF_UserPreferences_NotificationSoundEnabled DEFAULT 1,
                AutoPlayAudio BIT NOT NULL CONSTRAINT DF_UserPreferences_AutoPlayAudio DEFAULT 1,
                AutoAiExplanation BIT NOT NULL CONSTRAINT DF_UserPreferences_AutoAiExplanation DEFAULT 1,
                DailyReminderEnabled BIT NOT NULL CONSTRAINT DF_UserPreferences_DailyReminderEnabled DEFAULT 1,
                WeeklyCheckReminderEnabled BIT NOT NULL CONSTRAINT DF_UserPreferences_WeeklyCheckReminderEnabled DEFAULT 1,
                EmailNotificationsEnabled BIT NOT NULL CONSTRAINT DF_UserPreferences_EmailNotificationsEnabled DEFAULT 0,
                ReminderTimeLocal NVARCHAR(5) NOT NULL CONSTRAINT DF_UserPreferences_ReminderTimeLocal DEFAULT N'20:00',
                Timezone NVARCHAR(100) NOT NULL CONSTRAINT DF_UserPreferences_Timezone DEFAULT N'Asia/Bangkok',
                CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_UserPreferences_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
                UpdatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_UserPreferences_UpdatedAtUtc DEFAULT SYSUTCDATETIME(),
                CONSTRAINT FK_UserPreferences_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id)
            );
        END
        """,
        """
        IF COL_LENGTH('dbo.Users', 'IsDeleted') IS NULL
        BEGIN
            ALTER TABLE dbo.Users
            ADD IsDeleted BIT NOT NULL CONSTRAINT DF_Users_IsDeleted DEFAULT 0;
        END
        """,
        """
        IF COL_LENGTH('dbo.Users', 'DeletedAtUtc') IS NULL
        BEGIN
            ALTER TABLE dbo.Users ADD DeletedAtUtc DATETIME2 NULL;
        END
        """,
    ]

    for statement in statements:
        db.execute(text(statement))
    db.commit()


def is_user_soft_deleted(db: Session, user_id: int) -> bool:
    try:
        has_column = db.execute(
            text("SELECT CASE WHEN COL_LENGTH('dbo.Users', 'IsDeleted') IS NULL THEN 0 ELSE 1 END")
        ).scalar()
        if not has_column:
            return False
        return bool(
            db.execute(
                text("SELECT IsDeleted FROM dbo.Users WHERE Id = :user_id"),
                {"user_id": user_id},
            ).scalar()
        )
    except SQLAlchemyError:
        logger.warning("Could not check soft-delete status for user %s", user_id, exc_info=True)
        return False


def get_experience_preferences(db: Session, user_id: int) -> ExperiencePreferencesDto:
    row = _get_or_create_preferences(db, user_id)
    return _map_experience(row)


def update_experience_preferences(
    db: Session,
    user_id: int,
    payload: UpdateExperiencePreferencesRequest,
) -> ExperiencePreferencesDto:
    ensure_settings_schema(db)
    db.execute(
        text(
            """
            UPDATE dbo.UserPreferences
            SET ThemeMode = :theme_mode,
                Language = :language,
                NotificationSoundEnabled = :notification_sound_enabled,
                AutoPlayAudio = :auto_play_audio,
                AutoAiExplanation = :auto_ai_explanation,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE UserId = :user_id
            """
        ),
        {
            "user_id": user_id,
            "theme_mode": payload.themeMode,
            "language": payload.language,
            "notification_sound_enabled": payload.notificationSoundEnabled,
            "auto_play_audio": payload.autoPlayAudio,
            "auto_ai_explanation": payload.autoAiExplanation,
        },
    )
    db.commit()
    return get_experience_preferences(db, user_id)


def get_notification_preferences(db: Session, user_id: int) -> NotificationPreferencesDto:
    row = _get_or_create_preferences(db, user_id)
    return _map_notifications(row)


def update_notification_preferences(
    db: Session,
    user_id: int,
    payload: UpdateNotificationPreferencesRequest,
) -> NotificationPreferencesDto:
    ensure_settings_schema(db)
    db.execute(
        text(
            """
            UPDATE dbo.UserPreferences
            SET DailyReminderEnabled = :daily_reminder_enabled,
                WeeklyCheckReminderEnabled = :weekly_check_reminder_enabled,
                EmailNotificationsEnabled = :email_notifications_enabled,
                ReminderTimeLocal = :reminder_time_local,
                Timezone = :timezone,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE UserId = :user_id
            """
        ),
        {
            "user_id": user_id,
            "daily_reminder_enabled": payload.dailyReminderEnabled,
            "weekly_check_reminder_enabled": payload.weeklyCheckReminderEnabled,
            "email_notifications_enabled": payload.emailNotificationsEnabled,
            "reminder_time_local": payload.reminderTimeLocal,
            "timezone": payload.timezone,
        },
    )
    db.commit()
    return get_notification_preferences(db, user_id)


def reset_learning_progress(db: Session, user_id: int) -> DangerousActionResultDto:
    deleted: dict[str, int] = {}
    updated: dict[str, int] = {}
    skipped: list[str] = []

    try:
        _delete_attempt_history(db, user_id, deleted, skipped)
        _delete_user_roadmaps(db, user_id, deleted, skipped)
        _delete_by_user(db, "ProgressLogs", user_id, deleted, skipped)
        _delete_by_user(db, "ReviewQueue", user_id, deleted, skipped)
        _delete_by_user(db, "UserSkillProfiles", user_id, deleted, skipped)
        _delete_by_user(db, "UserPartStats", user_id, deleted, skipped)
        _delete_by_user(db, "UserSkillAnalytics", user_id, deleted, skipped)
        updated["UsersProgressFields"] = _reset_user_progress_fields(db, user_id)
        updated["EnrollmentsProgress"] = _reset_enrollments(db, user_id, skipped)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Reset progress failed for user %s", user_id)
        raise

    return DangerousActionResultDto(
        message="Learning progress reset successfully.",
        summary=DangerousActionSummaryDto(deleted=deleted, updated=updated, skipped=skipped),
    )


def delete_attempt_history(db: Session, user_id: int) -> DangerousActionResultDto:
    deleted: dict[str, int] = {}
    updated: dict[str, int] = {}
    skipped: list[str] = []

    try:
        _delete_attempt_history(db, user_id, deleted, skipped)
        _delete_by_user(db, "ReviewQueue", user_id, deleted, skipped)
        _delete_by_user(db, "UserSkillProfiles", user_id, deleted, skipped)
        _delete_by_user(db, "UserPartStats", user_id, deleted, skipped)
        _delete_by_user(db, "UserSkillAnalytics", user_id, deleted, skipped)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Delete attempt history failed for user %s", user_id)
        raise

    return DangerousActionResultDto(
        message="Attempt history deleted successfully.",
        summary=DangerousActionSummaryDto(deleted=deleted, updated=updated, skipped=skipped),
    )


def soft_delete_account(db: Session, user_id: int) -> DangerousActionResultDto:
    ensure_settings_schema(db)
    deleted: dict[str, int] = {}
    updated: dict[str, int] = {}
    skipped: list[str] = []

    if is_user_soft_deleted(db, user_id):
        return DangerousActionResultDto(
            message="Account was already deactivated.",
            summary=DangerousActionSummaryDto(deleted=deleted, updated={"Users": 0}, skipped=skipped),
        )

    try:
        _delete_attempt_history(db, user_id, deleted, skipped)
        _delete_user_roadmaps(db, user_id, deleted, skipped)
        _delete_by_user(db, "ProgressLogs", user_id, deleted, skipped)
        _delete_by_user(db, "ReviewQueue", user_id, deleted, skipped)
        _delete_by_user(db, "UserSkillProfiles", user_id, deleted, skipped)
        _delete_by_user(db, "UserPartStats", user_id, deleted, skipped)
        _delete_by_user(db, "UserSkillAnalytics", user_id, deleted, skipped)
        _delete_by_user(db, "UserPreferences", user_id, deleted, skipped)
        updated["Users"] = db.execute(
            text(
                """
                UPDATE dbo.Users
                SET IsDeleted = 1,
                    DeletedAtUtc = SYSUTCDATETIME(),
                    Name = N'Deleted User',
                    Email = CONCAT(N'deleted+', Id, N'+', CONVERT(NVARCHAR(36), NEWID()), N'@deleted.local'),
                    PasswordHash = NULL,
                    AvatarUrl = N'',
                    Provider = N'deleted',
                    ProviderId = NULL,
                    SubscriptionPlan = N'free',
                    PlanExpiredAt = NULL,
                    OnboardingCompleted = 0,
                    CurrentScore = NULL,
                    TargetScore = NULL,
                    ExamDate = NULL,
                    StudyMinutesPerDay = NULL,
                    WeakSkillsJson = N'[]'
                WHERE Id = :user_id AND IsDeleted = 0
                """
            ),
            {"user_id": user_id},
        ).rowcount or 0
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Soft delete account failed for user %s", user_id)
        raise

    return DangerousActionResultDto(
        message="Account deactivated successfully.",
        summary=DangerousActionSummaryDto(deleted=deleted, updated=updated, skipped=skipped),
    )


def _get_or_create_preferences(db: Session, user_id: int) -> dict[str, Any]:
    ensure_settings_schema(db)
    row = _select_preferences(db, user_id)
    if row:
        return row

    db.execute(
        text(
            """
            INSERT INTO dbo.UserPreferences (UserId)
            VALUES (:user_id)
            """
        ),
        {"user_id": user_id},
    )
    db.commit()
    row = _select_preferences(db, user_id)
    if row:
        return row
    raise RuntimeError("Unable to create user preferences.")


def _select_preferences(db: Session, user_id: int) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT UserId,
                   ThemeMode,
                   Language,
                   NotificationSoundEnabled,
                   AutoPlayAudio,
                   AutoAiExplanation,
                   DailyReminderEnabled,
                   WeeklyCheckReminderEnabled,
                   EmailNotificationsEnabled,
                   ReminderTimeLocal,
                   Timezone,
                   CreatedAtUtc,
                   UpdatedAtUtc
            FROM dbo.UserPreferences
            WHERE UserId = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    return dict(row) if row else None


def _map_experience(row: dict[str, Any]) -> ExperiencePreferencesDto:
    return ExperiencePreferencesDto(
        themeMode=row.get("ThemeMode") or DEFAULT_PREFERENCES["themeMode"],
        language=row.get("Language") or DEFAULT_PREFERENCES["language"],
        notificationSoundEnabled=bool(row.get("NotificationSoundEnabled")),
        autoPlayAudio=bool(row.get("AutoPlayAudio")),
        autoAiExplanation=bool(row.get("AutoAiExplanation")),
        updatedAtUtc=row.get("UpdatedAtUtc"),
    )


def _map_notifications(row: dict[str, Any]) -> NotificationPreferencesDto:
    return NotificationPreferencesDto(
        dailyReminderEnabled=bool(row.get("DailyReminderEnabled")),
        weeklyCheckReminderEnabled=bool(row.get("WeeklyCheckReminderEnabled")),
        emailNotificationsEnabled=bool(row.get("EmailNotificationsEnabled")),
        reminderTimeLocal=row.get("ReminderTimeLocal") or DEFAULT_PREFERENCES["reminderTimeLocal"],
        timezone=row.get("Timezone") or DEFAULT_PREFERENCES["timezone"],
        updatedAtUtc=row.get("UpdatedAtUtc"),
    )


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(
        db.execute(
            text("SELECT CASE WHEN OBJECT_ID(:table_name, N'U') IS NULL THEN 0 ELSE 1 END"),
            {"table_name": f"dbo.{table_name}"},
        ).scalar()
    )


def _count_by_user(db: Session, table_name: str, user_id: int) -> int:
    return int(
        db.execute(
            text(f"SELECT COUNT(1) FROM dbo.{table_name} WHERE UserId = :user_id"),
            {"user_id": user_id},
        ).scalar()
        or 0
    )


def _delete_by_user(
    db: Session,
    table_name: str,
    user_id: int,
    deleted: dict[str, int],
    skipped: list[str],
) -> int:
    if not _table_exists(db, table_name):
        skipped.append(f"{table_name}: table not found")
        return 0
    count = _count_by_user(db, table_name, user_id)
    db.execute(
        text(f"DELETE FROM dbo.{table_name} WHERE UserId = :user_id"),
        {"user_id": user_id},
    )
    deleted[table_name] = deleted.get(table_name, 0) + count
    return count


def _delete_joined_child(
    db: Session,
    child_table: str,
    child_alias: str,
    parent_table: str,
    parent_alias: str,
    parent_id_column: str,
    child_fk_column: str,
    user_id: int,
    deleted: dict[str, int],
    skipped: list[str],
) -> int:
    if not _table_exists(db, child_table) or not _table_exists(db, parent_table):
        skipped.append(f"{child_table}: required table not found")
        return 0
    count = int(
        db.execute(
            text(
                f"""
                SELECT COUNT(1)
                FROM dbo.{child_table} {child_alias}
                INNER JOIN dbo.{parent_table} {parent_alias}
                    ON {parent_alias}.{parent_id_column} = {child_alias}.{child_fk_column}
                WHERE {parent_alias}.UserId = :user_id
                """
            ),
            {"user_id": user_id},
        ).scalar()
        or 0
    )
    db.execute(
        text(
            f"""
            DELETE {child_alias}
            FROM dbo.{child_table} {child_alias}
            INNER JOIN dbo.{parent_table} {parent_alias}
                ON {parent_alias}.{parent_id_column} = {child_alias}.{child_fk_column}
            WHERE {parent_alias}.UserId = :user_id
            """
        ),
        {"user_id": user_id},
    )
    deleted[child_table] = deleted.get(child_table, 0) + count
    return count


def _delete_attempt_history(
    db: Session,
    user_id: int,
    deleted: dict[str, int],
    skipped: list[str],
) -> None:
    _delete_joined_child(
        db,
        "PracticeAttemptAnswers",
        "a",
        "PracticeAttempts",
        "p",
        "Id",
        "PracticeAttemptId",
        user_id,
        deleted,
        skipped,
    )
    _delete_joined_child(
        db,
        "MockTestAttemptAnswers",
        "a",
        "MockTestAttempts",
        "m",
        "Id",
        "MockTestAttemptId",
        user_id,
        deleted,
        skipped,
    )
    _delete_by_user(db, "PracticeAttempts", user_id, deleted, skipped)
    _delete_by_user(db, "MockTestAttempts", user_id, deleted, skipped)


def _delete_user_roadmaps(
    db: Session,
    user_id: int,
    deleted: dict[str, int],
    skipped: list[str],
) -> None:
    if not all(_table_exists(db, table) for table in ["UserRoadmapWeekItems", "UserRoadmapWeeks", "UserRoadmaps"]):
        skipped.append("UserRoadmaps: required roadmap tables not found")
        return

    week_item_count = int(
        db.execute(
            text(
                """
                SELECT COUNT(1)
                FROM dbo.UserRoadmapWeekItems i
                INNER JOIN dbo.UserRoadmapWeeks w ON w.Id = i.RoadmapWeekId
                INNER JOIN dbo.UserRoadmaps r ON r.Id = w.RoadmapId
                WHERE r.UserId = :user_id
                """
            ),
            {"user_id": user_id},
        ).scalar()
        or 0
    )
    db.execute(
        text(
            """
            DELETE i
            FROM dbo.UserRoadmapWeekItems i
            INNER JOIN dbo.UserRoadmapWeeks w ON w.Id = i.RoadmapWeekId
            INNER JOIN dbo.UserRoadmaps r ON r.Id = w.RoadmapId
            WHERE r.UserId = :user_id
            """
        ),
        {"user_id": user_id},
    )
    deleted["UserRoadmapWeekItems"] = deleted.get("UserRoadmapWeekItems", 0) + week_item_count

    week_count = int(
        db.execute(
            text(
                """
                SELECT COUNT(1)
                FROM dbo.UserRoadmapWeeks w
                INNER JOIN dbo.UserRoadmaps r ON r.Id = w.RoadmapId
                WHERE r.UserId = :user_id
                """
            ),
            {"user_id": user_id},
        ).scalar()
        or 0
    )
    db.execute(
        text(
            """
            DELETE w
            FROM dbo.UserRoadmapWeeks w
            INNER JOIN dbo.UserRoadmaps r ON r.Id = w.RoadmapId
            WHERE r.UserId = :user_id
            """
        ),
        {"user_id": user_id},
    )
    deleted["UserRoadmapWeeks"] = deleted.get("UserRoadmapWeeks", 0) + week_count

    _delete_by_user(db, "UserRoadmaps", user_id, deleted, skipped)


def _reset_user_progress_fields(db: Session, user_id: int) -> int:
    return db.execute(
        text(
            """
            UPDATE dbo.Users
            SET CurrentScore = NULL,
                WeakSkillsJson = N'[]'
            WHERE Id = :user_id
            """
        ),
        {"user_id": user_id},
    ).rowcount or 0


def _reset_enrollments(db: Session, user_id: int, skipped: list[str]) -> int:
    if not _table_exists(db, "Enrollments"):
        skipped.append("Enrollments: table not found")
        return 0
    return db.execute(
        text(
            """
            UPDATE dbo.Enrollments
            SET ProgressPercent = 0
            WHERE UserId = :user_id
            """
        ),
        {"user_id": user_id},
    ).rowcount or 0
