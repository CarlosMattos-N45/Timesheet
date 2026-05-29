namespace Timesheet.Agent.Infra.Http;

public enum SyncOutcome
{
    Created,
    AlreadyExists,
    DiscardLocal,
    Rejected,
    TransientFailure,
}
