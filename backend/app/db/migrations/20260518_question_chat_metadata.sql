IF COL_LENGTH('dbo.ChatConversations', 'QuestionId') IS NULL
BEGIN
    ALTER TABLE dbo.ChatConversations ADD QuestionId INT NULL;
END;

IF COL_LENGTH('dbo.ChatConversations', 'RuntimeQuestionId') IS NULL
BEGIN
    ALTER TABLE dbo.ChatConversations ADD RuntimeQuestionId INT NULL;
END;

IF COL_LENGTH('dbo.ChatConversations', 'AttemptId') IS NULL
BEGIN
    ALTER TABLE dbo.ChatConversations ADD AttemptId INT NULL;
END;

IF COL_LENGTH('dbo.ChatConversations', 'Mode') IS NULL
BEGIN
    ALTER TABLE dbo.ChatConversations ADD Mode NVARCHAR(50) NULL;
END;

IF COL_LENGTH('dbo.ChatConversations', 'Source') IS NULL
BEGIN
    ALTER TABLE dbo.ChatConversations ADD Source NVARCHAR(60) NULL;
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_ChatConversations_User_Question_Attempt'
      AND object_id = OBJECT_ID(N'dbo.ChatConversations')
)
BEGIN
    CREATE INDEX IX_ChatConversations_User_Question_Attempt
    ON dbo.ChatConversations(UserId, Source, QuestionId, RuntimeQuestionId, AttemptId, UpdatedAt DESC);
END;
