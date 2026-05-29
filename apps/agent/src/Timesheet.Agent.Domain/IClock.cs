namespace Timesheet.Agent.Domain;

public interface IClock
{
    DateTimeOffset NowUtc { get; }
    DateTimeOffset NowLocal { get; }
}

public sealed class SystemClock : IClock
{
    private static readonly TimeZoneInfo Tz =
        TimeZoneInfo.FindSystemTimeZoneById(TimeZoneConstants.SaoPaulo);
    public DateTimeOffset NowUtc => DateTimeOffset.UtcNow;
    public DateTimeOffset NowLocal => TimeZoneInfo.ConvertTime(DateTimeOffset.UtcNow, Tz);
}

public sealed class FakeClock(DateTimeOffset now) : IClock
{
    public DateTimeOffset NowUtc { get; set; } = now.ToUniversalTime();
    public DateTimeOffset NowLocal => TimeZoneInfo.ConvertTime(
        NowUtc, TimeZoneInfo.FindSystemTimeZoneById(TimeZoneConstants.SaoPaulo));
}

public static class TimeZoneConstants
{
    public const string SaoPaulo = "America/Sao_Paulo";
}
