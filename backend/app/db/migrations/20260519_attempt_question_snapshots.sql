IF OBJECT_ID(N'dbo.AttemptQuestionSessions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.AttemptQuestionSessions
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_AttemptQuestionSessions PRIMARY KEY,
        UserId INT NOT NULL,
        SourceType NVARCHAR(50) NOT NULL,
        SourceKey NVARCHAR(255) NOT NULL,
        Status NVARCHAR(50) NOT NULL CONSTRAINT DF_AttemptQuestionSessions_Status DEFAULT N'started',
        SubmittedAttemptId INT NULL,
        CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_AttemptQuestionSessions_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
        UpdatedAtUtc DATETIME2 NULL,
        SubmittedAtUtc DATETIME2 NULL
    );
END
GO

IF OBJECT_ID(N'dbo.AttemptQuestionItems', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.AttemptQuestionItems
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_AttemptQuestionItems PRIMARY KEY,
        AttemptId INT NOT NULL,
        SourceType NVARCHAR(50) NOT NULL,
        UserId INT NOT NULL,
        QuestionId INT NOT NULL,
        OrderIndex INT NOT NULL,
        Repeated BIT NOT NULL CONSTRAINT DF_AttemptQuestionItems_Repeated DEFAULT 0,
        RepeatReason NVARCHAR(100) NULL,
        CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_AttemptQuestionItems_CreatedAtUtc DEFAULT SYSUTCDATETIME()
    );
END
GO

IF OBJECT_ID(N'dbo.AttemptQuestionSessions', N'U') IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM sys.indexes
       WHERE name = N'IX_AttemptQuestionSessions_User_Source_Status'
         AND object_id = OBJECT_ID(N'dbo.AttemptQuestionSessions')
   )
BEGIN
    CREATE INDEX IX_AttemptQuestionSessions_User_Source_Status
    ON dbo.AttemptQuestionSessions(UserId, SourceType, SourceKey, Status, CreatedAtUtc DESC);
END
GO

IF OBJECT_ID(N'dbo.AttemptQuestionItems', N'U') IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM sys.indexes
       WHERE name = N'IX_AttemptQuestionItems_Attempt_Order'
         AND object_id = OBJECT_ID(N'dbo.AttemptQuestionItems')
   )
BEGIN
    CREATE UNIQUE INDEX IX_AttemptQuestionItems_Attempt_Order
    ON dbo.AttemptQuestionItems(AttemptId, OrderIndex);
END
GO

IF OBJECT_ID(N'dbo.AttemptQuestionItems', N'U') IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM sys.indexes
       WHERE name = N'IX_AttemptQuestionItems_User_Question'
         AND object_id = OBJECT_ID(N'dbo.AttemptQuestionItems')
   )
BEGIN
    CREATE INDEX IX_AttemptQuestionItems_User_Question
    ON dbo.AttemptQuestionItems(UserId, QuestionId, SourceType);
END
GO
