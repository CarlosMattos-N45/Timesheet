namespace Timesheet.Agent.Domain;

public sealed class ConfiguracaoLocal
{
    public int Id { get; init; } = 1;                         // singleton: CHECK (Id = 1)
    public required string BackendBaseUrl { get; set; }
    public string? UltimaSincronizacaoEm { get; set; }
    public string? JwtAccessToken { get; set; }               // DPAPI-protected blob (base64)
    public string? JwtRefreshToken { get; set; }              // DPAPI-protected blob (base64)
    public string? ExpiraEm { get; set; }
}
