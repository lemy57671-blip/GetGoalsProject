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
END;

IF COL_LENGTH('dbo.Users', 'IsDeleted') IS NULL
BEGIN
    ALTER TABLE dbo.Users
    ADD IsDeleted BIT NOT NULL CONSTRAINT DF_Users_IsDeleted DEFAULT 0;
END;

IF COL_LENGTH('dbo.Users', 'DeletedAtUtc') IS NULL
BEGIN
    ALTER TABLE dbo.Users ADD DeletedAtUtc DATETIME2 NULL;
END;
