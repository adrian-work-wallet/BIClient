namespace WorkWallet.BI.ClientDatabaseDeploy;

public class AppSettings
{
    public string? DatabaseConnectionString { get; set; }

    // large existing tables (e.g. an index rebuild migration) can exceed the default; override if needed
    public int SchemaDeploymentTimeoutSeconds { get; set; } = 600;
}
