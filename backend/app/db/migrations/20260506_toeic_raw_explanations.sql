IF OBJECT_ID(N'dbo.ToeicRawDocuments', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ToeicRawDocuments
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ToeicRawDocuments PRIMARY KEY,
        SourceFile NVARCHAR(260) NOT NULL,
        TestType NVARCHAR(50) NOT NULL,
        TestNumber INT NULL,
        Title NVARCHAR(255) NULL,
        RawText NVARCHAR(MAX) NULL,
        CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_ToeicRawDocuments_CreatedAtUtc DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'dbo.ToeicRawDocuments', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicRawDocuments', N'TestType') IS NULL
BEGIN
    ALTER TABLE dbo.ToeicRawDocuments ADD TestType NVARCHAR(50) NULL;
END;
GO

IF OBJECT_ID(N'dbo.ToeicRawDocuments', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicRawDocuments', N'TestType') IS NOT NULL
BEGIN
    UPDATE dbo.ToeicRawDocuments
    SET TestType = N'unknown'
    WHERE TestType IS NULL;

    ALTER TABLE dbo.ToeicRawDocuments ALTER COLUMN TestType NVARCHAR(50) NOT NULL;
END;
GO

IF OBJECT_ID(N'dbo.ToeicRawDocuments', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicRawDocuments', N'TestNumber') IS NULL
BEGIN
    ALTER TABLE dbo.ToeicRawDocuments ADD TestNumber INT NULL;
END;
GO

IF OBJECT_ID(N'dbo.ToeicRawDocuments', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicRawDocuments', N'Title') IS NULL
BEGIN
    ALTER TABLE dbo.ToeicRawDocuments ADD Title NVARCHAR(255) NULL;
END;
GO

IF OBJECT_ID(N'dbo.ToeicRawDocuments', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicRawDocuments', N'RawText') IS NULL
BEGIN
    ALTER TABLE dbo.ToeicRawDocuments ADD RawText NVARCHAR(MAX) NULL;
END;
GO

IF OBJECT_ID(N'dbo.ToeicRawDocuments', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicRawDocuments', N'CreatedAtUtc') IS NULL
BEGIN
    ALTER TABLE dbo.ToeicRawDocuments ADD CreatedAtUtc DATETIME2 NULL;
END;
GO

IF OBJECT_ID(N'dbo.ToeicRawDocuments', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.ToeicRawDocuments', N'CreatedAtUtc') IS NOT NULL
BEGIN
    UPDATE dbo.ToeicRawDocuments
    SET CreatedAtUtc = COALESCE(CreatedAtUtc, SYSUTCDATETIME())
    WHERE CreatedAtUtc IS NULL;

    IF COL_LENGTH(N'dbo.ToeicRawDocuments', N'ImportedAtUtc') IS NOT NULL
    BEGIN
        UPDATE dbo.ToeicRawDocuments
        SET CreatedAtUtc = COALESCE(ImportedAtUtc, CreatedAtUtc, SYSUTCDATETIME())
        WHERE CreatedAtUtc IS NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.default_constraints
        WHERE parent_object_id = OBJECT_ID(N'dbo.ToeicRawDocuments')
          AND name = N'DF_ToeicRawDocuments_CreatedAtUtc'
    )
    BEGIN
        ALTER TABLE dbo.ToeicRawDocuments
        ADD CONSTRAINT DF_ToeicRawDocuments_CreatedAtUtc DEFAULT SYSUTCDATETIME() FOR CreatedAtUtc;
    END;

    ALTER TABLE dbo.ToeicRawDocuments ALTER COLUMN CreatedAtUtc DATETIME2 NOT NULL;
END;
GO

IF OBJECT_ID(N'dbo.ToeicQuestionExplanations', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ToeicQuestionExplanations
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ToeicQuestionExplanations PRIMARY KEY,
        RawDocumentId INT NULL,
        RuntimeQuestionId INT NULL,
        TestType NVARCHAR(50) NOT NULL,
        TestNumber INT NULL,
        Part INT NULL,
        QuestionNumber INT NULL,
        GroupCode NVARCHAR(100) NULL,
        QuestionText NVARCHAR(MAX) NULL,
        PassageText NVARCHAR(MAX) NULL,
        OptionA NVARCHAR(MAX) NULL,
        OptionB NVARCHAR(MAX) NULL,
        OptionC NVARCHAR(MAX) NULL,
        OptionD NVARCHAR(MAX) NULL,
        CorrectOptionKey NVARCHAR(10) NULL,
        CorrectAnswerText NVARCHAR(MAX) NULL,
        ExplanationText NVARCHAR(MAX) NULL,
        VocabularyNotes NVARCHAR(MAX) NULL,
        GrammarNotes NVARCHAR(MAX) NULL,
        RawBlock NVARCHAR(MAX) NULL,
        CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_ToeicQuestionExplanations_CreatedAtUtc DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'dbo.ToeicRawDocuments', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicQuestionExplanations', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_ToeicQuestionExplanations_RawDocument')
BEGIN
    ALTER TABLE dbo.ToeicQuestionExplanations
    ADD CONSTRAINT FK_ToeicQuestionExplanations_RawDocument
        FOREIGN KEY (RawDocumentId) REFERENCES dbo.ToeicRawDocuments(Id);
END;
GO

IF OBJECT_ID(N'dbo.ToeicQuestionExplanations', N'U') IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM sys.indexes
       WHERE name = N'IX_ToeicQuestionExplanations_TestType_TestNumber_Part_QuestionNumber'
         AND object_id = OBJECT_ID(N'dbo.ToeicQuestionExplanations')
   )
BEGIN
    CREATE INDEX IX_ToeicQuestionExplanations_TestType_TestNumber_Part_QuestionNumber
    ON dbo.ToeicQuestionExplanations(TestType, TestNumber, Part, QuestionNumber);
END;
GO

IF OBJECT_ID(N'dbo.ToeicQuestionExplanations', N'U') IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM sys.indexes
       WHERE name = N'IX_ToeicQuestionExplanations_RuntimeQuestionId'
         AND object_id = OBJECT_ID(N'dbo.ToeicQuestionExplanations')
   )
BEGIN
    CREATE INDEX IX_ToeicQuestionExplanations_RuntimeQuestionId
    ON dbo.ToeicQuestionExplanations(RuntimeQuestionId);
END;
GO

IF OBJECT_ID(N'dbo.ToeicQuestionExplanations', N'U') IS NOT NULL
   AND NOT EXISTS (
       SELECT 1 FROM sys.indexes
       WHERE name = N'IX_ToeicQuestionExplanations_GroupCode'
         AND object_id = OBJECT_ID(N'dbo.ToeicQuestionExplanations')
   )
BEGIN
    CREATE INDEX IX_ToeicQuestionExplanations_GroupCode
    ON dbo.ToeicQuestionExplanations(GroupCode);
END;
GO
