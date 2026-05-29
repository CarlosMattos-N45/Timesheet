using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;
using Timesheet.Agent.Ipc;
using Timesheet.Agent.Service.Input;

namespace Timesheet.Agent.Service.Journey;

/// <summary>
/// BackgroundService: monitora login de sessão Windows, polling de inatividade (30s),
/// janela de almoço/fim e auto-encerramento. Traduz DecisaoJornada via DecisionApplier.
/// </summary>
public sealed class JourneyHostedService(
    IServiceScopeFactory scopeFactory,
    ISessionMonitor sessionMonitor,
    ILastInputProvider lastInputProvider,
    IpcServer ipcServer,
    IClock clock,
    ILogger<JourneyHostedService> logger) : BackgroundService
{
    private HorariosJornada _horarios = new(
        new TimeOnly(9, 0), new TimeOnly(12, 0), new TimeOnly(13, 0), new TimeOnly(18, 0));

    private bool _emJornada;
    private bool _aguardandoFim;

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        sessionMonitor.SessionLogon += OnSessionLogon;
        sessionMonitor.Start();

        var tracker = new InactivityTracker(limiarInatividadeSeg: 30);
        tracker.OnRetornoDeInatividade += retorno => OnRetornoInatividade(retorno, ct);

        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(30));

        while (!ct.IsCancellationRequested)
        {
            try
            {
                var idleMs = lastInputProvider.GetIdleMilliseconds();
                var agora = clock.NowLocal;
                tracker.Observe(idleMs, agora);

                if (_emJornada)
                {
                    await VerificarFimJornada(ct);
                    await VerificarAutoEncerramento(tracker, agora, ct);
                }
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Erro no polling de jornada.");
            }

            await timer.WaitForNextTickAsync(ct).ConfigureAwait(false);
        }

        sessionMonitor.SessionLogon -= OnSessionLogon;
        sessionMonitor.Stop();
    }

    private void OnSessionLogon()
    {
        // Dispara avaliação de login em background
        _ = Task.Run(async () =>
        {
            try
            {
                await AvaliarLoginAsync();
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Erro ao avaliar login.");
            }
        });
    }

    private async Task AvaliarLoginAsync()
    {
        var t = clock.NowLocal;
        var ehFds = t.DayOfWeek is DayOfWeek.Saturday or DayOfWeek.Sunday;
        var decisao = JourneyStateMachine.AvaliarLogin(t, _horarios, ehFds, trabalhaFds: false);
        await AplicarComDialogo(decisao, default);
    }

    private void OnRetornoInatividade(RetornoDeInatividade retorno, CancellationToken ct)
    {
        _ = Task.Run(async () =>
        {
            try
            {
                var duracao = (int)(retorno.FimInatividade - retorno.InicioInatividade).TotalMinutes;
                var decisao = JourneyStateMachine.AvaliarInatividade(
                    retorno.InicioInatividade, duracao, _horarios);

                if (decisao is not NenhumaAcao)
                {
                    await AplicarComDialogo(decisao, ct);

                    // Após saída para almoço, avaliar retorno
                    var retornoDecisao = JourneyStateMachine.AvaliarRetorno(retorno.FimInatividade, _horarios);
                    await AplicarComDialogo(retornoDecisao, ct);
                }
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Erro ao processar retorno de inatividade.");
            }
        }, ct);
    }

    private async Task VerificarFimJornada(CancellationToken ct)
    {
        if (_aguardandoFim) return;

        var decisao = JourneyStateMachine.AvaliarFim(clock.NowLocal, _horarios);
        if (decisao is ExigeDialogo)
        {
            _aguardandoFim = true;
            await AplicarComDialogo(decisao, ct);
        }
    }

    private async Task VerificarAutoEncerramento(InactivityTracker tracker, DateTimeOffset agora, CancellationToken ct)
    {
        if (tracker.InicioInatividade is null) return;

        var decisao = JourneyStateMachine.AvaliarAutoEncerramento(
            tracker.InicioInatividade.Value, agora, _horarios);

        if (decisao is FecharPendente)
            await AplicarComDialogo(decisao, ct);
    }

    private async Task AplicarComDialogo(DecisaoJornada decisao, CancellationToken ct)
    {
        await using var scope = scopeFactory.CreateAsyncScope();
        var repo = scope.ServiceProvider.GetRequiredService<MarcacaoLocalRepository>();
        var estadoRepo = scope.ServiceProvider.GetRequiredService<EstadoJornadaRepository>();
        var cl = scope.ServiceProvider.GetRequiredService<IClock>();
        var applier = new DecisionApplier(repo, estadoRepo, cl);

        if (decisao is ExigeDialogo diag)
        {
            var req = new DialogRequest(Guid.NewGuid().ToString(), diag.Kind,
                new Dictionary<string, string>
                {
                    ["horario"] = diag.HorarioProposto.ToString("o"),
                });

            DialogResponse resp;
            try
            {
                resp = await ipcServer.SendDialogRequestAsync(req, TimeSpan.FromSeconds(60));
            }
            catch
            {
                resp = new DialogResponse(req.Id, "TIMEOUT");
            }

            DecisaoJornada resolvida = diag.Kind switch
            {
                "CONFIRM_INICIO_ANTECIPADO" =>
                    JourneyStateMachine.ResolverInicioAntecipado(
                        resp.Answer, diag.HorarioProposto, diag.Fallback ?? diag.HorarioProposto),
                "CONFIRM_RETORNO_FORA_JANELA" =>
                    JourneyStateMachine.ResolverRetornoForaJanela(resp.Answer, diag.HorarioProposto),
                "PROMPT_FIM_JORNADA" =>
                    JourneyStateMachine.ResolverFim(
                        resp.Answer,
                        resp.Payload?.GetValueOrDefault("atividade"),
                        diag.HorarioProposto),
                _ => new NenhumaAcao(),
            };

            await applier.AplicarAsync(resolvida);

            if (resolvida is RegistrarAutomatico ra && ra.AtrasoMinutos is > 0)
            {
                var saudacao = GetSaudacao(cl.NowLocal.Hour);
                await ipcServer.SendAsync(new ToastMessage(
                    "Timesheet",
                    $"{saudacao}. Início registrado às {ra.Horario.LocalDateTime:HH:mm} (atraso {ra.AtrasoMinutos} min).",
                    10));
            }
        }
        else
        {
            await applier.AplicarAsync(decisao);

            if (decisao is RegistrarAutomatico ra2 && decisao is not NenhumaAcao)
            {
                _emJornada = ra2.Tipo == MarcacaoTipo.InicioJornada || ra2.Tipo == MarcacaoTipo.RetornoAlmoco;
            }
        }

        UpdateEmJornada(decisao);
    }

    private void UpdateEmJornada(DecisaoJornada d)
    {
        switch (d)
        {
            case RegistrarAutomatico ra:
                _emJornada = ra.Tipo is MarcacaoTipo.InicioJornada or MarcacaoTipo.RetornoAlmoco;
                if (ra.Tipo == MarcacaoTipo.FimJornada) _aguardandoFim = false;
                break;
            case RegistrarConfirmado rc:
                _emJornada = rc.Tipo is MarcacaoTipo.InicioJornada or MarcacaoTipo.RetornoAlmoco;
                if (rc.Tipo == MarcacaoTipo.FimJornada) _aguardandoFim = false;
                break;
            case Fechar:
            case FecharPendente:
                _emJornada = false;
                _aguardandoFim = false;
                break;
        }
    }

    private static string GetSaudacao(int hora) => hora switch
    {
        < 12 => "Bom dia",
        < 18 => "Boa tarde",
        _ => "Boa noite",
    };
}
