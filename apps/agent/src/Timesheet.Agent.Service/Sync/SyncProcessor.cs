using Microsoft.Extensions.Logging;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;
using Timesheet.Agent.Infra.Http;

namespace Timesheet.Agent.Service.Sync;

/// <summary>
/// Drena a fila de MarcacoesLocais pendentes e sincroniza com o backend (RN-012).
/// </summary>
public sealed class SyncProcessor(
    MarcacaoLocalRepository repo,
    IBackendClient client,
    ITokenManager tokens,
    IClock clock,
    ILogger<SyncProcessor>? logger = null)
{
    /// <summary>
    /// Drena a fila em ordem cronológica aplicando o SyncOutcome de cada item.
    /// Retorna a contagem de pendentes restante após a operação.
    /// </summary>
    public async Task<int> ProcessarFilaAsync(CancellationToken ct)
    {
        if (!await client.IsHealthyAsync(ct))
        {
            logger?.LogDebug("Backend indisponível — sync pausado.");
            var semSyncs = await repo.GetPendentesOrdenadasAsync();
            return semSyncs.Count;
        }

        string token;
        try
        {
            token = await tokens.GetValidAccessTokenAsync(ct);
        }
        catch (AuthException ex)
        {
            logger?.LogWarning("Token inválido ({Code}) — sync pausado até novo login.", ex.Code);
            var semToken = await repo.GetPendentesOrdenadasAsync();
            return semToken.Count;
        }

        var pendentes = await repo.GetPendentesOrdenadasAsync();

        foreach (var m in pendentes)
        {
            ct.ThrowIfCancellationRequested();

            var outcome = await client.PostMarcacaoAsync(m, token, ct);

            switch (outcome)
            {
                case SyncOutcome.Created:
                case SyncOutcome.AlreadyExists:
                case SyncOutcome.DiscardLocal:
                // RN-012: AJUSTE_WEB venceu → descartar local sem reenfileirar
                case SyncOutcome.Rejected:
                    await repo.MarcarSincronizadaAsync(m.Id);
                    break;

                case SyncOutcome.TransientFailure:
                    var proxima = clock.NowUtc
                        .AddSeconds(Backoff(m.TentativasSync + 1))
                        .ToString("o");
                    await repo.RegistrarFalhaSyncAsync(m.Id, "sync transient", proxima);
                    // Circuito provavelmente aberto — não continuar martelando.
                    goto done;
            }
        }

    done:
        var restantes = await repo.GetPendentesOrdenadasAsync();
        return restantes.Count;
    }

    /// <summary>Backoff exponencial (1→2→4…s) com teto em 30s.</summary>
    private static double Backoff(int tentativa) =>
        Math.Min(Math.Pow(2, tentativa - 1), 30);
}
