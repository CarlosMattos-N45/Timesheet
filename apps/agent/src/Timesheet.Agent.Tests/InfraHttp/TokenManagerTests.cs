using FluentAssertions;
using Moq;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;
using Timesheet.Agent.Infra.Http;
using Xunit;

namespace Timesheet.Agent.Tests.InfraHttp;

/// <summary>
/// Testes do TokenManager usando ITokenStore fake, FakeClock e repo SQLite :memory:.
/// </summary>
public sealed class TokenManagerTests : IAsyncLifetime
{
    private readonly SqliteInMemoryFixture _fixture = new();
    private ConfiguracaoLocalRepository _repo = null!;
    private Mock<IBackendClient> _client = null!;
    private FakeTokenStore _store = null!;
    private FakeClock _clock = null!;
    private TokenManager _sut = null!;

    // clock fixo: 2026-05-27T12:00:00Z
    private static readonly DateTimeOffset FixedNow =
        new DateTimeOffset(2026, 5, 27, 12, 0, 0, TimeSpan.Zero);

    public async Task InitializeAsync()
    {
        await _fixture.InitializeAsync();
        _repo = new ConfiguracaoLocalRepository(_fixture.Context);
        _client = new Mock<IBackendClient>();
        _store = new FakeTokenStore();
        _clock = new FakeClock(FixedNow);
        _sut = new TokenManager(_repo, _store, _client.Object, _clock);
    }

    public Task DisposeAsync() => _fixture.DisposeAsync();

    // ── helpers ────────────────────────────────────────────────────────────────

    private async Task SeedConfig(string access, string refresh, string expiraEm)
    {
        await _repo.UpsertAsync(new ConfiguracaoLocal
        {
            BackendBaseUrl = "http://127.0.0.1:8765",
            JwtAccessToken = _store.Protect(access),
            JwtRefreshToken = _store.Protect(refresh),
            ExpiraEm = expiraEm,
        });
    }

    // ── testes ─────────────────────────────────────────────────────────────────

    [Fact]
    public async Task SalvarTokens_persists_encrypted_and_sets_expiry()
    {
        // Primeiro, garantir que há uma config de base (BackendBaseUrl obrigatório)
        await _repo.UpsertAsync(new ConfiguracaoLocal { BackendBaseUrl = "http://127.0.0.1:8765" });

        await _sut.SalvarTokensAsync(new AuthResult("AT", "RT", "u1", 900));

        var cfg = await _repo.GetAsync();
        cfg.Should().NotBeNull();
        cfg!.JwtAccessToken.Should().NotBe("AT");          // cifrado — não texto puro
        cfg.JwtRefreshToken.Should().NotBe("RT");          // cifrado — não texto puro
        cfg.ExpiraEm.Should().Be("2026-05-27T12:15:00.0000000+00:00"); // now + 900s em ISO 8601 ("o" format)
    }

    [Fact]
    public async Task GetValidAccessToken_returns_cached_when_not_expired()
    {
        // expira em 12:15, now = 12:00 → ainda válido (margem de 30s)
        await SeedConfig(access: "AT", refresh: "RT", expiraEm: "2026-05-27T12:15:00+00:00");

        var token = await _sut.GetValidAccessTokenAsync();

        token.Should().Be("AT");
        _client.Verify(c => c.RefreshAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task GetValidAccessToken_refreshes_when_expired()
    {
        // expira em 11:00, now = 12:00 → expirado
        await SeedConfig(access: "ATold", refresh: "RT", expiraEm: "2026-05-27T11:00:00+00:00");

        _client.Setup(c => c.RefreshAsync("RT", It.IsAny<CancellationToken>()))
               .ReturnsAsync(new AuthResult("ATnew", "RTnew", null, 900));

        var token = await _sut.GetValidAccessTokenAsync();

        token.Should().Be("ATnew");

        var cfg = await _repo.GetAsync();
        cfg.Should().NotBeNull();
        // novo refresh deve estar persistido (rotação)
        _store.Unprotect(cfg!.JwtRefreshToken!).Should().Be("RTnew");
        cfg.ExpiraEm.Should().Be("2026-05-27T12:15:00.0000000+00:00");
    }

    [Fact]
    public async Task GetValidAccessToken_propagates_AuthException_when_refresh_revoked()
    {
        await SeedConfig(access: "ATold", refresh: "RT", expiraEm: "2026-05-27T11:00:00+00:00");

        _client.Setup(c => c.RefreshAsync("RT", It.IsAny<CancellationToken>()))
               .ThrowsAsync(new AuthException("UNAUTHORIZED"));

        var act = async () => await _sut.GetValidAccessTokenAsync();

        (await act.Should().ThrowAsync<AuthException>()).Which.Code.Should().Be("UNAUTHORIZED");
    }

    [Fact]
    public async Task GetValidAccessToken_throws_when_no_config()
    {
        // repo vazio — nunca logou
        var act = async () => await _sut.GetValidAccessTokenAsync();

        (await act.Should().ThrowAsync<AuthException>()).Which.Code.Should().Be("UNAUTHORIZED");
    }
}

/// <summary>
/// Implementação fake de ITokenStore para testes cross-platform:
/// Protect = "enc:" + texto; Unprotect = remove prefixo.
/// Garante que cifrado != texto puro (NotBe) e que round-trip funciona.
/// </summary>
internal sealed class FakeTokenStore : ITokenStore
{
    public string Protect(string plaintext) => "enc:" + plaintext;
    public string Unprotect(string blobBase64) => blobBase64.StartsWith("enc:")
        ? blobBase64[4..]
        : throw new InvalidOperationException("Blob não foi cifrado por FakeTokenStore");
}
