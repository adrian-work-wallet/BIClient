DROP PROCEDURE IF EXISTS mart.ETL_LoadReportedIssuePersonFact2;
GO

CREATE PROCEDURE mart.ETL_LoadReportedIssuePersonFact2
    @reportedIssuePersonTable2 mart.ETL_ReportedIssuePersonTable2 READONLY
    ,@investigation bit
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO mart.ReportedIssuePersonFact2
    (
        -- keys
        ReportedIssuePersonId
        ,Investigation
        ,ReportedIssue_key
        ,ReportedIssuePerson_key
        ,ReportedIssuePersonOptionType_key
        ,Contact_key
        ,Wallet_key
        -- facts
        ,FirstName
        ,LastName
        ,Email
    )
    SELECT
        -- keys
        a.ReportedIssuePersonId
        ,@investigation
        ,ri.ReportedIssue_key
        ,ribo.ReportedIssuePerson_key
        ,pot.ReportedIssuePersonOptionType_key
        ,c.Contact_key
        ,w.Wallet_key
        -- facts
        ,a.FirstName
        ,a.LastName
        ,a.Email
    FROM
        @reportedIssuePersonTable2 AS a
        INNER JOIN mart.ReportedIssue AS ri ON a.ReportedIssueId = ri.ReportedIssueId
        INNER JOIN mart.Wallet AS w ON a.WalletId = w.WalletId
        INNER JOIN mart.ReportedIssuePerson AS ribo ON
            w.Wallet_key = ribo.Wallet_key
            AND a.Question = ribo.Question
            AND a.[Option] = ribo.[Option]
        INNER JOIN mart.ReportedIssuePersonOptionType AS pot ON a.PersonOptionTypeCode = pot.PersonOptionTypeCode
        LEFT JOIN mart.Contact AS c ON a.ContactId = c.ContactId;

    PRINT 'INSERT mart.ReportedIssuePersonFact2, number of rows = ' + CAST(@@ROWCOUNT AS varchar);
END
GO
