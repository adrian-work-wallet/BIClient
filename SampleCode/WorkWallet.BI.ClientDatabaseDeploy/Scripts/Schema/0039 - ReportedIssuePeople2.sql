-- ReportedIssuePeople2 / ReportedIssueInvestigationPeople2: enriched person-response detail
-- (PersonOptionTypeCode, ContactId, FirstName, LastName, Email). The original
-- ReportedIssuePeople/ReportedIssueInvestigationPeople datasets and mart.ReportedIssuePerson/
-- mart.ReportedIssuePersonFact are unaffected - this adds new tables only.

CREATE TABLE mart.ReportedIssuePersonOptionType
(
    ReportedIssuePersonOptionType_key int IDENTITY
    ,PersonOptionTypeCode int NOT NULL /* business key */
    ,PersonOptionType nvarchar(50) NOT NULL
    ,_created datetime2(7) NOT NULL CONSTRAINT [DF_mart.ReportedIssuePersonOptionType__created] DEFAULT SYSUTCDATETIME()
    ,_edited datetime2(7) NULL
    ,CONSTRAINT [PK_mart.ReportedIssuePersonOptionType] PRIMARY KEY (ReportedIssuePersonOptionType_key)
    ,CONSTRAINT [UQ_mart.ReportedIssuePersonOptionType_Code] UNIQUE(PersonOptionTypeCode)
);

INSERT INTO mart.ReportedIssuePersonOptionType (PersonOptionTypeCode, PersonOptionType) VALUES (1, N'Other');
INSERT INTO mart.ReportedIssuePersonOptionType (PersonOptionTypeCode, PersonOptionType) VALUES (2, N'Contact');
INSERT INTO mart.ReportedIssuePersonOptionType (PersonOptionTypeCode, PersonOptionType) VALUES (3, N'User');

-- Keyed on the source response row id (ReportedIssuePersonId/ReportedIssueInvestigationPersonId)
-- rather than Question/Option, since a question/option can have multiple people selected.
CREATE TABLE mart.ReportedIssuePersonFact2
(
    ReportedIssuePersonId uniqueidentifier NOT NULL /* business key */
    ,Investigation bit NOT NULL
    ,ReportedIssue_key int NOT NULL
    ,ReportedIssuePerson_key int NOT NULL
    ,ReportedIssuePersonOptionType_key int NOT NULL
    ,Contact_key int NULL
    ,FirstName nvarchar(max) NULL
    ,LastName nvarchar(max) NULL
    ,Email nvarchar(max) NULL
    ,Wallet_key int NOT NULL
    ,_created datetime2(7) NOT NULL CONSTRAINT [DF_mart.ReportedIssuePersonFact2__created] DEFAULT SYSUTCDATETIME()
    ,_edited datetime2(7) NULL
    ,CONSTRAINT [PK_mart.ReportedIssuePersonFact2] PRIMARY KEY (ReportedIssuePersonId, Investigation)
    ,CONSTRAINT [FK_mart.ReportedIssuePersonFact2_mart.ReportedIssue_ReportedIssue_key] FOREIGN KEY(ReportedIssue_key) REFERENCES mart.ReportedIssue
    ,CONSTRAINT [FK_mart.ReportedIssuePersonFact2_mart.ReportedIssuePerson_ReportedIssuePerson_key] FOREIGN KEY(ReportedIssuePerson_key) REFERENCES mart.ReportedIssuePerson
    ,CONSTRAINT [FK_mart.ReportedIssuePersonFact2_mart.ReportedIssuePersonOptionType_ReportedIssuePersonOptionType_key] FOREIGN KEY(ReportedIssuePersonOptionType_key) REFERENCES mart.ReportedIssuePersonOptionType
    ,CONSTRAINT [FK_mart.ReportedIssuePersonFact2_mart.Contact_Contact_key] FOREIGN KEY(Contact_key) REFERENCES mart.Contact
    ,CONSTRAINT [FK_mart.ReportedIssuePersonFact2_mart.Wallet_Wallet_key] FOREIGN KEY(Wallet_key) REFERENCES mart.Wallet
);

GO
