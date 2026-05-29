using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Timesheet.Agent.Infra.Db;
using Timesheet.Agent.Infra.Http;
using Timesheet.Agent.Ipc;

namespace Timesheet.Agent.Service.Sync;

/// <summary>
/// BackgroundService: loop de 30s que drena a fila via SyncProcessor e empurra StatusPush ao tray.
/// </summary>
public sealed class SyncHostedService(
    IServiceScopeFactory scopeFactory,
    IpcServer ipcServer,
    ILogger<SyncHostedService> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(30));

        while (!ct.IsCancellationRequested)
        {
            try
            {
                await using var scope = scopeFactory.CreateAsyncScope();
                var repo = scope.ServiceProvider.GetRequiredService<MarcacaoLocalRepository>();
                var client = scope.ServiceProvider.GetRequiredService<IBackendClient>();
                var tokens = scope.ServiceProvider.GetRequiredService<ITokenManager>();
                var clock = scope.ServiceProvider.GetRequiredService<Timesheet.Agent.Domain.IClock>();

                var processor = new SyncProcessor(repo, client, tokens, clock);
                var pendentes = await processor.ProcessarFilaAsync(ct);

                var estadoRepo = scope.ServiceProvider.GetRequiredService<EstadoJornadaRepository>();
                var estado = await estadoRepo.GetAsync();
                var estadoStr = estado?.Status ?? "AGUARDANDO_INICIO";

                await ipcServer.SendAsync(new StatusPush(estadoStr, pendentes));
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Erro no ciclo de sync.");
            }

            await timer.WaitForNextTickAsync(ct).ConfigureAwait(false);
        }
    }
}
