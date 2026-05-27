namespace Timesheet.Agent.Domain;

public sealed class MarcacaoLocal
{
    public required string Id { get; init; }                  // UUID v4 (= idempotency_key no backend)
    public required string Tipo { get; init; }                // INICIO_JORNADA | SAIDA_ALMOCO | RETORNO_ALMOCO | FIM_JORNADA
    public required string HorarioRegistrado { get; init; }   // ISO 8601 UTC
    public string? HorarioEfetivo { get; set; }
    public required string Origem { get; init; }              // AGENTE_AUTOMATICO | AGENTE_CONFIRMADO
    public bool ConfirmadoPeloUsuario { get; set; }
    public required string DataJornada { get; init; }         // YYYY-MM-DD
    public bool Sincronizada { get; set; }
    public int TentativasSync { get; set; }
    public string? UltimoErroSync { get; set; }
    public string? ProximaTentativaEm { get; set; }
    public required string CriadoEm { get; init; }            // ISO 8601 UTC
}
