namespace Timesheet.Agent.Domain;

public sealed class EstadoJornadaAtual
{
    public int Id { get; init; } = 1;                         // singleton: CHECK (Id = 1)
    public required string DataJornada { get; set; }
    public required string Status { get; set; }               // AGUARDANDO_INICIO | EM_JORNADA | EM_ALMOCO | AGUARDANDO_FIM | FECHADA
    public string? UltimoInput { get; set; }
    public required string AtualizadoEm { get; set; }
}
