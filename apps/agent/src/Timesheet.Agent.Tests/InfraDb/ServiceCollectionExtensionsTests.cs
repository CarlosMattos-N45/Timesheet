using FluentAssertions;
using Microsoft.Extensions.DependencyInjection;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;
using Xunit;

namespace Timesheet.Agent.Tests.InfraDb;

public class ServiceCollectionExtensionsTests
{
    [Fact]
    public void AddAgentInfra_registers_all_services()
    {
        var services = new ServiceCollection();
        services.AddAgentInfra(":memory:");

        var provider = services.BuildServiceProvider();

        // IClock is registered as singleton
        var clock = provider.GetService<IClock>();
        clock.Should().NotBeNull();
        clock.Should().BeOfType<SystemClock>();

        // Repositories are registered as scoped
        using var scope = provider.CreateScope();
        var marcacaoRepo = scope.ServiceProvider.GetService<MarcacaoLocalRepository>();
        marcacaoRepo.Should().NotBeNull();

        var configRepo = scope.ServiceProvider.GetService<ConfiguracaoLocalRepository>();
        configRepo.Should().NotBeNull();

        var estadoRepo = scope.ServiceProvider.GetService<EstadoJornadaRepository>();
        estadoRepo.Should().NotBeNull();
    }
}
