IF OBJECT_ID(N'dbo.Users', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.Users', N'SubscriptionPlan') IS NULL
BEGIN
    ALTER TABLE dbo.Users
    ADD SubscriptionPlan NVARCHAR(50) NOT NULL
        CONSTRAINT DF_Users_SubscriptionPlan DEFAULT N'free';
END;

IF OBJECT_ID(N'dbo.Users', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.Users', N'PlanExpiredAt') IS NULL
BEGIN
    ALTER TABLE dbo.Users
    ADD PlanExpiredAt DATETIME2 NULL;
END;
