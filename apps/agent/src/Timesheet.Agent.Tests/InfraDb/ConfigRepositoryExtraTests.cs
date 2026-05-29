using FluentAssertions;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;
using Xunit;

namespace Timesheet.Agent.Tests.InfraDb;

public sealed class ConfigRepositoryExtraTests : IAsyncLifetime
{
    private readonly SqliteInMemoryFixture _fixture = new();
    private ConfiguracaoLocalRepository _configRepo = null!;

    public async Task InitializeAsync()
    {
        await _fixture.InitializeAsync();
        _configRepo = new ConfiguracaoLocalRepository(_fixture.Context);
    }

    public Task DisposeAsync() => _fixture.DisposeAsync();

    [Fact]
    public async Task GetAsync_returns_null_when_empty()
    {
        var result = await _configRepo.GetAsync();
        result.Should().BeNull();
    }

    [Fact]
    public async Task GetAsync_returns_config_after_upsert()
    {
        await _configRepo.UpsertAsync(new ConfiguracaoLocal { BackendBaseUrl = "http://127.0.0.1:8765" });
        var result = await _configRepo.GetAsync();
        result.Should().NotBeNull();
        result!.BackendBaseUrl.Should().Be("http://127.0.0.1:8765");
        result.Id.Should().Be(1);
    }
}
