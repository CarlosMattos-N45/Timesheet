namespace Timesheet.Agent.Ui.Common;

public static class Saudacao
{
    /// <summary>
    /// Retorna a saudação conforme a faixa horária:
    /// 0–11 → "Bom dia", 12–17 → "Boa tarde", 18–23 → "Boa noite"
    /// </summary>
    public static string Para(int hora) => hora switch
    {
        >= 0 and <= 11 => "Bom dia",
        >= 12 and <= 17 => "Boa tarde",
        _ => "Boa noite"
    };
}
