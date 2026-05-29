using FluentAssertions;
using Timesheet.Agent.Service.Input;
using Xunit;

namespace Timesheet.Agent.Tests.Service;

public class InactivityTrackerTests
{
    [Fact]
    public void Idle_below_threshold_is_not_inactive()
    {
        var t = new InactivityTracker(limiarInatividadeSeg: 30);
        t.Observe(idleMs: 5_000, agora: TestData.At(12, 0, 5));
        t.EstaInativo.Should().BeFalse();
        t.InicioInatividade.Should().BeNull();
    }

    [Fact]
    public void Crossing_threshold_marks_inactive_and_records_start()
    {
        var t = new InactivityTracker(30);
        t.Observe(idleMs: 30_000, agora: TestData.At(12, 0, 30));
        t.EstaInativo.Should().BeTrue();
        // inicio = agora - idle = 12:00:00
        t.InicioInatividade!.Value.Should().Be(TestData.At(12, 0, 0));
    }

    [Fact]
    public void Continuous_inactivity_keeps_original_start_and_grows_duration()
    {
        var t = new InactivityTracker(30);
        t.Observe(30_000, TestData.At(12, 0, 30));
        var inicio = t.InicioInatividade;
        t.Observe(600_000, TestData.At(12, 10, 0));
        t.InicioInatividade.Should().Be(inicio);
        t.DuracaoInatividadeContinuaMin.Should().BeGreaterThanOrEqualTo(10);
    }

    [Fact]
    public void Return_to_activity_raises_event_with_window()
    {
        var t = new InactivityTracker(30);
        RetornoDeInatividade? capturado = null;
        t.OnRetornoDeInatividade += e => capturado = e;
        t.Observe(30_000, TestData.At(12, 0, 30));     // inativo, inicio 12:00:00
        t.Observe(0, TestData.At(12, 11, 0));           // voltou input
        t.EstaInativo.Should().BeFalse();
        capturado.Should().NotBeNull();
        capturado!.InicioInatividade.Should().Be(TestData.At(12, 0, 0));
        capturado.FimInatividade.Should().Be(TestData.At(12, 11, 0));
    }

    [Fact]
    public void PrimeiroInputAposInatividade_true_once_then_false()
    {
        var t = new InactivityTracker(30);
        t.Observe(30_000, TestData.At(12, 0, 30));
        t.Observe(0, TestData.At(12, 11, 0));
        t.PrimeiroInputAposInatividade.Should().BeTrue();
        t.Observe(0, TestData.At(12, 11, 30));
        t.PrimeiroInputAposInatividade.Should().BeFalse();
    }

    [Fact]
    public void Win32Provider_returns_nonnegative_idle()  // roda em Windows
    {
        var p = new Win32LastInputProvider();
        p.GetIdleMilliseconds().Should().BeGreaterThanOrEqualTo(0u);
    }
}
