DROP TYPE IF EXISTS mart.ETL_ReportedIssuePersonTable2;
GO

CREATE TYPE mart.ETL_ReportedIssuePersonTable2 AS TABLE
(
    ReportedIssuePersonId uniqueidentifier NOT NULL
    ,ReportedIssueId uniqueidentifier NOT NULL
    ,PersonId uniqueidentifier NOT NULL
    ,OptionId uniqueidentifier NOT NULL
    ,Question nvarchar(500) NOT NULL
    ,[Option] nvarchar(50) NOT NULL
    ,PersonOptionTypeCode int NOT NULL
    ,ContactId uniqueidentifier NULL
    ,FirstName nvarchar(max) NULL
    ,LastName nvarchar(max) NULL
    ,Email nvarchar(max) NULL
    ,WalletId uniqueidentifier NOT NULL
    ,PRIMARY KEY (ReportedIssuePersonId)
);
GO
