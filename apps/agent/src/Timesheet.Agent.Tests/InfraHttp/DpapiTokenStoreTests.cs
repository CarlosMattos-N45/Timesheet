using FluentAssertions;
using Timesheet.Agent.Infra.Http;
using Xunit;

namespace Timesheet.Agent.Tests.InfraHttp;

public class DpapiTokenStoreTests
{
    [Fact]
    public void Protect_then_Unprotect_roundtrips()
    {
        // DpapiTokenStore only works on Windows; the test project targets net8.0-windows,
        // so this test will only ever execute on Windows.
        if (!OperatingSystem.IsWindows())
        {
            // Defensive guard; should never reach here on the configured target.
            return;
        }

        var store = new DpapiTokenStore();
        var blob = store.Protect("RT");
        blob.Should().NotBe("RT");           // cifrado — deve diferir do texto puro
        store.Unprotect(blob).Should().Be("RT");
    }
}
