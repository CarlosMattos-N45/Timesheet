namespace Timesheet.Agent.Domain;

public abstract record DecisaoJornada;

public sealed record NenhumaAcao : DecisaoJornada;

public sealed record RegistrarAutomatico(
    string Tipo,
    DateTimeOffset Horario,
    string Origem,
    int? AtrasoMinutos = null) : DecisaoJornada;

public sealed record RegistrarConfirmado(
    string Tipo,
    DateTimeOffset Horario,
    string Origem) : DecisaoJornada;

public sealed record RegistrarPendente(
    string Tipo,
    DateTimeOffset Horario) : DecisaoJornada;

public sealed record ExigeDialogo(
    string Kind,
    DateTimeOffset HorarioProposto,
    DateTimeOffset? Fallback = null) : DecisaoJornada;

public sealed record Fechar(
    string Tipo,
    DateTimeOffset Horario,
    string Atividade) : DecisaoJornada;

public sealed record FecharPendente(
    string Tipo,
    DateTimeOffset Horario) : DecisaoJornada;

public sealed record Relembrar(DateTimeOffset Em) : DecisaoJornada;
