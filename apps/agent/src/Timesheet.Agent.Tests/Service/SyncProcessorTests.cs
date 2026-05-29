using FluentAssertions;
using Moq;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Http;
using Timesheet.Agent.Tests;
using Xunit;

// ITokenManager is declared in Timesheet.Agent.Infra.Http

namespace Timesheet.Agent.Tests.Service;

public class SyncProcessorTests : IAsyncLifetime
{
    private readonly SqliteInMemoryFixture _fx = new();
    private readonly Mock<IBackendClient> _client = new();
    private readonly Mock<ITokenManager> _tokens = new();
    private Timesheet.Agent.Service.Sync.SyncProcessor _sut = null!;

    public async Task InitializeAsync()
    {
        await _fx.InitializeAsync();
        var repo = new Timesheet.Agent.Infra.Db.MarcacaoLocalRepository(_fx.Context);
        var clock = new FakeClock(new DateTimeOffset(2026, 5, 27, 12, 0, 0, TimeSpan.Zero));
        _sut = new Timesheet.Agent.Service.Sync.SyncProcessor(repo, _client.Object, _tokens.Object, clock);

        // default: token available
        _tokens.Setup(t => t.GetValidAccessTokenAsync(It.IsAny<CancellationToken>()))
               .ReturnsAsync("token-abc");
    }

    public Task DisposeAsync() => _fx.DisposeAsync();

    private static Timesheet.Agent.Domain.MarcacaoLocal Mk(string id, string criadoEm) =>
        TestData.Marcacao(id, criadoEm);

    [Fact]
    public async Task Drains_pending_in_chronological_order_and_marks_synced()
    {
        var repo = new Timesheet.Agent.Infra.Db.MarcacaoLocalRepository(_fx.Context);
        await repo.EnqueueAsync(Mk("b", "2026-05-27T13:00:00Z"));
        await repo.EnqueueAsync(Mk("a", "2026-05-27T12:00:00Z"));

        _client.Setup(c => c.IsHealthyAsync(It.IsAny<CancellationToken>())).ReturnsAsync(true);
        var seq = new List<string>();
        _client.Setup(c => c.PostMarcacaoAsync(
                It.IsAny<MarcacaoLocal>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .Callback<MarcacaoLocal, string, CancellationToken>((m, _, __) => seq.Add(m.Id))
            .ReturnsAsync(SyncOutcome.Created);

        await _sut.ProcessarFilaAsync(CancellationToken.None);

        seq.Should().Equal("a", "b");
        (await repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
    }

    [Fact]
    public async Task TransientFailure_keeps_pending_and_increments_attempts()
    {
        var repo = new Timesheet.Agent.Infra.Db.MarcacaoLocalRepository(_fx.Context);
        await repo.EnqueueAsync(Mk("x", "2026-05-27T12:00:00Z"));

        _client.Setup(c => c.IsHealthyAsync(It.IsAny<CancellationToken>())).ReturnsAsync(true);
        _client.Setup(c => c.PostMarcacaoAsync(
                It.IsAny<MarcacaoLocal>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(SyncOutcome.TransientFailure);

        await _sut.ProcessarFilaAsync(CancellationToken.None);

        var pend = await repo.GetPendentesOrdenadasAsync();
        pend.Should().ContainSingle();
        pend[0].TentativasSync.Should().Be(1);
        pend[0].ProximaTentativaEm.Should().NotBeNull();
    }

    [Fact]
    public async Task DiscardLocal_and_AlreadyExists_both_mark_synced()
    {
        var repo = new Timesheet.Agent.Infra.Db.MarcacaoLocalRepository(_fx.Context);
        await repo.EnqueueAsync(Mk("d", "2026-05-27T12:00:00Z"));
        await repo.EnqueueAsync(Mk("e", "2026-05-27T12:30:00Z"));

        _client.Setup(c => c.IsHealthyAsync(It.IsAny<CancellationToken>())).ReturnsAsync(true);
        _client.SetupSequence(c => c.PostMarcacaoAsync(
                It.IsAny<MarcacaoLocal>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(SyncOutcome.DiscardLocal)
            .ReturnsAsync(SyncOutcome.AlreadyExists);

        await _sut.ProcessarFilaAsync(CancellationToken.None);

        (await repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
    }

    [Fact]
    public async Task Does_not_post_when_backend_down()
    {
        var repo = new Timesheet.Agent.Infra.Db.MarcacaoLocalRepository(_fx.Context);
        await repo.EnqueueAsync(Mk("z", "2026-05-27T12:00:00Z"));

        _client.Setup(c => c.IsHealthyAsync(It.IsAny<CancellationToken>())).ReturnsAsync(false);

        await _sut.ProcessarFilaAsync(CancellationToken.None);

        _client.Verify(c => c.PostMarcacaoAsync(
            It.IsAny<MarcacaoLocal>(), It.IsAny<string>(), It.IsAny<CancellationToken>()),
            Times.Never);
        (await repo.GetPendentesOrdenadasAsync()).Should().ContainSingle();
    }
}
