namespace Timesheet.Agent.Ui.Validation;

public static class HorariosValidator
{
    /// <summary>
    /// Verifica se os 4 horários estão em ordem cronológica estrita:
    /// inicio &lt; saidaAlmoco &lt; retornoAlmoco &lt; fim
    /// </summary>
    public static bool SaoCronologicos(TimeOnly inicio, TimeOnly saidaAlmoco, TimeOnly retornoAlmoco, TimeOnly fim)
        => inicio < saidaAlmoco && saidaAlmoco < retornoAlmoco && retornoAlmoco < fim;
}
