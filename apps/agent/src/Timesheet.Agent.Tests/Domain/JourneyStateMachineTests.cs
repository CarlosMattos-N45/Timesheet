using FluentAssertions;
using Timesheet.Agent.Domain;
using Xunit;

namespace Timesheet.Agent.Tests.Domain;

public class JourneyStateMachineTests
{
    private static HorariosJornada Horarios() => new(
        Inicio: new TimeOnly(9, 0), SaidaAlmoco: new TimeOnly(12, 0),
        RetornoAlmoco: new TimeOnly(13, 0), Fim: new TimeOnly(18, 0));

    private static DateTimeOffset At(int h, int m) =>
        new(2026, 5, 27, h, m, 0, TimeSpan.FromHours(-3)); // quarta-feira, BRT

    [Fact]
    public void Login_dentro_da_janela_registra_automatico_sem_dialogo()
    {
        var d = JourneyStateMachine.AvaliarLogin(At(9, 2), Horarios(), ehFimDeSemana: false, trabalhaFds: false);
        d.Should().BeOfType<RegistrarAutomatico>();
        var r = (RegistrarAutomatico)d;
        r.Tipo.Should().Be(MarcacaoTipo.InicioJornada);
        r.Horario.Should().Be(At(9, 2));
        r.Origem.Should().Be(OrigemMarcacao.AgenteAutomatico);
    }

    [Fact]
    public void Login_em_atraso_registra_e_emite_toast_de_atraso()
    {
        var d = JourneyStateMachine.AvaliarLogin(At(9, 45), Horarios(), false, false);
        var r = d.Should().BeOfType<RegistrarAutomatico>().Subject;
        r.Horario.Should().Be(At(9, 45));
        r.AtrasoMinutos.Should().Be(45);
    }

    [Fact]
    public void Login_antecipado_exige_dialogo_com_fallback_h_ini()
    {
        var d = JourneyStateMachine.AvaliarLogin(At(6, 45), Horarios(), false, false);
        var dlg = d.Should().BeOfType<ExigeDialogo>().Subject;
        dlg.Kind.Should().Be("CONFIRM_INICIO_ANTECIPADO");
        dlg.HorarioProposto.Should().Be(At(6, 45));
        dlg.Fallback.Should().Be(At(9, 0));
    }

    [Fact]
    public void ResolverInicioAntecipado_timeout_usa_h_ini()
    {
        var r = JourneyStateMachine.ResolverInicioAntecipado("TIMEOUT", At(6, 45), At(9, 0));
        r.Horario.Should().Be(At(9, 0));
        r.Origem.Should().Be(OrigemMarcacao.AgenteConfirmado);
    }

    [Fact]
    public void Login_em_fim_de_semana_sem_trabalho_nao_registra()
    {
        JourneyStateMachine.AvaliarLogin(At(10, 0), Horarios(), ehFimDeSemana: true, trabalhaFds: false)
            .Should().BeOfType<NenhumaAcao>();
    }

    [Fact]
    public void Inatividade_na_janela_de_almoco_registra_saida()
    {
        var d = JourneyStateMachine.AvaliarInatividade(inicioInatividade: At(12, 5), duracaoMin: 13, Horarios());
        var r = d.Should().BeOfType<RegistrarAutomatico>().Subject;
        r.Tipo.Should().Be(MarcacaoTipo.SaidaAlmoco);
        r.Horario.Should().Be(At(12, 5));
    }

    [Fact]
    public void Inatividade_fora_da_janela_nao_registra()
    {
        JourneyStateMachine.AvaliarInatividade(At(15, 0), 13, Horarios()).Should().BeOfType<NenhumaAcao>();
    }

    [Fact]
    public void Inatividade_menor_que_10min_nao_registra()
    {
        JourneyStateMachine.AvaliarInatividade(At(12, 5), 8, Horarios()).Should().BeOfType<NenhumaAcao>();
    }

    [Fact]
    public void Retorno_dentro_da_janela_registra_automatico()
    {
        JourneyStateMachine.AvaliarRetorno(At(13, 10), Horarios())
            .Should().BeOfType<RegistrarAutomatico>()
            .Which.Horario.Should().Be(At(13, 10));
    }

    [Fact]
    public void Retorno_fora_da_janela_exige_dialogo()
    {
        JourneyStateMachine.AvaliarRetorno(At(14, 30), Horarios())
            .Should().BeOfType<ExigeDialogo>()
            .Which.Kind.Should().Be("CONFIRM_RETORNO_FORA_JANELA");
    }

    [Fact]
    public void Retorno_negado_gera_marcacao_pendente()
    {
        JourneyStateMachine.ResolverRetornoForaJanela("NAO", At(14, 30))
            .Should().BeOfType<RegistrarPendente>()
            .Which.Tipo.Should().Be(MarcacaoTipo.RetornoAlmoco);
    }

    [Fact]
    public void Fim_com_sim_e_atividade_fecha_jornada()
    {
        var r = JourneyStateMachine.ResolverFim("SIM", "Desenvolvi a feature X", At(18, 5))
            .Should().BeOfType<Fechar>().Subject;
        r.Horario.Should().Be(At(18, 5));
        r.Atividade.Should().Be("Desenvolvi a feature X");
    }

    [Fact]
    public void Fim_timeout_reagenda_em_30min()
    {
        JourneyStateMachine.ResolverFim("TIMEOUT", null, At(18, 0))
            .Should().BeOfType<Relembrar>()
            .Which.Em.Should().Be(At(18, 30));
    }

    [Fact]
    public void AutoEncerramento_apos_60min_inatividade_fecha_pendente()
    {
        var r = JourneyStateMachine.AvaliarAutoEncerramento(ultimoInput: At(18, 2), agora: At(19, 5), Horarios())
            .Should().BeOfType<FecharPendente>().Subject;
        r.Horario.Should().Be(At(18, 2));
    }

    [Fact]
    public void AutoEncerramento_antes_de_60min_nao_age()
    {
        JourneyStateMachine.AvaliarAutoEncerramento(At(18, 2), At(18, 40), Horarios())
            .Should().BeOfType<NenhumaAcao>();
    }

    [Fact]
    public void AvaliarFim_T_igual_h_fim_exige_dialogo()
    {
        // T == h_fim → deve exigir diálogo PROMPT_FIM_JORNADA com horarioProposto == h_fim
        var d = JourneyStateMachine.AvaliarFim(At(18, 0), Horarios());
        var dlg = d.Should().BeOfType<ExigeDialogo>().Subject;
        dlg.Kind.Should().Be("PROMPT_FIM_JORNADA");
        dlg.HorarioProposto.Should().Be(At(18, 0));
    }

    [Fact]
    public void AvaliarFim_T_menor_h_fim_retorna_nenhuma_acao()
    {
        // T < h_fim → deve retornar NenhumaAcao
        JourneyStateMachine.AvaliarFim(At(17, 59), Horarios())
            .Should().BeOfType<NenhumaAcao>();
    }

    [Fact]
    public void Retorno_sim_registra_confirmado()
    {
        // SIM → RegistrarConfirmado com tipo RetornoAlmoco e origem AgenteConfirmado
        var r = JourneyStateMachine.ResolverRetornoForaJanela("SIM", At(14, 30))
            .Should().BeOfType<RegistrarConfirmado>().Subject;
        r.Tipo.Should().Be(MarcacaoTipo.RetornoAlmoco);
        r.Origem.Should().Be(OrigemMarcacao.AgenteConfirmado);
        r.Horario.Should().Be(At(14, 30));
    }

    [Fact]
    public void ResolverFim_atividade_curta_lanca_exception()
    {
        // SIM com atividade < 10 chars → ArgumentException
        var act = () => JourneyStateMachine.ResolverFim("SIM", "curta", At(18, 5));
        act.Should().Throw<ArgumentException>()
            .WithParameterName("atividade");
    }
}
