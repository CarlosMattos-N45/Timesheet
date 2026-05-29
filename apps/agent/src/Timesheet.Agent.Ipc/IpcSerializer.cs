using System;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Timesheet.Agent.Ipc;

public static class IpcSerializer
{
    private static readonly JsonSerializerOptions Opts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    public static string Serialize(IpcMessage msg) =>
        JsonSerializer.Serialize(msg, Opts) + "\n";

    public static IpcMessage Deserialize(string line) =>
        JsonSerializer.Deserialize<IpcMessage>(line.Trim(), Opts)
        ?? throw new FormatException("Frame IPC inválido");
}
