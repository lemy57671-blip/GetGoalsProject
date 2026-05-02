IF OBJECT_ID(N'dbo.ChatConversations', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ChatConversations (
        Id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        UserId INT NOT NULL,
        Title NVARCHAR(255) NOT NULL CONSTRAINT DF_ChatConversations_Title DEFAULT N'',
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_ChatConversations_CreatedAt DEFAULT SYSUTCDATETIME(),
        UpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_ChatConversations_UpdatedAt DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_ChatConversations_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id)
    );

    CREATE INDEX IX_ChatConversations_UserId_UpdatedAt
        ON dbo.ChatConversations(UserId, UpdatedAt DESC);
END;

IF OBJECT_ID(N'dbo.ChatMessages', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ChatMessages (
        Id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        ConversationId INT NOT NULL,
        UserId INT NOT NULL,
        Role NVARCHAR(20) NOT NULL,
        Content NVARCHAR(MAX) NOT NULL,
        Intent NVARCHAR(100) NULL,
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_ChatMessages_CreatedAt DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_ChatMessages_ChatConversations FOREIGN KEY (ConversationId) REFERENCES dbo.ChatConversations(Id),
        CONSTRAINT FK_ChatMessages_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id)
    );

    CREATE INDEX IX_ChatMessages_ConversationId_CreatedAt
        ON dbo.ChatMessages(ConversationId, CreatedAt ASC);

    CREATE INDEX IX_ChatMessages_UserId_CreatedAt
        ON dbo.ChatMessages(UserId, CreatedAt DESC);
END;
