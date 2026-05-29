namespace Timesheet.Agent.Infra.Http;

public sealed class AuthException : Exception
{
    public string Code { get; }

    public AuthException(string code, string? message = null)
        : base(message ?? code)
    {
        Code = code;
    }
}
