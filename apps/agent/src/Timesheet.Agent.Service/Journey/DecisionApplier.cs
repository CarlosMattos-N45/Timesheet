using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;

namespace Timesheet.Agent.Service.Journey;

/// <summary>
/// Traduz uma <see cref="DecisaoJornada"/> em efeito concreto:
/// persistir <see cref="MarcacaoLocal"/> na fila e atualizar <see cref="EstadoJornadaAtual"/>.
///
/// Nota de fronteira: a atividade capturada no diálogo PROMPT_FIM_JORNADA NÃO é enviada
/// pelo Agente — o contrato POST /api/v1/marcacoes não tem campo atividade (Spec §4).
/// A Web persiste a atividade via POST /jornadas/{id}/atividade. O Agente captura a
/// atividade para UX local (v1.0), mas não a sincroniza.
/// </summary>
public sealed class DecisionApplier(
    MarcacaoLocalRepository repo,
    EstadoJornadaRepository estadoRepo,
    IClock clock)
{
    public async Task AplicarAsync(DecisaoJornada decisao)
    {
        switch (decisao)
        {
            case RegistrarAutomatico ra:
                await EnqueueAsync(ra.Tipo, ra.Horario, ra.Origem);
                await AtualizarEstadoAsync(ra.Tipo, ra.Horario);
                break;

            case RegistrarConfirmado rc:
                await EnqueueAsync(rc.Tipo, rc.Horario, rc.Origem);
                await AtualizarEstadoAsync(rc.Tipo, rc.Horario);
                break;

            case RegistrarPendente rp:
                // Origem presumida: confirmação pendente da Web
                await EnqueueAsync(rp.Tipo, rp.Horario, OrigemMarcacao.AgenteConfirmado);
                await AtualizarEstadoAsync(rp.Tipo, rp.Horario);
                break;

            case Fechar f:
                await EnqueueAsync(f.Tipo, f.Horario, OrigemMarcacao.AgenteAutomatico);
                await SetEstadoAsync(EstadoJornada.Fechada, f.Horario);
                break;

            case FecharPendente fp:
                await EnqueueAsync(fp.Tipo, fp.Horario, OrigemMarcacao.AgenteAutomatico);
                await SetEstadoAsync(EstadoJornada.Fechada, fp.Horario);
                break;

            // ExigeDialogo, Relembrar e NenhumaAcao: no-op.
            // O host trata o diálogo via IpcServer e re-chama a máquina com a resposta.
            case ExigeDialogo:
            case Relembrar:
            case NenhumaAcao:
                break;
        }
    }

    // ── helpers ──────────────────────────────────────────────────────────────

    private async Task EnqueueAsync(string tipo, DateTimeOffset horario, string origem)
    {
        var m = new MarcacaoLocal
        {
            Id = Guid.NewGuid().ToString(),           // UUID v4 = idempotency_key
            Tipo = tipo,
            HorarioRegistrado = horario.ToUniversalTime().ToString("o"),
            HorarioEfetivo = horario.ToUniversalTime().ToString("o"),
            Origem = origem,
            DataJornada = horario.LocalDateTime.Date.ToString("yyyy-MM-dd"),
            CriadoEm = clock.NowUtc.ToString("o"),
            Sincronizada = false,
        };
        await repo.EnqueueAsync(m);
    }

    private async Task AtualizarEstadoAsync(string tipo, DateTimeOffset horario)
    {
        var novoStatus = tipo switch
        {
            MarcacaoTipo.InicioJornada => EstadoJornada.EmJornada,
            MarcacaoTipo.SaidaAlmoco => EstadoJornada.EmAlmoco,
            MarcacaoTipo.RetornoAlmoco => EstadoJornada.EmJornada,
            MarcacaoTipo.FimJornada => EstadoJornada.Fechada,
            _ => EstadoJornada.EmJornada,
        };
        await SetEstadoAsync(novoStatus, horario);
    }

    private async Task SetEstadoAsync(string status, DateTimeOffset horario)
    {
        await estadoRepo.UpsertAsync(new EstadoJornadaAtual
        {
            DataJornada = horario.LocalDateTime.Date.ToString("yyyy-MM-dd"),
            Status = status,
            AtualizadoEm = clock.NowUtc.ToString("o"),
        });
    }
}
