IF OBJECT_ID(N'dbo.UserQuestionNotes', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserQuestionNotes
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_UserQuestionNotes PRIMARY KEY,
        UserId INT NOT NULL,
        QuestionId INT NOT NULL,
        AttemptId INT NULL,
        NoteText NVARCHAR(MAX) NOT NULL,
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_UserQuestionNotes_CreatedAt DEFAULT SYSUTCDATETIME(),
        UpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_UserQuestionNotes_UpdatedAt DEFAULT SYSUTCDATETIME()
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_UserQuestionNotes_UserId_QuestionId'
      AND object_id = OBJECT_ID(N'dbo.UserQuestionNotes')
)
BEGIN
    CREATE INDEX IX_UserQuestionNotes_UserId_QuestionId
    ON dbo.UserQuestionNotes(UserId, QuestionId);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_UserQuestionNotes_UserId_UpdatedAt'
      AND object_id = OBJECT_ID(N'dbo.UserQuestionNotes')
)
BEGIN
    CREATE INDEX IX_UserQuestionNotes_UserId_UpdatedAt
    ON dbo.UserQuestionNotes(UserId, UpdatedAt DESC);
END;

IF OBJECT_ID(N'dbo.UserQuestionHighlights', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserQuestionHighlights
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_UserQuestionHighlights PRIMARY KEY,
        UserId INT NOT NULL,
        QuestionId INT NOT NULL,
        AttemptId INT NULL,
        TargetType NVARCHAR(50) NOT NULL,
        TargetKey NVARCHAR(20) NULL,
        SelectedText NVARCHAR(MAX) NOT NULL,
        StartOffset INT NULL,
        EndOffset INT NULL,
        Color NVARCHAR(30) NOT NULL CONSTRAINT DF_UserQuestionHighlights_Color DEFAULT N'yellow',
        NoteText NVARCHAR(MAX) NULL,
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_UserQuestionHighlights_CreatedAt DEFAULT SYSUTCDATETIME(),
        UpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_UserQuestionHighlights_UpdatedAt DEFAULT SYSUTCDATETIME()
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_UserQuestionHighlights_UserId_QuestionId'
      AND object_id = OBJECT_ID(N'dbo.UserQuestionHighlights')
)
BEGIN
    CREATE INDEX IX_UserQuestionHighlights_UserId_QuestionId
    ON dbo.UserQuestionHighlights(UserId, QuestionId);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_UserQuestionHighlights_UserId_UpdatedAt'
      AND object_id = OBJECT_ID(N'dbo.UserQuestionHighlights')
)
BEGIN
    CREATE INDEX IX_UserQuestionHighlights_UserId_UpdatedAt
    ON dbo.UserQuestionHighlights(UserId, UpdatedAt DESC);
END;

IF OBJECT_ID(N'dbo.UserQuestionBookmarks', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.UserQuestionBookmarks
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_UserQuestionBookmarks PRIMARY KEY,
        UserId INT NOT NULL,
        QuestionId INT NOT NULL,
        AttemptId INT NULL,
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_UserQuestionBookmarks_CreatedAt DEFAULT SYSUTCDATETIME()
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'UX_UserQuestionBookmarks_UserId_QuestionId'
      AND object_id = OBJECT_ID(N'dbo.UserQuestionBookmarks')
)
BEGIN
    CREATE UNIQUE INDEX UX_UserQuestionBookmarks_UserId_QuestionId
    ON dbo.UserQuestionBookmarks(UserId, QuestionId);
END;
