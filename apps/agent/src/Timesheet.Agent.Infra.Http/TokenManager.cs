using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;

namespace Timesheet.Agent.Infra.Http;

/// <summary>
/// Persiste tokens JWT cifrados e decide quando refrescar automaticamente.
/// </summary>
public sealed class TokenManager(
    ConfiguracaoLocalRepository repo,
    ITokenStore store,
    IBackendClient client,
    IClock clock)
{
    private static readonly TimeSpan MargemExpiracao = TimeSpan.FromSeconds(30);

    /// <summary>
    /// Persiste os tokens cifrados e calcula ExpiraEm = now + ExpiresIn.
    /// </summary>
    public async Task SalvarTokensAsync(AuthResult auth, CancellationToken ct = default)
    {
        var cfg = await repo.GetAsync() ?? new ConfiguracaoLocal { BackendBaseUrl = string.Empty };

        cfg.JwtAccessToken = store.Protect(auth.AccessToken);
        cfg.JwtRefreshToken = store.Protect(auth.RefreshToken);
        cfg.ExpiraEm = clock.NowUtc.AddSeconds(auth.ExpiresIn).ToString("o");

        await repo.UpsertAsync(cfg);
    }

    /// <summary>
    /// Retorna o access token válido. Refresca automaticamente se expirado.
    /// Lança AuthException("UNAUTHORIZED") se não houver config ou refresh revogado.
    /// </summary>
    public async Task<string> GetValidAccessTokenAsync(CancellationToken ct = default)
    {
        var cfg = await repo.GetAsync();

        if (cfg is null || string.IsNullOrEmpty(cfg.JwtRefreshToken))
            throw new AuthException("UNAUTHORIZED");

        var expiraEm = DateTimeOffset.Parse(cfg.ExpiraEm!, System.Globalization.CultureInfo.InvariantCulture,
            System.Globalization.DateTimeStyles.AssumeUniversal | System.Globalization.DateTimeStyles.AdjustToUniversal);

        if (expiraEm > clock.NowUtc + MargemExpiracao)
            return store.Unprotect(cfg.JwtAccessToken!);

        // expirado ou dentro da margem — refrescar
        var refreshToken = store.Unprotect(cfg.JwtRefreshToken);
        var novo = await client.RefreshAsync(refreshToken, ct); // propaga AuthException se revogado

        await SalvarTokensAsync(novo, ct);
        return novo.AccessToken;
    }
}
