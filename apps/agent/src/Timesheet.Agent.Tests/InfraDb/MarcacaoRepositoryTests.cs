using FluentAssertions;
using Timesheet.Agent.Infra.Db;
using Xunit;

namespace Timesheet.Agent.Tests.InfraDb;

public sealed class MarcacaoRepositoryTests : IAsyncLifetime
{
    private readonly SqliteInMemoryFixture _fixture = new();
    private MarcacaoLocalRepository _repo = null!;

    public async Task InitializeAsync()
    {
        await _fixture.InitializeAsync();
        _repo = new MarcacaoLocalRepository(_fixture.Context);
    }

    public Task DisposeAsync() => _fixture.DisposeAsync();

    [Fact]
    public async Task GetPendentes_returns_only_unsynced_ordered_by_criadoEm()
    {
        await _repo.EnqueueAsync(TestData.Marcacao("b", criadoEm: "2026-05-27T13:00:00Z"));
        await _repo.EnqueueAsync(TestData.Marcacao("a", criadoEm: "2026-05-27T12:00:00Z"));
        var pend = await _repo.GetPendentesOrdenadasAsync();
        pend.Select(m => m.Id).Should().Equal("a", "b");
    }

    [Fact]
    public async Task MarcarSincronizada_removes_from_pendentes()
    {
        await _repo.EnqueueAsync(TestData.Marcacao("x", criadoEm: "2026-05-27T12:00:00Z"));
        await _repo.MarcarSincronizadaAsync("x");
        (await _repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
    }
}
