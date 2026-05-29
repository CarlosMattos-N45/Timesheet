using System.Runtime.Versioning;
using Microsoft.Win32;

namespace Timesheet.Agent.Service.Input;

[SupportedOSPlatform("windows")]
public sealed class WindowsSessionMonitor : ISessionMonitor
{
    public event Action? SessionLogon;

    public void Start()
    {
        SystemEvents.SessionSwitch += OnSessionSwitch;
    }

    public void Stop()
    {
        SystemEvents.SessionSwitch -= OnSessionSwitch;
    }

    private void OnSessionSwitch(object sender, SessionSwitchEventArgs e)
    {
        if (e.Reason == SessionSwitchReason.SessionLogon ||
            e.Reason == SessionSwitchReason.SessionUnlock)
        {
            SessionLogon?.Invoke();
        }
    }
}
