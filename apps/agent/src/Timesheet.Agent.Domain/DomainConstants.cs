namespace Timesheet.Agent.Domain;

public static class MarcacaoTipo
{
    public const string InicioJornada = "INICIO_JORNADA";
    public const string SaidaAlmoco = "SAIDA_ALMOCO";
    public const string RetornoAlmoco = "RETORNO_ALMOCO";
    public const string FimJornada = "FIM_JORNADA";
}

public static class OrigemMarcacao
{
    public const string AgenteAutomatico = "AGENTE_AUTOMATICO";
    public const string AgenteConfirmado = "AGENTE_CONFIRMADO";
}

public static class EstadoJornada
{
    public const string AguardandoInicio = "AGUARDANDO_INICIO";
    public const string EmJornada = "EM_JORNADA";
    public const string EmAlmoco = "EM_ALMOCO";
    public const string AguardandoFim = "AGUARDANDO_FIM";
    public const string Fechada = "FECHADA";
}
