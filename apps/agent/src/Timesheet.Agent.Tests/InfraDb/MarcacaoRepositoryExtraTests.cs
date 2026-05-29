using FluentAssertions;
using Timesheet.Agent.Infra.Db;
using Xunit;

namespace Timesheet.Agent.Tests.InfraDb;

public sealed class MarcacaoRepositoryExtraTests : IAsyncLifetime
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
    public async Task RegistrarFalhaSyncAsync_increments_tentativas_and_sets_erro()
    {
        await _repo.EnqueueAsync(TestData.Marcacao("err1", "2026-05-27T12:00:00Z"));
        await _repo.RegistrarFalhaSyncAsync("err1", "timeout", "2026-05-27T13:00:00Z");

        var m = await _repo.GetByIdAsync("err1");
        m.Should().NotBeNull();
        m!.TentativasSync.Should().Be(1);
        m.UltimoErroSync.Should().Be("timeout");
        m.ProximaTentativaEm.Should().Be("2026-05-27T13:00:00Z");
    }

    [Fact]
    public async Task GetByIdAsync_returns_null_when_not_found()
    {
        var result = await _repo.GetByIdAsync("nonexistent");
        result.Should().BeNull();
    }
}
