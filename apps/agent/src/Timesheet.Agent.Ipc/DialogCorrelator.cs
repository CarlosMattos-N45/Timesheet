using System;
using System.Collections.Concurrent;
using System.Threading;
using System.Threading.Tasks;

namespace Timesheet.Agent.Ipc;

/// <summary>
/// Correlaciona DialogRequests com suas DialogResponses por Id, com timeout configurável.
/// Thread-safe. Timeout → resposta sintética com Answer="TIMEOUT".
/// </summary>
public sealed class DialogCorrelator
{
    private readonly ConcurrentDictionary<string, TaskCompletionSource<DialogResponse>> _pending = new();

    public Task<DialogResponse> Register(string id, TimeSpan timeout)
    {
        var tcs = new TaskCompletionSource<DialogResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
        _pending[id] = tcs;
        var cts = new CancellationTokenSource(timeout);
        cts.Token.Register(() =>
        {
            if (_pending.TryRemove(id, out var t))
                t.TrySetResult(new DialogResponse(id, "TIMEOUT"));
            cts.Dispose();
        });
        return tcs.Task;
    }

    public void Complete(DialogResponse resp)
    {
        if (_pending.TryRemove(resp.Id, out var tcs))
            tcs.TrySetResult(resp);
    }
}
