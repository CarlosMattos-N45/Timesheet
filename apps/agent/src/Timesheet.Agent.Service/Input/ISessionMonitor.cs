namespace Timesheet.Agent.Service.Input;

public interface ISessionMonitor
{
    event Action SessionLogon;
    void Start();
    void Stop();
}
