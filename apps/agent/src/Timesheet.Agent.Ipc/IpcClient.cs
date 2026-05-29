using System;
using System.Threading;
using System.Threading.Tasks;

namespace Timesheet.Agent.Ipc;

/// <summary>
/// Lado WPF do canal IPC. Recebe mensagens do Service e envia DialogResponse de volta.
/// </summary>
public sealed class IpcClient
{
    private readonly IDuplexChannel _channel;

    /// <summary>Disparado para cada IpcMessage recebida do Service.</summary>
    public event Action<IpcMessage>? OnMessage;

    public IpcClient(IDuplexChannel channel)
    {
        _channel = channel;
    }

    /// <summary>Envia a resposta do diálogo de volta ao Service.</summary>
    public Task SendAsync(DialogResponse response) =>
        _channel.WriteLineAsync(IpcSerializer.Serialize(response));

    /// <summary>
    /// Loop de leitura: lê frames do canal e dispara OnMessage para cada mensagem recebida.
    /// Deve ser executado em background pelo host WPF.
    /// </summary>
    public async Task StartReadLoopAsync(CancellationToken ct = default)
    {
        await foreach (var line in _channel.ReadLinesAsync(ct))
        {
            var msg = IpcSerializer.Deserialize(line);
            OnMessage?.Invoke(msg);
        }
    }
}
