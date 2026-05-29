namespace Timesheet.Agent.Domain;

public sealed record HorariosJornada(
    TimeOnly Inicio,
    TimeOnly SaidaAlmoco,
    TimeOnly RetornoAlmoco,
    TimeOnly Fim);
