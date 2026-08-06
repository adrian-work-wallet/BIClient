DROP PROCEDURE IF EXISTS mart.ETL_DeleteAssetObservationFacts;
GO

-- Deletes AssetInspectionObservationFact rows scoped by ObservationId (the AssetInspections2-scoped
-- equivalent is mart.ETL_DeleteAssetInspectionFacts, scoped by InspectionId)
CREATE PROCEDURE mart.ETL_DeleteAssetObservationFacts @observationTable mart.ETL_AssetObservationTable READONLY
AS
BEGIN
    SET NOCOUNT ON;

    DELETE mart.AssetInspectionObservationFact
    FROM mart.AssetInspectionObservationFact AS f
    INNER JOIN mart.AssetObservation AS a ON f.AssetObservation_key = a.AssetObservation_key
    INNER JOIN @observationTable AS x ON a.ObservationId = x.ObservationId;

    PRINT 'DELETE mart.AssetInspectionObservationFact, number of rows = ' + CAST(@@ROWCOUNT AS varchar);
END

GO
