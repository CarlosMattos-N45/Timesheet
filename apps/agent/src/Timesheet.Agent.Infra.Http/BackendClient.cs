using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Timesheet.Agent.Domain;

namespace Timesheet.Agent.Infra.Http;

public interface IBackendClient
{
    Task<AuthResult> LoginAsync(string email, string senha, CancellationToken ct = default);
    Task<AuthResult> RefreshAsync(string refreshToken, CancellationToken ct = default);
    Task<CreateTerceiroResult> CreateTerceiroAsync(CreateTerceiroDto dto, CancellationToken ct = default);
    Task<SyncOutcome> PostMarcacaoAsync(MarcacaoLocal m, string accessToken, CancellationToken ct = default);
    Task<bool> IsHealthyAsync(CancellationToken ct = default);
    Task<bool> IsReadyAsync(CancellationToken ct = default);
}

public sealed class BackendClient : IBackendClient
{
    private readonly HttpClient _http;

    private static readonly JsonSerializerOptions JsonOpts = new(JsonSerializerDefaults.Web);

    public BackendClient(HttpClient http)
    {
        _http = http;
    }

    public async Task<AuthResult> LoginAsync(string email, string senha, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync("/api/v1/auth/login", new LoginRequestDto(email, senha), JsonOpts, ct);

        if (resp.StatusCode == HttpStatusCode.Unauthorized)
        {
            var err = await ReadApiError(resp, ct);
            throw new AuthException(err?.Code ?? "UNAUTHORIZED", err?.Message);
        }

        resp.EnsureSuccessStatusCode();

        var body = await resp.Content.ReadFromJsonAsync<AuthLoginResponse>(JsonOpts, ct)
                   ?? throw new InvalidOperationException("Resposta vazia do backend (login)");

        return new AuthResult(body.AccessToken, body.RefreshToken, body.TerceiroId, body.ExpiresIn);
    }

    public async Task<AuthResult> RefreshAsync(string refreshToken, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync("/api/v1/auth/refresh", new RefreshRequestDto(refreshToken), JsonOpts, ct);

        if (resp.StatusCode == HttpStatusCode.Unauthorized)
        {
            var err = await ReadApiError(resp, ct);
            throw new AuthException(err?.Code ?? "UNAUTHORIZED", err?.Message);
        }

        resp.EnsureSuccessStatusCode();

        var body = await resp.Content.ReadFromJsonAsync<AuthRefreshResponse>(JsonOpts, ct)
                   ?? throw new InvalidOperationException("Resposta vazia do backend (refresh)");

        return new AuthResult(body.AccessToken, body.RefreshToken, null, body.ExpiresIn);
    }

    public async Task<CreateTerceiroResult> CreateTerceiroAsync(CreateTerceiroDto dto, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync("/api/v1/terceiros", dto, JsonOpts, ct);

        if (resp.StatusCode is HttpStatusCode.Forbidden or HttpStatusCode.UnprocessableEntity)
        {
            var err = await ReadApiError(resp, ct);
            throw new AuthException(err?.Code ?? resp.StatusCode.ToString(), err?.Message);
        }

        resp.EnsureSuccessStatusCode();

        return await resp.Content.ReadFromJsonAsync<CreateTerceiroResult>(JsonOpts, ct)
               ?? throw new InvalidOperationException("Resposta vazia do backend (terceiro)");
    }

    public async Task<SyncOutcome> PostMarcacaoAsync(MarcacaoLocal m, string accessToken, CancellationToken ct = default)
    {
        try
        {
            using var req = new HttpRequestMessage(HttpMethod.Post, "/api/v1/marcacoes");
            req.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", accessToken);
            req.Content = JsonContent.Create(
                new PostMarcacaoDto(m.Tipo, m.HorarioRegistrado, m.HorarioEfetivo, m.Origem, m.Id),
                options: JsonOpts);

            var resp = await _http.SendAsync(req, ct);

            if (resp.StatusCode == HttpStatusCode.Created)
                return SyncOutcome.Created;

            if (resp.StatusCode == HttpStatusCode.Conflict)
            {
                var err = await ReadApiError(resp, ct);
                return err?.Code == "AJUSTE_WEB_WINS"
                    ? SyncOutcome.DiscardLocal
                    : SyncOutcome.AlreadyExists;
            }

            if (resp.StatusCode == HttpStatusCode.UnprocessableEntity)
                return SyncOutcome.Rejected;

            if ((int)resp.StatusCode >= 500)
                return SyncOutcome.TransientFailure;

            if (resp.StatusCode == HttpStatusCode.Unauthorized)
            {
                var err = await ReadApiError(resp, ct);
                throw new AuthException(err?.Code ?? "UNAUTHORIZED", err?.Message);
            }

            return SyncOutcome.TransientFailure;
        }
        catch (AuthException)
        {
            throw;
        }
        catch
        {
            return SyncOutcome.TransientFailure;
        }
    }

    public async Task<bool> IsHealthyAsync(CancellationToken ct = default)
    {
        try
        {
            var resp = await _http.GetAsync("/api/v1/health", ct);
            return resp.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    public async Task<bool> IsReadyAsync(CancellationToken ct = default)
    {
        try
        {
            var resp = await _http.GetAsync("/api/v1/ready", ct);
            return resp.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    // ── helpers ───────────────────────────────────────────────────────────────

    private static async Task<ApiError?> ReadApiError(HttpResponseMessage resp, CancellationToken ct)
    {
        try
        {
            return await resp.Content.ReadFromJsonAsync<ApiError>(JsonOpts, ct);
        }
        catch
        {
            return null;
        }
    }

    // ── private response DTOs ─────────────────────────────────────────────────

    private sealed record AuthLoginResponse(
        [property: System.Text.Json.Serialization.JsonPropertyName("access_token")] string AccessToken,
        [property: System.Text.Json.Serialization.JsonPropertyName("refresh_token")] string RefreshToken,
        [property: System.Text.Json.Serialization.JsonPropertyName("terceiro_id")] string? TerceiroId,
        [property: System.Text.Json.Serialization.JsonPropertyName("expires_in")] int ExpiresIn);

    private sealed record AuthRefreshResponse(
        [property: System.Text.Json.Serialization.JsonPropertyName("access_token")] string AccessToken,
        [property: System.Text.Json.Serialization.JsonPropertyName("refresh_token")] string RefreshToken,
        [property: System.Text.Json.Serialization.JsonPropertyName("expires_in")] int ExpiresIn);
}
