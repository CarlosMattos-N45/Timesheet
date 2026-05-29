using Timesheet.Agent.Infra.Http;
using Timesheet.Agent.Ui.Validation;

namespace Timesheet.Agent.Ui.ViewModels;

public sealed class WizardViewModel
{
    // ── Passo 1 ───────────────────────────────────────────────────────────────

    public string Nome { get; set; } = string.Empty;
    public string Empresa { get; set; } = string.Empty;
    public string Cnpj { get; set; } = string.Empty;

    public bool Passo1Valido =>
        !string.IsNullOrWhiteSpace(Nome) &&
        !string.IsNullOrWhiteSpace(Empresa) &&
        CnpjValidator.IsValid(Cnpj);

    // ── Passo 2 ───────────────────────────────────────────────────────────────

    public TimeOnly Inicio { get; set; } = new(8, 0);
    public TimeOnly SaidaAlmoco { get; set; } = new(12, 0);
    public TimeOnly RetornoAlmoco { get; set; } = new(13, 0);
    public TimeOnly Fim { get; set; } = new(17, 0);
    public bool TrabalhaFds { get; set; }

    public bool Passo2Valido =>
        HorariosValidator.SaoCronologicos(Inicio, SaidaAlmoco, RetornoAlmoco, Fim);

    // ── Passo 3 ───────────────────────────────────────────────────────────────

    public string Email { get; set; } = string.Empty;
    public string Senha { get; set; } = string.Empty;
    public string SenhaConfirmacao { get; set; } = string.Empty;
    public string? EmailDestinatario { get; set; }

    public bool Passo3Valido =>
        !string.IsNullOrWhiteSpace(Email) &&
        PasswordStrength.Avaliar(Senha) != ForcaSenha.Fraca &&
        Senha == SenhaConfirmacao;

    // ── Montar request ────────────────────────────────────────────────────────

    public CreateTerceiroDto MontarRequest() => new(
        Nome: Nome,
        EmpresaNome: Empresa,
        EmpresaCnpj: CnpjValidator.OnlyDigits(Cnpj),
        HorarioInicioJornada: Inicio.ToString("HH:mm:ss"),
        HorarioSaidaAlmoco: SaidaAlmoco.ToString("HH:mm:ss"),
        HorarioRetornoAlmoco: RetornoAlmoco.ToString("HH:mm:ss"),
        HorarioFimJornada: Fim.ToString("HH:mm:ss"),
        TrabalhaFimDeSemana: TrabalhaFds,
        EmailContato: Email,
        EmailDestinatarioRelatorio: EmailDestinatario,
        Senha: Senha,
        SenhaConfirmacao: SenhaConfirmacao);
}
