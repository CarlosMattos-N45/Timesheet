using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;
using Xunit;

namespace Timesheet.Agent.Tests.InfraDb;

public sealed class ConfigRepositoryTests : IAsyncLifetime
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
    public async Task Upsert_twice_keeps_single_row()
    {
        await _configRepo.UpsertAsync(new ConfiguracaoLocal { BackendBaseUrl = "http://127.0.0.1:8765" });
        await _configRepo.UpsertAsync(new ConfiguracaoLocal { BackendBaseUrl = "http://127.0.0.1:8765" });
        (await _fixture.Context.ConfiguracaoLocal.CountAsync()).Should().Be(1);
    }
}
