namespace Timesheet.Agent.Ui.Validation;

public enum ForcaSenha { Fraca, Media, Forte }

public static class PasswordStrength
{
    public static ForcaSenha Avaliar(string senha)
    {
        if (senha is null || senha.Length < 8)
            return ForcaSenha.Fraca;

        bool temMaiuscula = senha.Any(char.IsUpper);
        bool temMinuscula = senha.Any(char.IsLower);
        bool temDigito = senha.Any(char.IsDigit);
        bool temEspecial = senha.Any(c => !char.IsLetterOrDigit(c));

        int score = (temMaiuscula ? 1 : 0) + (temMinuscula ? 1 : 0)
                  + (temDigito ? 1 : 0) + (temEspecial ? 1 : 0);

        return score >= 3 ? ForcaSenha.Forte : ForcaSenha.Media;
    }
}
