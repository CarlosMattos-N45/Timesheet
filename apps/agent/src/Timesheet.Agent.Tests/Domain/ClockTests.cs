using FluentAssertions;
using Timesheet.Agent.Domain;
using Xunit;

namespace Timesheet.Agent.Tests.Domain;

public class ClockTests
{
    [Fact]
    public void FakeClock_returns_fixed_instant()
    {
        var clock = new FakeClock(DateTimeOffset.Parse("2026-05-27T12:00:00Z"));
        clock.NowUtc.Should().Be(DateTimeOffset.Parse("2026-05-27T12:00:00+00:00"));
    }

    [Fact]
    public void SystemClock_NowLocal_uses_sao_paulo_offset()
    {
        var clock = new SystemClock();
        clock.NowLocal.Offset.Should().Be(TimeSpan.FromHours(-3));
    }

    [Fact]
    public void Constants_match_backend_contract()
    {
        MarcacaoTipo.InicioJornada.Should().Be("INICIO_JORNADA");
        MarcacaoTipo.SaidaAlmoco.Should().Be("SAIDA_ALMOCO");
        MarcacaoTipo.RetornoAlmoco.Should().Be("RETORNO_ALMOCO");
        MarcacaoTipo.FimJornada.Should().Be("FIM_JORNADA");
        OrigemMarcacao.AgenteAutomatico.Should().Be("AGENTE_AUTOMATICO");
        OrigemMarcacao.AgenteConfirmado.Should().Be("AGENTE_CONFIRMADO");
    }
}
