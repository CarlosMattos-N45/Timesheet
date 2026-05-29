using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Timesheet.Agent.Infra.Db;
using Xunit;

namespace Timesheet.Agent.Tests;

/// <summary>
/// Shared SQLite in-memory setup for tests that need an AgentDbContext.
/// Opens a persistent connection so the in-memory database lives for the test lifetime.
/// </summary>
public sealed class SqliteInMemoryFixture : IAsyncLifetime
{
    public SqliteConnection Connection { get; private set; } = null!;
    public AgentDbContext Context { get; private set; } = null!;

    public async Task InitializeAsync()
    {
        Connection = new SqliteConnection("DataSource=:memory:");
        await Connection.OpenAsync();
        var options = new DbContextOptionsBuilder<AgentDbContext>()
            .UseSqlite(Connection)
            .Options;
        Context = new AgentDbContext(options);
        await Context.Database.MigrateAsync();
    }

    public async Task DisposeAsync()
    {
        await Context.DisposeAsync();
        await Connection.DisposeAsync();
    }
}
