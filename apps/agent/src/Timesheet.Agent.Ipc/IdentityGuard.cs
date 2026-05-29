using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;

namespace Timesheet.Agent.Ipc;

/// <summary>
/// Valida a identidade do processo cliente do NamedPipe por PID e SessionId.
/// Previne injeção de processo malicioso (Spec §7).
/// </summary>
[SupportedOSPlatform("windows")]
public static class IdentityGuard
{
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetNamedPipeClientProcessId(
        Microsoft.Win32.SafeHandles.SafePipeHandle pipe,
        out uint clientProcessId);

    /// <summary>
    /// Obtém o PID do processo cliente conectado ao NamedPipe.
    /// </summary>
    public static uint GetClientPid(Microsoft.Win32.SafeHandles.SafePipeHandle pipeHandle)
    {
        if (!GetNamedPipeClientProcessId(pipeHandle, out var pid))
            throw new InvalidOperationException(
                $"GetNamedPipeClientProcessId falhou. Win32Error={Marshal.GetLastWin32Error()}");
        return pid;
    }

    /// <summary>
    /// Retorna true se o processo com <paramref name="clientPid"/> pertence à sessão esperada.
    /// </summary>
    public static bool IsTrusted(uint clientPid, int expectedSessionId)
    {
        try
        {
            using var process = Process.GetProcessById((int)clientPid);
            return process.SessionId == expectedSessionId;
        }
        catch (ArgumentException)
        {
            // Processo não existe mais
            return false;
        }
    }
}
