using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Channels;
using Timesheet.Agent.Ipc;

namespace Timesheet.Agent.Tests.Ipc;

/// <summary>
/// Canal em memória para testes de IpcServer/IpcClient sem NamedPipe real.
/// </summary>
public sealed class FakeChannel : IDuplexChannel
{
    public List<string> Written { get; } = new();

    private readonly Channel<string> _incoming = Channel.CreateUnbounded<string>();

    public System.Threading.Tasks.Task WriteLineAsync(string line)
    {
        Written.Add(line);
        return System.Threading.Tasks.Task.CompletedTask;
    }

    public async IAsyncEnumerable<string> ReadLinesAsync(
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        await foreach (var line in _incoming.Reader.ReadAllAsync(ct))
        {
            yield return line;
        }
    }

    /// <summary>Injeta um frame como se viesse do outro lado do canal.</summary>
    public void Inject(string line) => _incoming.Writer.TryWrite(line);
}
