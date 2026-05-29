namespace Timesheet.Agent.Service.Input;

public sealed record RetornoDeInatividade(DateTimeOffset InicioInatividade, DateTimeOffset FimInatividade);

public sealed class InactivityTracker
{
    private readonly int _limiarMs;
    private bool _foiInativoNaLeituraAnterior;
    private DateTimeOffset _ultimaAgora;

    public bool EstaInativo { get; private set; }
    public DateTimeOffset? InicioInatividade { get; private set; }
    public bool PrimeiroInputAposInatividade { get; private set; }

    public double DuracaoInatividadeContinuaMin =>
        EstaInativo && InicioInatividade.HasValue
            ? (_ultimaAgora - InicioInatividade.Value).TotalMinutes
            : 0;

    public event Action<RetornoDeInatividade>? OnRetornoDeInatividade;

    public InactivityTracker(int limiarInatividadeSeg = 30)
    {
        _limiarMs = limiarInatividadeSeg * 1000;
    }

    public void Observe(uint idleMs, DateTimeOffset agora)
    {
        _ultimaAgora = agora;
        var inativoAgora = idleMs >= (uint)_limiarMs;

        if (inativoAgora)
        {
            if (!_foiInativoNaLeituraAnterior)
            {
                // transição ativo -> inativo: registra início da inatividade
                InicioInatividade = CalcularInicioInatividade(agora, idleMs);
            }
            // continua inativo: mantém InicioInatividade original
            EstaInativo = true;
            PrimeiroInputAposInatividade = false;
            _foiInativoNaLeituraAnterior = true;
        }
        else if (_foiInativoNaLeituraAnterior)
        {
            // transição inativo -> ativo: dispara evento e seta flag de primeiro input
            var inicioCapturado = InicioInatividade!.Value;
            EstaInativo = false;
            _foiInativoNaLeituraAnterior = false;
            PrimeiroInputAposInatividade = true;
            OnRetornoDeInatividade?.Invoke(new RetornoDeInatividade(inicioCapturado, agora));
        }
        else
        {
            // ativo consecutivo: limpa flag de primeiro input e inicio
            if (PrimeiroInputAposInatividade)
            {
                PrimeiroInputAposInatividade = false;
                InicioInatividade = null;
            }
        }
    }

    private static DateTimeOffset CalcularInicioInatividade(DateTimeOffset agora, uint idleMs) =>
        agora - TimeSpan.FromMilliseconds(idleMs);
}
