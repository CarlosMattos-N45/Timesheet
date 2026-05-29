using System.Collections.Generic;
using System.IO;
using System.IO.Pipes;
using System.Runtime.CompilerServices;
using System.Runtime.Versioning;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Threading;
using System.Threading.Tasks;

namespace Timesheet.Agent.Ipc;

/// <summary>
/// Implementação concreta de IDuplexChannel sobre NamedPipe com ACL owner-only.
/// [SupportedOSPlatform("windows")] — usa PipeSecurity e WindowsIdentity.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class NamedPipeChannel : IDuplexChannel
{
    public const string PipeName = "TimesheetAgent";

    private readonly Stream _stream;
    private readonly StreamReader _reader;
    private readonly StreamWriter _writer;

    private NamedPipeChannel(Stream stream)
    {
        _stream = stream;
        _reader = new StreamReader(stream, leaveOpen: true);
        _writer = new StreamWriter(stream, leaveOpen: true) { AutoFlush = true };
    }

    /// <summary>
    /// Cria o lado servidor com ACL restrita ao owner (SID do processo Service).
    /// Aguarda conexão do cliente antes de retornar.
    /// </summary>
    public static async Task<NamedPipeChannel> CreateServerAsync(CancellationToken ct = default)
    {
        var security = new PipeSecurity();
        var owner = WindowsIdentity.GetCurrent().Owner!;
        security.AddAccessRule(new PipeAccessRule(
            owner,
            PipeAccessRights.FullControl,
            AccessControlType.Allow));

        var pipe = NamedPipeServerStreamAcl.Create(
            PipeName,
            PipeDirection.InOut,
            maxNumberOfServerInstances: 1,
            PipeTransmissionMode.Byte,
            PipeOptions.Asynchronous,
            inBufferSize: 0,
            outBufferSize: 0,
            pipeSecurity: security);

        await pipe.WaitForConnectionAsync(ct);
        return new NamedPipeChannel(pipe);
    }

    /// <summary>Cria o lado cliente e conecta ao servidor.</summary>
    public static async Task<NamedPipeChannel> CreateClientAsync(CancellationToken ct = default)
    {
        var pipe = new NamedPipeClientStream(".", PipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
        await pipe.ConnectAsync(ct);
        return new NamedPipeChannel(pipe);
    }

    /// <inheritdoc/>
    public Task WriteLineAsync(string line) => _writer.WriteAsync(line);

    /// <inheritdoc/>
    public async IAsyncEnumerable<string> ReadLinesAsync(
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        string? line;
        while ((line = await _reader.ReadLineAsync(ct)) is not null)
        {
            yield return line;
        }
    }

    public void Dispose()
    {
        _writer.Dispose();
        _reader.Dispose();
        _stream.Dispose();
    }
}
