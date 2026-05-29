namespace Timesheet.Agent.Domain;

public static class JourneyStateMachine
{
    /// <summary>
    /// RF-003: Avalia o login do Windows e decide a marcação de INICIO_JORNADA.
    /// </summary>
    public static DecisaoJornada AvaliarLogin(
        DateTimeOffset t,
        HorariosJornada horarios,
        bool ehFimDeSemana,
        bool trabalhaFds)
    {
        if (ehFimDeSemana && !trabalhaFds)
            return new NenhumaAcao();

        var hIniOffset = JanelaTolerancia(horarios.Inicio, DateOnly.FromDateTime(t.Date)).Centro;
        var diff = t - hIniOffset;

        if (Math.Abs(diff.TotalMinutes) <= RegrasJornada.ToleranciaMin)
            return new RegistrarAutomatico(MarcacaoTipo.InicioJornada, t, OrigemMarcacao.AgenteAutomatico);

        if (diff.TotalMinutes > RegrasJornada.ToleranciaMin)
            return new RegistrarAutomatico(
                MarcacaoTipo.InicioJornada, t, OrigemMarcacao.AgenteAutomatico,
                AtrasoMinutos: (int)diff.TotalMinutes);

        // antecipação: diff < -30min
        return new ExigeDialogo("CONFIRM_INICIO_ANTECIPADO", t, Fallback: hIniOffset);
    }

    /// <summary>
    /// RF-003: Resolve o diálogo de início antecipado.
    /// </summary>
    public static RegistrarConfirmado ResolverInicioAntecipado(
        string answer,
        DateTimeOffset t,
        DateTimeOffset hIni)
    {
        var horario = answer == "SIM" ? t : hIni;
        return new RegistrarConfirmado(MarcacaoTipo.InicioJornada, horario, OrigemMarcacao.AgenteConfirmado);
    }

    /// <summary>
    /// RF-004: Avalia inatividade para detectar SAIDA_ALMOCO.
    /// </summary>
    public static DecisaoJornada AvaliarInatividade(
        DateTimeOffset inicioInatividade,
        int duracaoMin,
        HorariosJornada horarios)
    {
        if (duracaoMin < RegrasJornada.InatividadeAlmocoMin)
            return new NenhumaAcao();

        var dia = DateOnly.FromDateTime(inicioInatividade.Date);
        var (janelaInicio, janelaFim, _) = JanelaTolerancia(horarios.SaidaAlmoco, dia);

        var fimInatividade = inicioInatividade.AddMinutes(duracaoMin);
        var intersecta = inicioInatividade <= janelaFim && fimInatividade >= janelaInicio;

        if (!intersecta)
            return new NenhumaAcao();

        return new RegistrarAutomatico(MarcacaoTipo.SaidaAlmoco, inicioInatividade, OrigemMarcacao.AgenteAutomatico);
    }

    /// <summary>
    /// RF-005: Avalia o retorno após almoço.
    /// </summary>
    public static DecisaoJornada AvaliarRetorno(DateTimeOffset t, HorariosJornada horarios)
    {
        var dia = DateOnly.FromDateTime(t.Date);
        var (janelaInicio, janelaFim, _) = JanelaTolerancia(horarios.RetornoAlmoco, dia);

        if (t >= janelaInicio && t <= janelaFim)
            return new RegistrarAutomatico(MarcacaoTipo.RetornoAlmoco, t, OrigemMarcacao.AgenteAutomatico);

        return new ExigeDialogo("CONFIRM_RETORNO_FORA_JANELA", t);
    }

    /// <summary>
    /// RF-005: Resolve o diálogo de retorno fora da janela.
    /// </summary>
    public static DecisaoJornada ResolverRetornoForaJanela(string answer, DateTimeOffset t)
    {
        if (answer == "SIM")
            return new RegistrarConfirmado(MarcacaoTipo.RetornoAlmoco, t, OrigemMarcacao.AgenteConfirmado);

        return new RegistrarPendente(MarcacaoTipo.RetornoAlmoco, t);
    }

    /// <summary>
    /// RF-006: Avalia o fim de jornada.
    /// </summary>
    public static DecisaoJornada AvaliarFim(DateTimeOffset t, HorariosJornada horarios)
    {
        var dia = DateOnly.FromDateTime(t.Date);
        var hFimOffset = JanelaTolerancia(horarios.Fim, dia).Centro;

        if (t >= hFimOffset)
            return new ExigeDialogo("PROMPT_FIM_JORNADA", hFimOffset);

        return new NenhumaAcao();
    }

    /// <summary>
    /// RF-006: Resolve o diálogo de fim de jornada.
    /// </summary>
    public static DecisaoJornada ResolverFim(string answer, string? atividade, DateTimeOffset t)
    {
        if (answer == "SIM")
        {
            if (atividade == null || atividade.Length < RegrasJornada.MinCharsAtividade)
                throw new ArgumentException(
                    $"Atividade deve ter pelo menos {RegrasJornada.MinCharsAtividade} caracteres.",
                    nameof(atividade));

            return new Fechar(MarcacaoTipo.FimJornada, t, atividade);
        }

        // NAO ou TIMEOUT: relembrar em 30 min
        return new Relembrar(t.AddMinutes(RegrasJornada.RepromptFimMin));
    }

    /// <summary>
    /// RF-006: Avalia auto-encerramento por inatividade prolongada após h_fim.
    /// </summary>
    public static DecisaoJornada AvaliarAutoEncerramento(
        DateTimeOffset ultimoInput,
        DateTimeOffset agora,
        HorariosJornada horarios)
    {
        var dia = DateOnly.FromDateTime(agora.Date);
        var hFimOffset = JanelaTolerancia(horarios.Fim, dia).Centro;

        if (agora >= hFimOffset && (agora - ultimoInput).TotalMinutes >= RegrasJornada.AutoEncerramentoMin)
            return new FecharPendente(MarcacaoTipo.FimJornada, ultimoInput);

        return new NenhumaAcao();
    }

    // --- helpers privados ---

    /// <summary>
    /// Calcula a janela de tolerância [h-30min, h+30min] para um horário cadastrado no dia de referência.
    /// O offset BRT (-03:00) é fixo conforme o domínio do sistema (funcionários BR).
    /// </summary>
    private static (DateTimeOffset Inicio, DateTimeOffset Fim, DateTimeOffset Centro) JanelaTolerancia(
        TimeOnly h, DateOnly dia)
    {
        var offset = TimeSpan.FromHours(-3); // BRT (America/Sao_Paulo, sem DST em 2026)
        var centro = new DateTimeOffset(dia.Year, dia.Month, dia.Day, h.Hour, h.Minute, h.Second, offset);
        return (centro.AddMinutes(-RegrasJornada.ToleranciaMin),
                centro.AddMinutes(RegrasJornada.ToleranciaMin),
                centro);
    }
}
