-- ReportedIssues: add LeadInvestigatorContact_key to ReportedIssue dimension
-- and add ReportedIssueInvestigationTeamFact table for investigation team members.
-- mart.ETL_ReportedIssueTable and dependent stored procedures are updated via the
-- Types and StoredProcedures DbUp groups which run after schema scripts.

-- Step 1: add LeadInvestigatorContact_key column to mart.ReportedIssue.

IF NOT EXISTS(SELECT 1 FROM sys.columns WHERE [Name] = N'LeadInvestigatorContact_key' AND object_id = OBJECT_ID(N'mart.ReportedIssue'))
BEGIN

    ALTER TABLE mart.ReportedIssue
    ADD LeadInvestigatorContact_key int NULL;

END

GO

-- Step 2: add missing FK constraints omitted in 0022.

IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys WHERE [name] = N'FK_mart.AssetAssignment_mart.Contact_Contact_key' AND parent_object_id = OBJECT_ID(N'mart.AssetAssignment'))
BEGIN

    ALTER TABLE mart.AssetAssignment
    ADD CONSTRAINT [FK_mart.AssetAssignment_mart.Contact_Contact_key]
        FOREIGN KEY (Contact_key) REFERENCES mart.Contact (Contact_key);

END

GO

IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys WHERE [name] = N'FK_mart.InductionTaken_mart.Contact_Contact_key' AND parent_object_id = OBJECT_ID(N'mart.InductionTaken'))
BEGIN

    ALTER TABLE mart.InductionTaken
    ADD CONSTRAINT [FK_mart.InductionTaken_mart.Contact_Contact_key]
        FOREIGN KEY (Contact_key) REFERENCES mart.Contact (Contact_key);

END

GO

IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys WHERE [name] = N'FK_mart.ReportedIssue_mart.Contact_ReportedByContact_key' AND parent_object_id = OBJECT_ID(N'mart.ReportedIssue'))
BEGIN

    ALTER TABLE mart.ReportedIssue
    ADD CONSTRAINT [FK_mart.ReportedIssue_mart.Contact_ReportedByContact_key]
        FOREIGN KEY (ReportedByContact_key) REFERENCES mart.Contact (Contact_key);

END

GO

IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys WHERE [name] = N'FK_mart.SafetyCard_mart.Contact_EmployeeContact_key' AND parent_object_id = OBJECT_ID(N'mart.SafetyCard'))
BEGIN

    ALTER TABLE mart.SafetyCard
    ADD CONSTRAINT [FK_mart.SafetyCard_mart.Contact_EmployeeContact_key]
        FOREIGN KEY (EmployeeContact_key) REFERENCES mart.Contact (Contact_key);

END

GO

-- Step 3: add FK constraint for LeadInvestigatorContact_key.

IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys WHERE [name] = N'FK_mart.ReportedIssue_mart.Contact_LeadInvestigatorContact_key' AND parent_object_id = OBJECT_ID(N'mart.ReportedIssue'))
BEGIN

    ALTER TABLE mart.ReportedIssue
    ADD CONSTRAINT [FK_mart.ReportedIssue_mart.Contact_LeadInvestigatorContact_key]
        FOREIGN KEY (LeadInvestigatorContact_key) REFERENCES mart.Contact (Contact_key);

END

GO

-- Step 4: create mart.ReportedIssueInvestigationTeamFact table.

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE [name] = N'ReportedIssueInvestigationTeamFact' AND [schema_id] = SCHEMA_ID(N'mart'))
BEGIN

    CREATE TABLE mart.ReportedIssueInvestigationTeamFact
    (
        ReportedIssue_key int NOT NULL
        ,Contact_key int NOT NULL
        ,Wallet_key int NOT NULL
        ,_created datetime2(7) NOT NULL CONSTRAINT [DF_mart.ReportedIssueInvestigationTeamFact__created] DEFAULT SYSUTCDATETIME()
        ,_edited datetime2(7) NULL
        ,CONSTRAINT [PK_mart.ReportedIssueInvestigationTeamFact] PRIMARY KEY (ReportedIssue_key, Contact_key)
        ,CONSTRAINT [FK_mart.ReportedIssueInvestigationTeamFact_mart.ReportedIssue_ReportedIssue_key] FOREIGN KEY (ReportedIssue_key) REFERENCES mart.ReportedIssue
        ,CONSTRAINT [FK_mart.ReportedIssueInvestigationTeamFact_mart.Contact_Contact_key] FOREIGN KEY (Contact_key) REFERENCES mart.Contact
        ,CONSTRAINT [FK_mart.ReportedIssueInvestigationTeamFact_mart.Wallet_Wallet_key] FOREIGN KEY (Wallet_key) REFERENCES mart.Wallet
    );

END

GO
