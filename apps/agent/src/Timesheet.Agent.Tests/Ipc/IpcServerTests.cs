using System;
using System.Threading.Tasks;
using FluentAssertions;
using Timesheet.Agent.Ipc;
using Xunit;

namespace Timesheet.Agent.Tests.Ipc;

public class IpcServerTests
{
    [Fact]
    public async Task SendAsync_writes_serialized_toast_to_channel()
    {
        var channel = new FakeChannel();
        var server = new IpcServer(channel, new DialogCorrelator());
        await server.SendAsync(new ToastMessage("Bom dia", "Maria", 10));
        channel.Written.Should().ContainSingle()
            .Which.Should().Contain("\"type\":\"TOAST\"").And.EndWith("\n");
    }

    [Fact]
    public async Task SendDialogRequest_resolves_when_response_frame_arrives()
    {
        var channel = new FakeChannel();
        var server = new IpcServer(channel, new DialogCorrelator());
        var pending = server.SendDialogRequestAsync(
            new DialogRequest("d9", "PROMPT_FIM_JORNADA", new()), TimeSpan.FromSeconds(5));
        // simula o WPF respondendo
        channel.Inject(IpcSerializer.Serialize(new DialogResponse("d9", "SIM")));
        (await pending).Answer.Should().Be("SIM");
    }
}
