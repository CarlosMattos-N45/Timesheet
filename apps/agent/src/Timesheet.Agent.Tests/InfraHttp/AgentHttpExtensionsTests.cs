using FluentAssertions;
using Microsoft.Extensions.DependencyInjection;
using Timesheet.Agent.Infra.Http;
using Xunit;

namespace Timesheet.Agent.Tests.InfraHttp;

public class AgentHttpExtensionsTests
{
    [Fact]
    public void AddAgentHttp_registers_IBackendClient()
    {
        var services = new ServiceCollection();
        services.AddAgentHttp("http://127.0.0.1:8765");

        var provider = services.BuildServiceProvider();
        var client = provider.GetService<IBackendClient>();
        client.Should().NotBeNull();
        client.Should().BeOfType<BackendClient>();
    }
}
