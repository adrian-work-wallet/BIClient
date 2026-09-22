-- mart.PermitSignatureFact was clustered on the GUID PermitSignatureId, giving no seek path
-- for the per-permit deletes in mart.ETL_DeletePermitFacts (filtered by Permit_key), and causing
-- fragmentation from clustering on a random GUID. Re-cluster on Permit_key instead.

IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE [name] = N'PK_mart.PermitSignatureFact' AND [parent_object_id] = OBJECT_ID(N'mart.PermitSignatureFact'))
BEGIN

    ALTER TABLE mart.PermitSignatureFact DROP CONSTRAINT [PK_mart.PermitSignatureFact];

END

GO

IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE [name] = N'UQ_mart.PermitSignatureFact_PermitSignatureId' AND [parent_object_id] = OBJECT_ID(N'mart.PermitSignatureFact'))
BEGIN

    -- redundant once the PK below covers the same uniqueness
    ALTER TABLE mart.PermitSignatureFact DROP CONSTRAINT [UQ_mart.PermitSignatureFact_PermitSignatureId];

END

GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE [name] = N'IX_mart.PermitSignatureFact_Permit_key' AND object_id = OBJECT_ID(N'mart.PermitSignatureFact'))
BEGIN

    CREATE CLUSTERED INDEX [IX_mart.PermitSignatureFact_Permit_key] ON mart.PermitSignatureFact (Permit_key);

END

GO

IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE [name] = N'PK_mart.PermitSignatureFact' AND [parent_object_id] = OBJECT_ID(N'mart.PermitSignatureFact'))
BEGIN

    ALTER TABLE mart.PermitSignatureFact ADD CONSTRAINT [PK_mart.PermitSignatureFact] PRIMARY KEY NONCLUSTERED (PermitSignatureId);

END

GO
