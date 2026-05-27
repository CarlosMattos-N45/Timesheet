using FluentAssertions;
using Xunit;

namespace Timesheet.Agent.Tests;

public class SmokeTests
{
    [Fact]
    public void Smoke_RuntimeCheck_Adds()
    {
        // Valida pipeline de testes — xUnit + FluentAssertions + Moq disponíveis.
        var result = 1 + 1;
        result.Should().Be(2);
    }

    [Fact]
    public void Smoke_DomainAssembly_IsLoaded()
    {
        // Garante que a referência de projeto Domain está resolvida.
        var asm = typeof(Timesheet.Agent.Domain.AssemblyMarker).Assembly;
        asm.Should().NotBeNull();
        asm.GetName().Name.Should().Be("Timesheet.Agent.Domain");
    }
}
