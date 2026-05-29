using FluentAssertions;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;
using Xunit;

namespace Timesheet.Agent.Tests.InfraDb;

public sealed class EstadoJornadaRepositoryTests : IAsyncLifetime
{
    private readonly SqliteInMemoryFixture _fixture = new();
    private EstadoJornadaRepository _repo = null!;

    public async Task InitializeAsync()
    {
        await _fixture.InitializeAsync();
        _repo = new EstadoJornadaRepository(_fixture.Context);
    }

    public Task DisposeAsync() => _fixture.DisposeAsync();

    [Fact]
    public async Task GetAsync_returns_null_when_empty()
    {
        var result = await _repo.GetAsync();
        result.Should().BeNull();
    }

    [Fact]
    public async Task UpsertAsync_creates_and_updates_singleton()
    {
        var estado = new EstadoJornadaAtual
        {
            DataJornada = "2026-05-27",
            Status = "EM_JORNADA",
            AtualizadoEm = "2026-05-27T12:00:00Z",
        };
        await _repo.UpsertAsync(estado);

        var fetched = await _repo.GetAsync();
        fetched.Should().NotBeNull();
        fetched!.Status.Should().Be("EM_JORNADA");
        fetched.Id.Should().Be(1);

        // Update
        estado = new EstadoJornadaAtual
        {
            DataJornada = "2026-05-27",
            Status = "FECHADA",
            AtualizadoEm = "2026-05-27T18:00:00Z",
        };
        await _repo.UpsertAsync(estado);

        fetched = await _repo.GetAsync();
        fetched!.Status.Should().Be("FECHADA");
    }
}
