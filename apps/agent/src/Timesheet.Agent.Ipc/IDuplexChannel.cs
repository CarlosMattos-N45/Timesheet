using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace Timesheet.Agent.Ipc;

/// <summary>
/// Abstração de canal bidirecional de leitura/escrita de linhas.
/// Permite testar IpcServer/IpcClient sem abrir NamedPipe real.
/// </summary>
public interface IDuplexChannel
{
    Task WriteLineAsync(string line);
    IAsyncEnumerable<string> ReadLinesAsync(CancellationToken ct = default);
}
