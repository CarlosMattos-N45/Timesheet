using System;
using System.Threading.Tasks;
using FluentAssertions;
using Timesheet.Agent.Ipc;
using Xunit;

namespace Timesheet.Agent.Tests.Ipc;

public class DialogCorrelatorTests
{
    [Fact]
    public async Task Complete_resolves_pending_task_with_answer()
    {
        var c = new DialogCorrelator();
        var task = c.Register("d1", timeout: TimeSpan.FromSeconds(5));
        c.Complete(new DialogResponse("d1", "SIM"));
        (await task).Answer.Should().Be("SIM");
    }

    [Fact]
    public async Task Timeout_resolves_with_TIMEOUT_answer()
    {
        var c = new DialogCorrelator();
        var task = c.Register("d2", timeout: TimeSpan.FromMilliseconds(50));
        var resp = await task;
        resp.Id.Should().Be("d2");
        resp.Answer.Should().Be("TIMEOUT");
    }

    [Fact]
    public void Complete_unknown_id_is_ignored()
    {
        var c = new DialogCorrelator();
        var act = () => c.Complete(new DialogResponse("ghost", "SIM"));
        act.Should().NotThrow();
    }

    [Fact]
    public async Task Complete_only_resolves_matching_id()
    {
        var c = new DialogCorrelator();
        var t3 = c.Register("d3", TimeSpan.FromSeconds(5));
        var t4 = c.Register("d4", TimeSpan.FromSeconds(5));
        c.Complete(new DialogResponse("d4", "NAO"));
        (await t4).Answer.Should().Be("NAO");
        t3.IsCompleted.Should().BeFalse();
    }
}
