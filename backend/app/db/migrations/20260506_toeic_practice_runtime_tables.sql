IF OBJECT_ID(N'dbo.ToeicPracticeQuestionAssets', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ToeicPracticeQuestionAssets
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ToeicPracticeQuestionAssets PRIMARY KEY,
        QuestionId INT NULL,
        PassageId INT NULL,
        AssetType NVARCHAR(50) NOT NULL,
        RelativePath NVARCHAR(500) NOT NULL,
        CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_ToeicPracticeQuestionAssets_CreatedAtUtc DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeQuestionOptions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ToeicPracticeQuestionOptions
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ToeicPracticeQuestionOptions PRIMARY KEY,
        QuestionId INT NOT NULL,
        OptionKey NVARCHAR(10) NOT NULL,
        OptionText NVARCHAR(MAX) NOT NULL,
        SortOrder INT NOT NULL,
        IsCorrect BIT NOT NULL CONSTRAINT DF_ToeicPracticeQuestionOptions_IsCorrect DEFAULT 0
    );
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ToeicPracticeQuestions
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ToeicPracticeQuestions PRIMARY KEY,
        SetId INT NOT NULL,
        PassageId INT NULL,
        TestNumber INT NULL,
        Part INT NOT NULL,
        Section NVARCHAR(50) NULL,
        QuestionNumber INT NULL,
        QuestionText NVARCHAR(MAX) NULL,
        CorrectOptionKey NVARCHAR(10) NULL,
        Explanation NVARCHAR(MAX) NULL,
        Difficulty NVARCHAR(50) NULL,
        SkillCode NVARCHAR(100) NULL,
        SortOrder INT NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_ToeicPracticeQuestions_IsActive DEFAULT 1,
        CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_ToeicPracticeQuestions_CreatedAtUtc DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticePassages', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ToeicPracticePassages
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ToeicPracticePassages PRIMARY KEY,
        SetId INT NOT NULL,
        Part INT NOT NULL,
        GroupCode NVARCHAR(100) NULL,
        PassageText NVARCHAR(MAX) NULL,
        AudioPath NVARCHAR(500) NULL,
        ImagePath NVARCHAR(500) NULL,
        CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_ToeicPracticePassages_CreatedAtUtc DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeSets', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ToeicPracticeSets
    (
        Id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ToeicPracticeSets PRIMARY KEY,
        Code NVARCHAR(100) NOT NULL,
        Title NVARCHAR(255) NOT NULL,
        Type NVARCHAR(50) NOT NULL,
        TestNumber INT NULL,
        Part INT NULL,
        Description NVARCHAR(MAX) NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_ToeicPracticeSets_IsActive DEFAULT 1,
        CreatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_ToeicPracticeSets_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
        UpdatedAtUtc DATETIME2 NOT NULL CONSTRAINT DF_ToeicPracticeSets_UpdatedAtUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_ToeicPracticeSets_Code UNIQUE (Code)
    );
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeSets', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_ToeicPracticeQuestions_Set')
BEGIN
    ALTER TABLE dbo.ToeicPracticeQuestions
    ADD CONSTRAINT FK_ToeicPracticeQuestions_Set
        FOREIGN KEY (SetId) REFERENCES dbo.ToeicPracticeSets(Id);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeSets', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticePassages', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_ToeicPracticePassages_Set')
BEGIN
    ALTER TABLE dbo.ToeicPracticePassages
    ADD CONSTRAINT FK_ToeicPracticePassages_Set
        FOREIGN KEY (SetId) REFERENCES dbo.ToeicPracticeSets(Id);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticePassages', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_ToeicPracticeQuestions_Passage')
BEGIN
    ALTER TABLE dbo.ToeicPracticeQuestions
    ADD CONSTRAINT FK_ToeicPracticeQuestions_Passage
        FOREIGN KEY (PassageId) REFERENCES dbo.ToeicPracticePassages(Id);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticeQuestionOptions', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_ToeicPracticeQuestionOptions_Question')
BEGIN
    ALTER TABLE dbo.ToeicPracticeQuestionOptions
    ADD CONSTRAINT FK_ToeicPracticeQuestionOptions_Question
        FOREIGN KEY (QuestionId) REFERENCES dbo.ToeicPracticeQuestions(Id);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticeQuestionAssets', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_ToeicPracticeQuestionAssets_Question')
BEGIN
    ALTER TABLE dbo.ToeicPracticeQuestionAssets
    ADD CONSTRAINT FK_ToeicPracticeQuestionAssets_Question
        FOREIGN KEY (QuestionId) REFERENCES dbo.ToeicPracticeQuestions(Id);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticePassages', N'U') IS NOT NULL
   AND OBJECT_ID(N'dbo.ToeicPracticeQuestionAssets', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = N'FK_ToeicPracticeQuestionAssets_Passage')
BEGIN
    ALTER TABLE dbo.ToeicPracticeQuestionAssets
    ADD CONSTRAINT FK_ToeicPracticeQuestionAssets_Passage
        FOREIGN KEY (PassageId) REFERENCES dbo.ToeicPracticePassages(Id);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ToeicPracticeQuestions_SetId_Part_QuestionNumber' AND object_id = OBJECT_ID(N'dbo.ToeicPracticeQuestions'))
BEGIN
    CREATE INDEX IX_ToeicPracticeQuestions_SetId_Part_QuestionNumber
    ON dbo.ToeicPracticeQuestions(SetId, Part, QuestionNumber);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeQuestions', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ToeicPracticeQuestions_Part' AND object_id = OBJECT_ID(N'dbo.ToeicPracticeQuestions'))
BEGIN
    CREATE INDEX IX_ToeicPracticeQuestions_Part
    ON dbo.ToeicPracticeQuestions(Part);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeQuestionOptions', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ToeicPracticeQuestionOptions_QuestionId' AND object_id = OBJECT_ID(N'dbo.ToeicPracticeQuestionOptions'))
BEGIN
    CREATE INDEX IX_ToeicPracticeQuestionOptions_QuestionId
    ON dbo.ToeicPracticeQuestionOptions(QuestionId);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticeQuestionAssets', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ToeicPracticeQuestionAssets_QuestionId' AND object_id = OBJECT_ID(N'dbo.ToeicPracticeQuestionAssets'))
BEGIN
    CREATE INDEX IX_ToeicPracticeQuestionAssets_QuestionId
    ON dbo.ToeicPracticeQuestionAssets(QuestionId);
END;
GO

IF OBJECT_ID(N'dbo.ToeicPracticePassages', N'U') IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_ToeicPracticePassages_SetId_Part' AND object_id = OBJECT_ID(N'dbo.ToeicPracticePassages'))
BEGIN
    CREATE INDEX IX_ToeicPracticePassages_SetId_Part
    ON dbo.ToeicPracticePassages(SetId, Part);
END;
GO
