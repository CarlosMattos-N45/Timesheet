using FluentAssertions;
using Timesheet.Agent.Ipc;
using Xunit;

namespace Timesheet.Agent.Tests.Ipc;

public class IpcSerializerTests
{
    [Fact]
    public void Serialize_toast_is_newline_terminated_json()
    {
        var json = IpcSerializer.Serialize(new ToastMessage("Bom dia", "corpo", 10));
        json.Should().EndWith("\n");
        json.Should().Contain("\"type\":\"TOAST\"");
    }

    [Fact]
    public void Deserialize_dialog_response_roundtrips_answer()
    {
        var json = "{\"type\":\"DIALOG_RESPONSE\",\"id\":\"abc\",\"answer\":\"SIM\"}\n";
        var msg = IpcSerializer.Deserialize(json);
        msg.Should().BeOfType<DialogResponse>().Which.Answer.Should().Be("SIM");
    }
}
