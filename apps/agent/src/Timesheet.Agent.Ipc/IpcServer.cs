using System;
using System.Threading;
using System.Threading.Tasks;

namespace Timesheet.Agent.Ipc;

/// <summary>
/// Lado Service do canal IPC. Envia mensagens ao WPF e aguarda respostas correlacionadas.
/// O loop de leitura é iniciado automaticamente no construtor.
/// </summary>
public sealed class IpcServer
{
    private readonly IDuplexChannel _channel;
    private readonly DialogCorrelator _correlator;
    private readonly CancellationTokenSource _readLoopCts = new();

    public IpcServer(IDuplexChannel channel, DialogCorrelator correlator)
    {
        _channel = channel;
        _correlator = correlator;
        _ = StartReadLoopAsync(_readLoopCts.Token);
    }

    /// <summary>Envia uma mensagem fire-and-forget (ToastMessage ou StatusPush).</summary>
    public Task SendAsync(IpcMessage message) =>
        _channel.WriteLineAsync(IpcSerializer.Serialize(message));

    /// <summary>
    /// Envia um DialogRequest e aguarda a DialogResponse correlacionada por Id.
    /// Se o timeout expirar, retorna DialogResponse sintética com Answer="TIMEOUT".
    /// </summary>
    public async Task<DialogResponse> SendDialogRequestAsync(DialogRequest request, TimeSpan timeout)
    {
        var task = _correlator.Register(request.Id, timeout);
        await _channel.WriteLineAsync(IpcSerializer.Serialize(request));
        return await task;
    }

    /// <summary>
    /// Loop de leitura: lê frames do canal e roteia DialogResponse ao correlator.
    /// Deve ser executado em background pelo host.
    /// </summary>
    public async Task StartReadLoopAsync(CancellationToken ct = default)
    {
        await foreach (var line in _channel.ReadLinesAsync(ct))
        {
            var msg = IpcSerializer.Deserialize(line);
            if (msg is DialogResponse dr)
                _correlator.Complete(dr);
        }
    }
}
