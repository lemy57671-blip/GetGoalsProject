/* Runtime TOEIC review persistence for practice/fulltest/minitest/weeklycheck.
   This script is intentionally idempotent and safe for SQL Server/SSMS/VS.
   Schema changes use dynamic SQL so SQL Server never compiles references to
   columns that are added earlier in the same migration run. */

SET NOCOUNT ON;

IF OBJECT_ID(N'dbo.ReviewQueue', N'U') IS NULL
BEGIN
    EXEC(N'
        CREATE TABLE dbo.ReviewQueue
        (
            Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ReviewQueue PRIMARY KEY,
            UserId INT NOT NULL,
            [Source] NVARCHAR(60) NOT NULL CONSTRAINT DF_ReviewQueue_Source DEFAULT N''practice'',
            AttemptId INT NULL,
            AttemptIdKey AS ISNULL(AttemptId, 0) PERSISTED,
            QuestionId INT NULL,
            RuntimeQuestionId INT NULL,
            DiagnosticQuestionId INT NULL,
            QuestionNumber INT NULL,
            Part INT NULL,
            Section NVARCHAR(50) NULL,
            Skill NVARCHAR(100) NULL,
            SkillCode NVARCHAR(100) NULL,
            ReviewReason NVARCHAR(50) NOT NULL CONSTRAINT DF_ReviewQueue_ReviewReason DEFAULT N''wrong'',
            SelectedOptionKey NVARCHAR(10) NULL,
            CorrectOptionKey NVARCHAR(10) NULL,
            IsCorrect BIT NOT NULL CONSTRAINT DF_ReviewQueue_IsCorrect DEFAULT 0,
            IsSkipped BIT NOT NULL CONSTRAINT DF_ReviewQueue_IsSkipped DEFAULT 0,
            IsActive BIT NOT NULL CONSTRAINT DF_ReviewQueue_IsActive DEFAULT 1,
            LastAnsweredAtUtc DATETIME2 NULL,
            CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_ReviewQueue_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
            UpdatedAtUtc DATETIME2 NULL,
            [Status] NVARCHAR(50) NOT NULL CONSTRAINT DF_ReviewQueue_Status DEFAULT N''pending'',
            SourceAttemptType NVARCHAR(60) NULL,
            SourceAttemptId INT NULL,
            Note NVARCHAR(MAX) NULL,
            AddedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_ReviewQueue_AddedAtUtc DEFAULT SYSUTCDATETIME(),
            ReviewedAtUtc DATETIME2 NULL
        );
    ');
END;

IF OBJECT_ID(N'dbo.ReviewQueue', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH(N'dbo.ReviewQueue', N'Id') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD Id INT IDENTITY(1,1) NOT NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'UserId') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD UserId INT NOT NULL DEFAULT 0 WITH VALUES;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'Source') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD [Source] NVARCHAR(60) NOT NULL DEFAULT N''practice'' WITH VALUES;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'AttemptId') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD AttemptId INT NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'QuestionId') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD QuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'RuntimeQuestionId') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD RuntimeQuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'DiagnosticQuestionId') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD DiagnosticQuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'QuestionNumber') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD QuestionNumber INT NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'Part') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD Part INT NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'Section') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD Section NVARCHAR(50) NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'Skill') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD Skill NVARCHAR(100) NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'SkillCode') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD SkillCode NVARCHAR(100) NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'ReviewReason') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD ReviewReason NVARCHAR(50) NOT NULL DEFAULT N''wrong'' WITH VALUES;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'SelectedOptionKey') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD SelectedOptionKey NVARCHAR(10) NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'CorrectOptionKey') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD CorrectOptionKey NVARCHAR(10) NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'IsCorrect') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD IsCorrect BIT NOT NULL DEFAULT 0 WITH VALUES;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'IsSkipped') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD IsSkipped BIT NOT NULL DEFAULT 0 WITH VALUES;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'IsActive') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD IsActive BIT NOT NULL DEFAULT 1 WITH VALUES;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'LastAnsweredAtUtc') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD LastAnsweredAtUtc DATETIME2 NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'CreatedAtUtc') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD CreatedAtUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'UpdatedAtUtc') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD UpdatedAtUtc DATETIME2 NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'Status') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD [Status] NVARCHAR(50) NOT NULL DEFAULT N''pending'' WITH VALUES;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'SourceAttemptType') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD SourceAttemptType NVARCHAR(60) NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'SourceAttemptId') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD SourceAttemptId INT NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'Note') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD Note NVARCHAR(MAX) NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'AddedAtUtc') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD AddedAtUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'ReviewedAtUtc') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD ReviewedAtUtc DATETIME2 NULL;');
    IF COL_LENGTH(N'dbo.ReviewQueue', N'AttemptId') IS NOT NULL
       AND COL_LENGTH(N'dbo.ReviewQueue', N'AttemptIdKey') IS NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD AttemptIdKey AS ISNULL(AttemptId, 0) PERSISTED;');
END;
GO

SET NOCOUNT ON;

IF OBJECT_ID(N'dbo.ReviewQueue', N'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM sys.key_constraints
        WHERE parent_object_id = OBJECT_ID(N'dbo.ReviewQueue')
          AND [type] = N'PK'
    )
       AND COL_LENGTH(N'dbo.ReviewQueue', N'Id') IS NOT NULL
        EXEC(N'ALTER TABLE dbo.ReviewQueue ADD CONSTRAINT PK_ReviewQueue PRIMARY KEY (Id);');

    IF COL_LENGTH(N'dbo.ReviewQueue', N'QuestionId') IS NOT NULL
        EXEC(N'
            BEGIN TRY
                ALTER TABLE dbo.ReviewQueue ALTER COLUMN QuestionId INT NULL;
            END TRY
            BEGIN CATCH
                PRINT N''ReviewQueue.QuestionId nullable migration skipped.'';
            END CATCH;
        ');

    IF COL_LENGTH(N'dbo.ReviewQueue', N'Source') IS NOT NULL
        EXEC(N'
            UPDATE dbo.ReviewQueue SET [Source] = N''practice'' WHERE [Source] IS NULL OR LTRIM(RTRIM([Source])) = N'''';
            BEGIN TRY
                ALTER TABLE dbo.ReviewQueue ALTER COLUMN [Source] NVARCHAR(60) NOT NULL;
            END TRY
            BEGIN CATCH
                PRINT N''ReviewQueue.Source widen/not-null migration skipped.'';
            END CATCH;
        ');

    IF COL_LENGTH(N'dbo.ReviewQueue', N'ReviewReason') IS NOT NULL
        EXEC(N'
            UPDATE dbo.ReviewQueue SET ReviewReason = N''wrong'' WHERE ReviewReason IS NULL OR LTRIM(RTRIM(ReviewReason)) = N'''';
            BEGIN TRY
                ALTER TABLE dbo.ReviewQueue ALTER COLUMN ReviewReason NVARCHAR(50) NOT NULL;
            END TRY
            BEGIN CATCH
                PRINT N''ReviewQueue.ReviewReason widen/not-null migration skipped.'';
            END CATCH;
        ');

    IF COL_LENGTH(N'dbo.ReviewQueue', N'IsCorrect') IS NOT NULL
        EXEC(N'
            UPDATE dbo.ReviewQueue SET IsCorrect = 0 WHERE IsCorrect IS NULL;
            BEGIN TRY
                ALTER TABLE dbo.ReviewQueue ALTER COLUMN IsCorrect BIT NOT NULL;
            END TRY
            BEGIN CATCH
                PRINT N''ReviewQueue.IsCorrect not-null migration skipped.'';
            END CATCH;
        ');

    IF COL_LENGTH(N'dbo.ReviewQueue', N'IsSkipped') IS NOT NULL
        EXEC(N'
            UPDATE dbo.ReviewQueue SET IsSkipped = 0 WHERE IsSkipped IS NULL;
            BEGIN TRY
                ALTER TABLE dbo.ReviewQueue ALTER COLUMN IsSkipped BIT NOT NULL;
            END TRY
            BEGIN CATCH
                PRINT N''ReviewQueue.IsSkipped not-null migration skipped.'';
            END CATCH;
        ');

    IF COL_LENGTH(N'dbo.ReviewQueue', N'IsActive') IS NOT NULL
        EXEC(N'
            UPDATE dbo.ReviewQueue SET IsActive = 1 WHERE IsActive IS NULL;
            BEGIN TRY
                ALTER TABLE dbo.ReviewQueue ALTER COLUMN IsActive BIT NOT NULL;
            END TRY
            BEGIN CATCH
                PRINT N''ReviewQueue.IsActive not-null migration skipped.'';
            END CATCH;
        ');

    IF COL_LENGTH(N'dbo.ReviewQueue', N'CreatedAtUtc') IS NOT NULL
        EXEC(N'
            UPDATE dbo.ReviewQueue SET CreatedAtUtc = SYSUTCDATETIME() WHERE CreatedAtUtc IS NULL;
            BEGIN TRY
                ALTER TABLE dbo.ReviewQueue ALTER COLUMN CreatedAtUtc DATETIME2 NOT NULL;
            END TRY
            BEGIN CATCH
                PRINT N''ReviewQueue.CreatedAtUtc not-null migration skipped.'';
            END CATCH;
        ');
END;
GO

SET NOCOUNT ON;

IF OBJECT_ID(N'dbo.UserQuestionNotes', N'U') IS NULL
BEGIN
    EXEC(N'
        CREATE TABLE dbo.UserQuestionNotes
        (
            Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_UserQuestionNotes PRIMARY KEY,
            UserId INT NOT NULL,
            QuestionId INT NULL,
            [Source] NVARCHAR(60) NULL,
            AttemptId INT NULL,
            RuntimeQuestionId INT NULL,
            DiagnosticQuestionId INT NULL,
            NoteText NVARCHAR(MAX) NOT NULL DEFAULT N'''',
            CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            UpdatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            CreatedAtUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            UpdatedAtUtc DATETIME2 NULL,
            IsActive BIT NOT NULL DEFAULT 1
        );
    ');
END;

IF OBJECT_ID(N'dbo.UserQuestionHighlights', N'U') IS NULL
BEGIN
    EXEC(N'
        CREATE TABLE dbo.UserQuestionHighlights
        (
            Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_UserQuestionHighlights PRIMARY KEY,
            UserId INT NOT NULL,
            QuestionId INT NULL,
            [Source] NVARCHAR(60) NULL,
            AttemptId INT NULL,
            RuntimeQuestionId INT NULL,
            DiagnosticQuestionId INT NULL,
            TargetType NVARCHAR(50) NOT NULL DEFAULT N''question_text'',
            TargetKey NVARCHAR(20) NULL,
            SelectedText NVARCHAR(MAX) NOT NULL DEFAULT N'''',
            HighlightText NVARCHAR(MAX) NULL,
            StartOffset INT NULL,
            EndOffset INT NULL,
            Color NVARCHAR(30) NOT NULL DEFAULT N''yellow'',
            NoteText NVARCHAR(MAX) NULL,
            CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            UpdatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            CreatedAtUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            UpdatedAtUtc DATETIME2 NULL,
            IsActive BIT NOT NULL DEFAULT 1
        );
    ');
END;

IF OBJECT_ID(N'dbo.UserQuestionBookmarks', N'U') IS NULL
BEGIN
    EXEC(N'
        CREATE TABLE dbo.UserQuestionBookmarks
        (
            Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_UserQuestionBookmarks PRIMARY KEY,
            UserId INT NOT NULL,
            QuestionId INT NULL,
            [Source] NVARCHAR(60) NULL,
            AttemptId INT NULL,
            RuntimeQuestionId INT NULL,
            DiagnosticQuestionId INT NULL,
            CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            CreatedAtUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
            UpdatedAtUtc DATETIME2 NULL,
            IsActive BIT NOT NULL DEFAULT 1
        );
    ');
END;

IF OBJECT_ID(N'dbo.UserQuestionNotes', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'UserId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD UserId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'QuestionId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD QuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'Source') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD [Source] NVARCHAR(60) NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'AttemptId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD AttemptId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'RuntimeQuestionId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD RuntimeQuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'DiagnosticQuestionId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD DiagnosticQuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'NoteText') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD NoteText NVARCHAR(MAX) NOT NULL DEFAULT N'''' WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'CreatedAt') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'UpdatedAt') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD UpdatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'CreatedAtUtc') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD CreatedAtUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'UpdatedAtUtc') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD UpdatedAtUtc DATETIME2 NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'IsActive') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionNotes ADD IsActive BIT NOT NULL DEFAULT 1 WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionNotes', N'Source') IS NOT NULL EXEC(N'BEGIN TRY ALTER TABLE dbo.UserQuestionNotes ALTER COLUMN [Source] NVARCHAR(60) NULL; END TRY BEGIN CATCH PRINT N''UserQuestionNotes.Source widen skipped.''; END CATCH;');
END;

IF OBJECT_ID(N'dbo.UserQuestionHighlights', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'UserId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD UserId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'QuestionId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD QuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'Source') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD [Source] NVARCHAR(60) NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'AttemptId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD AttemptId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'RuntimeQuestionId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD RuntimeQuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'DiagnosticQuestionId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD DiagnosticQuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'TargetType') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD TargetType NVARCHAR(50) NOT NULL DEFAULT N''question_text'' WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'TargetKey') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD TargetKey NVARCHAR(20) NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'SelectedText') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD SelectedText NVARCHAR(MAX) NOT NULL DEFAULT N'''' WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'HighlightText') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD HighlightText NVARCHAR(MAX) NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'StartOffset') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD StartOffset INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'EndOffset') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD EndOffset INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'Color') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD Color NVARCHAR(30) NOT NULL DEFAULT N''yellow'' WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'NoteText') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD NoteText NVARCHAR(MAX) NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'CreatedAt') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'UpdatedAt') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD UpdatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'CreatedAtUtc') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD CreatedAtUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'UpdatedAtUtc') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD UpdatedAtUtc DATETIME2 NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'IsActive') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionHighlights ADD IsActive BIT NOT NULL DEFAULT 1 WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionHighlights', N'Source') IS NOT NULL EXEC(N'BEGIN TRY ALTER TABLE dbo.UserQuestionHighlights ALTER COLUMN [Source] NVARCHAR(60) NULL; END TRY BEGIN CATCH PRINT N''UserQuestionHighlights.Source widen skipped.''; END CATCH;');
END;

IF OBJECT_ID(N'dbo.UserQuestionBookmarks', N'U') IS NOT NULL
BEGIN
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'UserId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD UserId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'QuestionId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD QuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'Source') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD [Source] NVARCHAR(60) NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'AttemptId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD AttemptId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'RuntimeQuestionId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD RuntimeQuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'DiagnosticQuestionId') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD DiagnosticQuestionId INT NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'CreatedAt') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'CreatedAtUtc') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD CreatedAtUtc DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME() WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'UpdatedAtUtc') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD UpdatedAtUtc DATETIME2 NULL;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'IsActive') IS NULL EXEC(N'ALTER TABLE dbo.UserQuestionBookmarks ADD IsActive BIT NOT NULL DEFAULT 1 WITH VALUES;');
    IF COL_LENGTH(N'dbo.UserQuestionBookmarks', N'Source') IS NOT NULL EXEC(N'BEGIN TRY ALTER TABLE dbo.UserQuestionBookmarks ALTER COLUMN [Source] NVARCHAR(60) NULL; END TRY BEGIN CATCH PRINT N''UserQuestionBookmarks.Source widen skipped.''; END CATCH;');
END;
GO

SET NOCOUNT ON;

IF OBJECT_ID(N'dbo.ReviewQueue', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'Source') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'AttemptId') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'RuntimeQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'DiagnosticQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'QuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'Skill') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'SkillCode') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'ReviewReason') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'LastAnsweredAtUtc') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'CreatedAtUtc') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'UpdatedAtUtc') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'AddedAtUtc') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'IsActive') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'IsCorrect') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'IsSkipped') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'Status') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'SourceAttemptType') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'SourceAttemptId') IS NOT NULL
BEGIN
    EXEC(N'
        UPDATE dbo.ReviewQueue
        SET
            [Source] = CASE
                WHEN LOWER(REPLACE(REPLACE(COALESCE([Source], SourceAttemptType, N''''), N''-'', N''''), N''_'', N'''')) IN (N''full'', N''fulltest'', N''mock'', N''mocktest'') THEN N''fulltest''
                WHEN LOWER(REPLACE(REPLACE(COALESCE([Source], SourceAttemptType, N''''), N''-'', N''''), N''_'', N'''')) IN (N''mini'', N''minitest'') THEN N''minitest''
                WHEN LOWER(REPLACE(REPLACE(COALESCE([Source], SourceAttemptType, N''''), N''-'', N''''), N''_'', N'''')) IN (N''weekly'', N''weeklycheck'') THEN N''weeklycheck''
                WHEN LOWER(REPLACE(REPLACE(COALESCE([Source], SourceAttemptType, N''''), N''-'', N''''), N''_'', N'''')) IN (N''diagnostic'', N''placement'', N''placementtest'') THEN N''diagnostic''
                ELSE N''practice''
            END,
            AttemptId = COALESCE(AttemptId, SourceAttemptId),
            SourceAttemptType = COALESCE(SourceAttemptType, [Source]),
            SourceAttemptId = COALESCE(SourceAttemptId, AttemptId),
            SkillCode = COALESCE(SkillCode, Skill),
            ReviewReason = COALESCE(NULLIF(ReviewReason, N''''), N''wrong''),
            CreatedAtUtc = COALESCE(CreatedAtUtc, AddedAtUtc, SYSUTCDATETIME()),
            UpdatedAtUtc = COALESCE(UpdatedAtUtc, AddedAtUtc, CreatedAtUtc, SYSUTCDATETIME()),
            LastAnsweredAtUtc = COALESCE(LastAnsweredAtUtc, UpdatedAtUtc, CreatedAtUtc, AddedAtUtc),
            IsActive = COALESCE(IsActive, 1),
            IsCorrect = COALESCE(IsCorrect, CASE WHEN [Status] = N''reviewed'' THEN 1 ELSE 0 END),
            IsSkipped = COALESCE(IsSkipped, CASE WHEN ReviewReason = N''skipped'' THEN 1 ELSE 0 END)
        WHERE [Source] IS NULL
           OR [Source] NOT IN (N''practice'', N''fulltest'', N''minitest'', N''weeklycheck'', N''diagnostic'')
           OR (AttemptId IS NULL AND SourceAttemptId IS NOT NULL)
           OR SourceAttemptType IS NULL
           OR (SourceAttemptId IS NULL AND AttemptId IS NOT NULL)
           OR (SkillCode IS NULL AND Skill IS NOT NULL)
           OR ReviewReason IS NULL
           OR CreatedAtUtc IS NULL
           OR UpdatedAtUtc IS NULL
           OR LastAnsweredAtUtc IS NULL
           OR IsActive IS NULL
           OR IsCorrect IS NULL
           OR IsSkipped IS NULL;

        UPDATE dbo.ReviewQueue
        SET RuntimeQuestionId = CASE
                WHEN [Source] IN (N''practice'', N''fulltest'', N''minitest'', N''weeklycheck'') THEN COALESCE(RuntimeQuestionId, QuestionId)
                ELSE RuntimeQuestionId
            END,
            DiagnosticQuestionId = CASE
                WHEN [Source] = N''diagnostic'' THEN COALESCE(DiagnosticQuestionId, QuestionId)
                ELSE DiagnosticQuestionId
            END
        WHERE QuestionId IS NOT NULL
          AND (
              ([Source] IN (N''practice'', N''fulltest'', N''minitest'', N''weeklycheck'') AND RuntimeQuestionId IS NULL)
              OR ([Source] = N''diagnostic'' AND DiagnosticQuestionId IS NULL)
          );
    ');
END;

IF OBJECT_ID(N'dbo.ReviewQueue', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicPracticeQuestions', N'Section') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'Source') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'RuntimeQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'QuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'QuestionNumber') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'Part') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'Section') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'SkillCode') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'CorrectOptionKey') IS NOT NULL
BEGIN
    EXEC(N'
        UPDATE rq
        SET
            rq.QuestionId = COALESCE(rq.QuestionId, rq.RuntimeQuestionId),
            rq.QuestionNumber = COALESCE(rq.QuestionNumber, q.QuestionNumber),
            rq.Part = COALESCE(rq.Part, q.Part),
            rq.Section = COALESCE(rq.Section, q.Section),
            rq.SkillCode = COALESCE(rq.SkillCode, q.SkillCode),
            rq.CorrectOptionKey = COALESCE(rq.CorrectOptionKey, q.CorrectOptionKey)
        FROM dbo.ReviewQueue rq
        JOIN dbo.ToeicPracticeQuestions q ON q.Id = rq.RuntimeQuestionId
        WHERE rq.[Source] IN (N''practice'', N''fulltest'', N''minitest'', N''weeklycheck'');
    ');
END;
GO

SET NOCOUNT ON;

IF OBJECT_ID(N'dbo.ReviewQueue', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.PracticeAttemptAnswers', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.PracticeAttempts', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'AttemptIdKey') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicPracticeQuestions', N'Section') IS NOT NULL
BEGIN
    EXEC(N'
        ;WITH practice_review_source AS
        (
            SELECT
                pa.UserId,
                CASE WHEN LOWER(REPLACE(pa.Mode, N''_'', N''-'')) = N''weekly-check'' THEN N''weeklycheck'' ELSE N''practice'' END AS [Source],
                pa.Id AS AttemptId,
                ans.QuestionId AS RuntimeQuestionId,
                ans.QuestionNumber,
                COALESCE(ans.Part, q.Part) AS Part,
                q.Section AS Section,
                COALESCE(ans.Skill, q.SkillCode) AS SkillCode,
                CAST(ans.IsCorrect AS BIT) AS IsCorrect,
                CAST(CASE WHEN ans.SelectedAnswerIndex IS NULL THEN 1 ELSE 0 END AS BIT) AS IsSkipped,
                CASE WHEN ans.SelectedAnswerIndex IS NULL THEN NULL ELSE CHAR(65 + ans.SelectedAnswerIndex) END AS SelectedOptionKey,
                COALESCE(CASE WHEN ans.CorrectAnswerIndex IS NULL THEN NULL ELSE CHAR(65 + ans.CorrectAnswerIndex) END, q.CorrectOptionKey) AS CorrectOptionKey,
                CASE WHEN ans.SelectedAnswerIndex IS NULL THEN N''skipped'' ELSE N''wrong'' END AS ReviewReason,
                COALESCE(pa.SubmittedAtUtc, pa.CreatedAtUtc, ans.CreatedAtUtc, SYSUTCDATETIME()) AS LastAnsweredAtUtc,
                ans.Explanation AS Note
            FROM dbo.PracticeAttemptAnswers ans
            JOIN dbo.PracticeAttempts pa ON pa.Id = ans.PracticeAttemptId
            JOIN dbo.ToeicPracticeQuestions q ON q.Id = ans.QuestionId
            WHERE ans.IsCorrect = 0
        ),
        practice_review_ranked AS
        (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY UserId, [Source], RuntimeQuestionId, ReviewReason, AttemptId
                ORDER BY LastAnsweredAtUtc DESC, AttemptId DESC
            ) AS rn
            FROM practice_review_source
        )
        MERGE dbo.ReviewQueue AS target
        USING (SELECT * FROM practice_review_ranked WHERE rn = 1) AS source
        ON target.UserId = source.UserId
           AND target.[Source] = source.[Source]
           AND target.RuntimeQuestionId = source.RuntimeQuestionId
           AND target.ReviewReason = source.ReviewReason
           AND target.AttemptIdKey = ISNULL(source.AttemptId, 0)
           AND target.IsActive = 1
        WHEN MATCHED AND source.LastAnsweredAtUtc >= COALESCE(target.LastAnsweredAtUtc, ''19000101'') THEN
            UPDATE SET
                AttemptId = source.AttemptId,
                SourceAttemptType = source.[Source],
                SourceAttemptId = source.AttemptId,
                QuestionId = source.RuntimeQuestionId,
                QuestionNumber = source.QuestionNumber,
                Part = source.Part,
                Section = source.Section,
                SkillCode = source.SkillCode,
                IsCorrect = source.IsCorrect,
                IsSkipped = source.IsSkipped,
                SelectedOptionKey = source.SelectedOptionKey,
                CorrectOptionKey = source.CorrectOptionKey,
                LastAnsweredAtUtc = source.LastAnsweredAtUtc,
                UpdatedAtUtc = SYSUTCDATETIME(),
                [Status] = N''pending'',
                Note = COALESCE(source.Note, target.Note)
        WHEN NOT MATCHED BY TARGET THEN
            INSERT
            (
                UserId, [Source], AttemptId, QuestionId, RuntimeQuestionId, DiagnosticQuestionId,
                QuestionNumber, Part, Section, SkillCode, ReviewReason, SelectedOptionKey,
                CorrectOptionKey, IsCorrect, IsSkipped, IsActive, LastAnsweredAtUtc,
                CreatedAtUtc, UpdatedAtUtc, [Status], SourceAttemptType, SourceAttemptId, Note, AddedAtUtc
            )
            VALUES
            (
                source.UserId, source.[Source], source.AttemptId, source.RuntimeQuestionId,
                source.RuntimeQuestionId, NULL, source.QuestionNumber, source.Part, source.Section,
                source.SkillCode, source.ReviewReason, source.SelectedOptionKey, source.CorrectOptionKey,
                source.IsCorrect, source.IsSkipped, 1, source.LastAnsweredAtUtc, source.LastAnsweredAtUtc,
                SYSUTCDATETIME(), N''pending'', source.[Source], source.AttemptId, source.Note, source.LastAnsweredAtUtc
            );
    ');
END;

IF OBJECT_ID(N'dbo.ReviewQueue', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.MockTestAttemptAnswers', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.MockTestAttempts', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticeSets', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'AttemptIdKey') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicPracticeQuestions', N'Section') IS NOT NULL
BEGIN
    EXEC(N'
        ;WITH mock_review_source AS
        (
            SELECT
                ma.UserId,
                CASE
                    WHEN LOWER(REPLACE(REPLACE(ps.[Type], N''-'', N''''), N''_'', N'''')) IN (N''mini'', N''minitest'') THEN N''minitest''
                    ELSE N''fulltest''
                END AS [Source],
                ma.Id AS AttemptId,
                ans.QuestionId AS RuntimeQuestionId,
                ans.QuestionNumber,
                COALESCE(ans.Part, q.Part) AS Part,
                q.Section AS Section,
                COALESCE(ans.Skill, q.SkillCode) AS SkillCode,
                CAST(ans.IsCorrect AS BIT) AS IsCorrect,
                CAST(CASE WHEN ans.SelectedAnswerIndex IS NULL THEN 1 ELSE 0 END AS BIT) AS IsSkipped,
                CASE WHEN ans.SelectedAnswerIndex IS NULL THEN NULL ELSE CHAR(65 + ans.SelectedAnswerIndex) END AS SelectedOptionKey,
                COALESCE(CASE WHEN ans.CorrectAnswerIndex IS NULL THEN NULL ELSE CHAR(65 + ans.CorrectAnswerIndex) END, q.CorrectOptionKey) AS CorrectOptionKey,
                CASE WHEN ans.SelectedAnswerIndex IS NULL THEN N''skipped'' ELSE N''wrong'' END AS ReviewReason,
                COALESCE(ma.SubmittedAtUtc, ma.CreatedAtUtc, SYSUTCDATETIME()) AS LastAnsweredAtUtc,
                ans.Explanation AS Note
            FROM dbo.MockTestAttemptAnswers ans
            JOIN dbo.MockTestAttempts ma ON ma.Id = ans.MockTestAttemptId
            JOIN dbo.ToeicPracticeQuestions q ON q.Id = ans.QuestionId
            JOIN dbo.ToeicPracticeSets ps ON ps.Id = q.SetId
            WHERE ans.IsCorrect = 0
              AND LOWER(REPLACE(REPLACE(ps.[Type], N''-'', N''''), N''_'', N'''')) IN
                  (N''full'', N''fulltest'', N''mock'', N''mocktest'', N''mini'', N''minitest'')
        ),
        mock_review_ranked AS
        (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY UserId, [Source], RuntimeQuestionId, ReviewReason, AttemptId
                ORDER BY LastAnsweredAtUtc DESC, AttemptId DESC
            ) AS rn
            FROM mock_review_source
        )
        MERGE dbo.ReviewQueue AS target
        USING (SELECT * FROM mock_review_ranked WHERE rn = 1) AS source
        ON target.UserId = source.UserId
           AND target.[Source] = source.[Source]
           AND target.RuntimeQuestionId = source.RuntimeQuestionId
           AND target.ReviewReason = source.ReviewReason
           AND target.AttemptIdKey = ISNULL(source.AttemptId, 0)
           AND target.IsActive = 1
        WHEN MATCHED AND source.LastAnsweredAtUtc >= COALESCE(target.LastAnsweredAtUtc, ''19000101'') THEN
            UPDATE SET
                AttemptId = source.AttemptId,
                SourceAttemptType = source.[Source],
                SourceAttemptId = source.AttemptId,
                QuestionId = source.RuntimeQuestionId,
                QuestionNumber = source.QuestionNumber,
                Part = source.Part,
                Section = source.Section,
                SkillCode = source.SkillCode,
                IsCorrect = source.IsCorrect,
                IsSkipped = source.IsSkipped,
                SelectedOptionKey = source.SelectedOptionKey,
                CorrectOptionKey = source.CorrectOptionKey,
                LastAnsweredAtUtc = source.LastAnsweredAtUtc,
                UpdatedAtUtc = SYSUTCDATETIME(),
                [Status] = N''pending'',
                Note = COALESCE(source.Note, target.Note)
        WHEN NOT MATCHED BY TARGET THEN
            INSERT
            (
                UserId, [Source], AttemptId, QuestionId, RuntimeQuestionId, DiagnosticQuestionId,
                QuestionNumber, Part, Section, SkillCode, ReviewReason, SelectedOptionKey,
                CorrectOptionKey, IsCorrect, IsSkipped, IsActive, LastAnsweredAtUtc,
                CreatedAtUtc, UpdatedAtUtc, [Status], SourceAttemptType, SourceAttemptId, Note, AddedAtUtc
            )
            VALUES
            (
                source.UserId, source.[Source], source.AttemptId, source.RuntimeQuestionId,
                source.RuntimeQuestionId, NULL, source.QuestionNumber, source.Part, source.Section,
                source.SkillCode, source.ReviewReason, source.SelectedOptionKey, source.CorrectOptionKey,
                source.IsCorrect, source.IsSkipped, 1, source.LastAnsweredAtUtc, source.LastAnsweredAtUtc,
                SYSUTCDATETIME(), N''pending'', source.[Source], source.AttemptId, source.Note, source.LastAnsweredAtUtc
            );
    ');
END;
GO

SET NOCOUNT ON;

IF OBJECT_ID(N'dbo.ReviewQueue', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'UserId') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'Source') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'RuntimeQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'ReviewReason') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'AttemptIdKey') IS NOT NULL
   AND COL_LENGTH(N'dbo.ReviewQueue', N'IsActive') IS NOT NULL
BEGIN
    EXEC(N'
        ;WITH ranked AS
        (
            SELECT Id,
                   ROW_NUMBER() OVER (
                       PARTITION BY UserId, [Source], RuntimeQuestionId, ReviewReason, AttemptIdKey
                       ORDER BY COALESCE(UpdatedAtUtc, LastAnsweredAtUtc, CreatedAtUtc) DESC, Id DESC
                   ) AS rn
            FROM dbo.ReviewQueue
            WHERE IsActive = 1
              AND RuntimeQuestionId IS NOT NULL
        )
        UPDATE rq
        SET IsActive = 0,
            UpdatedAtUtc = SYSUTCDATETIME()
        FROM dbo.ReviewQueue rq
        JOIN ranked r ON r.Id = rq.Id
        WHERE r.rn > 1;
    ');

    IF EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'UX_ReviewQueue_User_Source_RuntimeQuestion_Reason_Active'
          AND object_id = OBJECT_ID(N'dbo.ReviewQueue')
    )
        EXEC(N'DROP INDEX UX_ReviewQueue_User_Source_RuntimeQuestion_Reason_Active ON dbo.ReviewQueue;');

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'UX_ReviewQueue_User_Source_RuntimeQuestion_Reason_Attempt_Active'
          AND object_id = OBJECT_ID(N'dbo.ReviewQueue')
    )
        EXEC(N'
            CREATE UNIQUE INDEX UX_ReviewQueue_User_Source_RuntimeQuestion_Reason_Attempt_Active
            ON dbo.ReviewQueue(UserId, [Source], RuntimeQuestionId, ReviewReason, AttemptIdKey)
            WHERE IsActive = 1 AND RuntimeQuestionId IS NOT NULL;
        ');

    IF COL_LENGTH(N'dbo.ReviewQueue', N'AttemptId') IS NOT NULL
       AND NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = N'IX_ReviewQueue_User_Source_Attempt'
              AND object_id = OBJECT_ID(N'dbo.ReviewQueue')
       )
        EXEC(N'CREATE INDEX IX_ReviewQueue_User_Source_Attempt ON dbo.ReviewQueue(UserId, [Source], AttemptId, ReviewReason, IsActive);');
END;
GO

SET NOCOUNT ON;

IF OBJECT_ID(N'dbo.UserQuestionNotes', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionNotes', N'Source') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionNotes', N'RuntimeQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionNotes', N'DiagnosticQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionNotes', N'QuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionNotes', N'UpdatedAtUtc') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionNotes', N'IsActive') IS NOT NULL
BEGIN
    EXEC(N'
        UPDATE dbo.UserQuestionNotes
        SET [Source] = CASE
                WHEN [Source] IS NULL OR LTRIM(RTRIM([Source])) = N'''' THEN N''practice''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''full'', N''fulltest'', N''mock'', N''mocktest'') THEN N''fulltest''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''mini'', N''minitest'') THEN N''minitest''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''weekly'', N''weeklycheck'') THEN N''weeklycheck''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''diagnostic'', N''placement'', N''placementtest'') THEN N''diagnostic''
                ELSE [Source]
            END,
            RuntimeQuestionId = CASE WHEN [Source] <> N''diagnostic'' THEN COALESCE(RuntimeQuestionId, QuestionId) ELSE RuntimeQuestionId END,
            DiagnosticQuestionId = CASE WHEN [Source] = N''diagnostic'' THEN COALESCE(DiagnosticQuestionId, QuestionId) ELSE DiagnosticQuestionId END,
            UpdatedAtUtc = COALESCE(UpdatedAtUtc, SYSUTCDATETIME()),
            IsActive = COALESCE(IsActive, 1);
    ');

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'IX_UserQuestionNotes_User_Source_Runtime'
          AND object_id = OBJECT_ID(N'dbo.UserQuestionNotes')
    )
        EXEC(N'CREATE INDEX IX_UserQuestionNotes_User_Source_Runtime ON dbo.UserQuestionNotes(UserId, [Source], RuntimeQuestionId, IsActive);');
END;

IF OBJECT_ID(N'dbo.UserQuestionHighlights', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionHighlights', N'Source') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionHighlights', N'RuntimeQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionHighlights', N'DiagnosticQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionHighlights', N'QuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionHighlights', N'HighlightText') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionHighlights', N'SelectedText') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionHighlights', N'UpdatedAtUtc') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionHighlights', N'IsActive') IS NOT NULL
BEGIN
    EXEC(N'
        UPDATE dbo.UserQuestionHighlights
        SET [Source] = CASE
                WHEN [Source] IS NULL OR LTRIM(RTRIM([Source])) = N'''' THEN N''practice''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''full'', N''fulltest'', N''mock'', N''mocktest'') THEN N''fulltest''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''mini'', N''minitest'') THEN N''minitest''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''weekly'', N''weeklycheck'') THEN N''weeklycheck''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''diagnostic'', N''placement'', N''placementtest'') THEN N''diagnostic''
                ELSE [Source]
            END,
            RuntimeQuestionId = CASE WHEN [Source] <> N''diagnostic'' THEN COALESCE(RuntimeQuestionId, QuestionId) ELSE RuntimeQuestionId END,
            DiagnosticQuestionId = CASE WHEN [Source] = N''diagnostic'' THEN COALESCE(DiagnosticQuestionId, QuestionId) ELSE DiagnosticQuestionId END,
            HighlightText = COALESCE(HighlightText, SelectedText),
            UpdatedAtUtc = COALESCE(UpdatedAtUtc, SYSUTCDATETIME()),
            IsActive = COALESCE(IsActive, 1);
    ');

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'IX_UserQuestionHighlights_User_Source_Runtime'
          AND object_id = OBJECT_ID(N'dbo.UserQuestionHighlights')
    )
        EXEC(N'CREATE INDEX IX_UserQuestionHighlights_User_Source_Runtime ON dbo.UserQuestionHighlights(UserId, [Source], RuntimeQuestionId, IsActive);');
END;

IF OBJECT_ID(N'dbo.UserQuestionBookmarks', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionBookmarks', N'UserId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionBookmarks', N'Source') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionBookmarks', N'RuntimeQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionBookmarks', N'DiagnosticQuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionBookmarks', N'QuestionId') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionBookmarks', N'UpdatedAtUtc') IS NOT NULL
   AND COL_LENGTH(N'dbo.UserQuestionBookmarks', N'IsActive') IS NOT NULL
BEGIN
    EXEC(N'
        UPDATE dbo.UserQuestionBookmarks
        SET [Source] = CASE
                WHEN [Source] IS NULL OR LTRIM(RTRIM([Source])) = N'''' THEN N''practice''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''full'', N''fulltest'', N''mock'', N''mocktest'') THEN N''fulltest''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''mini'', N''minitest'') THEN N''minitest''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''weekly'', N''weeklycheck'') THEN N''weeklycheck''
                WHEN LOWER(REPLACE(REPLACE([Source], N''-'', N''''), N''_'', N'''')) IN (N''diagnostic'', N''placement'', N''placementtest'') THEN N''diagnostic''
                ELSE [Source]
            END,
            RuntimeQuestionId = CASE WHEN [Source] <> N''diagnostic'' THEN COALESCE(RuntimeQuestionId, QuestionId) ELSE RuntimeQuestionId END,
            DiagnosticQuestionId = CASE WHEN [Source] = N''diagnostic'' THEN COALESCE(DiagnosticQuestionId, QuestionId) ELSE DiagnosticQuestionId END,
            UpdatedAtUtc = COALESCE(UpdatedAtUtc, SYSUTCDATETIME()),
            IsActive = COALESCE(IsActive, 1);
    ');

    IF EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'UX_UserQuestionBookmarks_UserId_QuestionId'
          AND object_id = OBJECT_ID(N'dbo.UserQuestionBookmarks')
    )
        EXEC(N'DROP INDEX UX_UserQuestionBookmarks_UserId_QuestionId ON dbo.UserQuestionBookmarks;');

    EXEC(N'
        ;WITH ranked AS
        (
            SELECT Id,
                   ROW_NUMBER() OVER (
                       PARTITION BY UserId, [Source], RuntimeQuestionId
                       ORDER BY UpdatedAtUtc DESC, Id DESC
                   ) AS rn
            FROM dbo.UserQuestionBookmarks
            WHERE IsActive = 1
              AND RuntimeQuestionId IS NOT NULL
        )
        UPDATE b
        SET IsActive = 0,
            UpdatedAtUtc = SYSUTCDATETIME()
        FROM dbo.UserQuestionBookmarks b
        JOIN ranked r ON r.Id = b.Id
        WHERE r.rn > 1;
    ');

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE name = N'UX_UserQuestionBookmarks_User_Source_Runtime_Active'
          AND object_id = OBJECT_ID(N'dbo.UserQuestionBookmarks')
    )
        EXEC(N'
            CREATE UNIQUE INDEX UX_UserQuestionBookmarks_User_Source_Runtime_Active
            ON dbo.UserQuestionBookmarks(UserId, [Source], RuntimeQuestionId)
            WHERE IsActive = 1 AND RuntimeQuestionId IS NOT NULL;
        ');
END;
GO
