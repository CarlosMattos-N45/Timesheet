using FluentAssertions;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Tests;
using Xunit;

namespace Timesheet.Agent.Tests.Service;

public class DecisionApplierTests : IAsyncLifetime
{
    private readonly SqliteInMemoryFixture _fx = new();
    private Timesheet.Agent.Service.Journey.DecisionApplier _applier = null!;
    private Timesheet.Agent.Infra.Db.MarcacaoLocalRepository _repo = null!;
    private Timesheet.Agent.Infra.Db.EstadoJornadaRepository _estadoRepo = null!;

    public async Task InitializeAsync()
    {
        await _fx.InitializeAsync();
        _repo = new Timesheet.Agent.Infra.Db.MarcacaoLocalRepository(_fx.Context);
        _estadoRepo = new Timesheet.Agent.Infra.Db.EstadoJornadaRepository(_fx.Context);
        var clock = new FakeClock(new DateTimeOffset(2026, 5, 27, 12, 0, 0, TimeSpan.Zero));
        _applier = new Timesheet.Agent.Service.Journey.DecisionApplier(_repo, _estadoRepo, clock);
    }

    public Task DisposeAsync() => _fx.DisposeAsync();

    private static DateTimeOffset At(int h, int m) =>
        new(2026, 5, 27, h, m, 0, TimeSpan.FromHours(-3));

    [Fact]
    public async Task RegistrarAutomatico_inicio_enqueues_and_sets_state_em_jornada()
    {
        await _applier.AplicarAsync(new RegistrarAutomatico(
            MarcacaoTipo.InicioJornada, At(9, 2), OrigemMarcacao.AgenteAutomatico));

        var pend = await _repo.GetPendentesOrdenadasAsync();
        pend.Should().ContainSingle();
        pend[0].Tipo.Should().Be("INICIO_JORNADA");
        pend[0].Origem.Should().Be("AGENTE_AUTOMATICO");
        Guid.TryParse(pend[0].Id, out _).Should().BeTrue();    // UUID v4 = idempotency_key
        (await _estadoRepo.GetAsync())!.Status.Should().Be("EM_JORNADA");
    }

    [Fact]
    public async Task ExigeDialogo_does_not_enqueue()
    {
        await _applier.AplicarAsync(new ExigeDialogo("PROMPT_FIM_JORNADA", At(18, 0)));

        (await _repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
    }

    [Fact]
    public async Task Fechar_sets_state_fechada_and_enqueues_fim()
    {
        await _applier.AplicarAsync(new Fechar(MarcacaoTipo.FimJornada, At(18, 5), "Atividade do dia ok"));

        (await _estadoRepo.GetAsync())!.Status.Should().Be("FECHADA");
        (await _repo.GetPendentesOrdenadasAsync()).Should().ContainSingle()
            .Which.Tipo.Should().Be("FIM_JORNADA");
    }

    [Fact]
    public async Task RegistrarConfirmado_enqueues_and_sets_state()
    {
        await _applier.AplicarAsync(new RegistrarConfirmado(
            MarcacaoTipo.InicioJornada, At(8, 30), OrigemMarcacao.AgenteConfirmado));

        var pend = await _repo.GetPendentesOrdenadasAsync();
        pend.Should().ContainSingle();
        pend[0].Tipo.Should().Be("INICIO_JORNADA");
        pend[0].Origem.Should().Be("AGENTE_CONFIRMADO");
        (await _estadoRepo.GetAsync())!.Status.Should().Be("EM_JORNADA");
    }

    [Fact]
    public async Task RegistrarPendente_retorno_almoco_enqueues()
    {
        await _applier.AplicarAsync(new RegistrarPendente(MarcacaoTipo.RetornoAlmoco, At(14, 30)));

        var pend = await _repo.GetPendentesOrdenadasAsync();
        pend.Should().ContainSingle();
        pend[0].Tipo.Should().Be("RETORNO_ALMOCO");
        (await _estadoRepo.GetAsync())!.Status.Should().Be("EM_JORNADA");
    }

    [Fact]
    public async Task Relembrar_does_not_enqueue()
    {
        await _applier.AplicarAsync(new Relembrar(At(18, 30)));

        (await _repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
    }

    [Fact]
    public async Task NenhumaAcao_does_not_enqueue()
    {
        await _applier.AplicarAsync(new NenhumaAcao());

        (await _repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
    }
}
