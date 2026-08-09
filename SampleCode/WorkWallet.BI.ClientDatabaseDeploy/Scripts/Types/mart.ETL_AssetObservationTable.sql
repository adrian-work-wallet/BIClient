DROP TYPE IF EXISTS mart.ETL_AssetObservationTable;
GO

CREATE TYPE mart.ETL_AssetObservationTable AS TABLE
(
    AssetId uniqueidentifier NOT NULL
    ,ObservationId uniqueidentifier NOT NULL
    ,ObservationStatusCode int NOT NULL -- 0 = observation, 1 = defect (open), 32 = defect (closed)
    ,ObservedOn datetimeoffset(7) NOT NULL
    ,ObservedByContactId uniqueidentifier NULL -- allow NULLs
    ,Deleted bit NOT NULL
    ,ClosedOn datetimeoffset(7) NULL -- allow NULLs
    ,ClosedByContactId uniqueidentifier NULL -- allow NULLs
    ,ClosureNotes nvarchar(max) NOT NULL
    ,WalletId uniqueidentifier NOT NULL
    ,PRIMARY KEY (ObservedOn, ObservationId) -- putting ObservedOn first to order the data load
);
GO
