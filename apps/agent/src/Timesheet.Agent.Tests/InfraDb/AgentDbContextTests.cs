using FluentAssertions;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;
using Xunit;

namespace Timesheet.Agent.Tests.InfraDb;

public sealed class AgentDbContextTests : IAsyncLifetime
{
    private SqliteConnection _conn = null!;
    private AgentDbContext _ctx = null!;

    public async Task InitializeAsync()
    {
        // SQLite shared in-memory por conexao — vive enquanto a conexao estiver aberta.
        _conn = new SqliteConnection("DataSource=:memory:");
        await _conn.OpenAsync();
        var options = new DbContextOptionsBuilder<AgentDbContext>()
            .UseSqlite(_conn)
            .Options;
        _ctx = new AgentDbContext(options);
        await _ctx.Database.MigrateAsync();
    }

    public async Task DisposeAsync()
    {
        await _ctx.DisposeAsync();
        await _conn.DisposeAsync();
    }

    [Fact]
    public async Task Migration_creates_all_three_tables()
    {
        var tables = await _ctx.Database
            .SqlQueryRaw<string>("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            .ToListAsync();
        tables.Should().Contain("MarcacaoLocal");
        tables.Should().Contain("EstadoJornadaAtual");
        tables.Should().Contain("ConfiguracaoLocal");
        tables.Should().Contain("__EFMigrationsHistory");
    }

    [Fact]
    public async Task MarcacaoLocal_roundtrip()
    {
        var id = Guid.NewGuid().ToString();
        _ctx.MarcacoesLocais.Add(new MarcacaoLocal
        {
            Id = id,
            Tipo = "INICIO_JORNADA",
            HorarioRegistrado = "2026-05-27T12:00:00Z",
            Origem = "AGENTE_AUTOMATICO",
            DataJornada = "2026-05-27",
            CriadoEm = "2026-05-27T12:00:00Z",
        });
        await _ctx.SaveChangesAsync();

        var fetched = await _ctx.MarcacoesLocais.SingleAsync(m => m.Id == id);
        fetched.Tipo.Should().Be("INICIO_JORNADA");
        fetched.Sincronizada.Should().BeFalse();
        fetched.TentativasSync.Should().Be(0);
    }

    [Fact]
    public async Task MarcacaoLocal_duplicate_id_rejected()
    {
        var id = Guid.NewGuid().ToString();
        _ctx.MarcacoesLocais.Add(new MarcacaoLocal
        {
            Id = id,
            Tipo = "INICIO_JORNADA",
            HorarioRegistrado = "2026-05-27T12:00:00Z",
            Origem = "AGENTE_AUTOMATICO",
            DataJornada = "2026-05-27",
            CriadoEm = "2026-05-27T12:00:00Z",
        });
        await _ctx.SaveChangesAsync();

        // Usar segundo contexto (mesma conexao) para bypassar o ChangeTracker
        // e forcar violacao de PK no banco.
        var options2 = new DbContextOptionsBuilder<AgentDbContext>()
            .UseSqlite(_conn)
            .Options;
        await using var ctx2 = new AgentDbContext(options2);
        ctx2.MarcacoesLocais.Add(new MarcacaoLocal
        {
            Id = id,
            Tipo = "FIM_JORNADA",
            HorarioRegistrado = "2026-05-27T18:00:00Z",
            Origem = "AGENTE_AUTOMATICO",
            DataJornada = "2026-05-27",
            CriadoEm = "2026-05-27T18:00:00Z",
        });

        Func<Task> act = async () => await ctx2.SaveChangesAsync();
        await act.Should().ThrowAsync<DbUpdateException>();
    }

    [Fact]
    public async Task EstadoJornadaAtual_singleton_rejects_id_other_than_1()
    {
        _ctx.EstadoJornadaAtual.Add(new EstadoJornadaAtual
        {
            Id = 2,
            DataJornada = "2026-05-27",
            Status = "EM_JORNADA",
            AtualizadoEm = "2026-05-27T12:00:00Z",
        });
        Func<Task> act = async () => await _ctx.SaveChangesAsync();
        await act.Should().ThrowAsync<DbUpdateException>();
    }

    [Fact]
    public async Task ConfiguracaoLocal_singleton_rejects_id_other_than_1()
    {
        _ctx.ConfiguracaoLocal.Add(new ConfiguracaoLocal
        {
            Id = 5,
            BackendBaseUrl = "http://127.0.0.1:8765",
        });
        Func<Task> act = async () => await _ctx.SaveChangesAsync();
        await act.Should().ThrowAsync<DbUpdateException>();
    }

    [Fact]
    public async Task Pending_queue_ordered_by_criado_em()
    {
        _ctx.MarcacoesLocais.AddRange(
            new MarcacaoLocal { Id = "b", Tipo = "INICIO_JORNADA", HorarioRegistrado = "x", Origem = "AGENTE_AUTOMATICO", DataJornada = "2026-05-27", CriadoEm = "2026-05-27T13:00:00Z" },
            new MarcacaoLocal { Id = "a", Tipo = "SAIDA_ALMOCO", HorarioRegistrado = "x", Origem = "AGENTE_AUTOMATICO", DataJornada = "2026-05-27", CriadoEm = "2026-05-27T12:00:00Z" }
        );
        await _ctx.SaveChangesAsync();

        var pending = await _ctx.MarcacoesLocais
            .Where(m => !m.Sincronizada)
            .OrderBy(m => m.CriadoEm)
            .Select(m => m.Id)
            .ToListAsync();

        pending.Should().Equal("a", "b");
    }

    [Fact]
    public async Task Index_on_sincronizada_and_proxima_tentativa_exists()
    {
        var indexes = await _ctx.Database
            .SqlQueryRaw<string>("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='MarcacaoLocal'")
            .ToListAsync();
        indexes.Should().Contain(name => name.Contains("Sincronizada"));
    }

    [Fact]
    public void AgentDbContextFactory_creates_context_with_env_path()
    {
        // Verifica que a design-time factory instancia o contexto sem erros.
        var originalPath = Environment.GetEnvironmentVariable("AGENT_DB_PATH");
        try
        {
            Environment.SetEnvironmentVariable("AGENT_DB_PATH", ":memory:");
            var factory = new AgentDbContextFactory();
            using var ctx = factory.CreateDbContext([]);
            ctx.Should().NotBeNull();
        }
        finally
        {
            Environment.SetEnvironmentVariable("AGENT_DB_PATH", originalPath);
        }
    }
}
