namespace Timesheet.Agent.Infra.Http;

internal sealed record ApiError(string? Code, string? Message);
