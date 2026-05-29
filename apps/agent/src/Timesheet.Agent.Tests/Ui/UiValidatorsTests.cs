using FluentAssertions;
using Timesheet.Agent.Ui.Common;
using Timesheet.Agent.Ui.Validation;
using Timesheet.Agent.Ui.ViewModels;
using Xunit;

namespace Timesheet.Agent.Tests.Ui;

public class UiValidatorsTests
{
    // ── CnpjValidator ─────────────────────────────────────────────────────────

    [Theory]
    [InlineData("11222333000181", true)]
    [InlineData("11222333000180", false)]
    [InlineData("11111111111111", false)]
    [InlineData("112223330001", false)]
    public void Cnpj_validates_check_digits(string cnpj, bool expected)
        => CnpjValidator.IsValid(cnpj).Should().Be(expected);

    [Fact]
    public void Cnpj_OnlyDigits_strips_mask()
        => CnpjValidator.OnlyDigits("11.222.333/0001-81").Should().Be("11222333000181");

    // ── HorariosValidator ─────────────────────────────────────────────────────

    [Fact]
    public void Horarios_cronologicos_ok()
        => HorariosValidator.SaoCronologicos(new(9, 0), new(12, 0), new(13, 0), new(18, 0)).Should().BeTrue();

    [Fact]
    public void Horarios_fora_de_ordem_falham()
        => HorariosValidator.SaoCronologicos(new(9, 0), new(13, 0), new(12, 0), new(18, 0)).Should().BeFalse();

    // ── PasswordStrength ──────────────────────────────────────────────────────

    [Fact]
    public void Password_curta_e_fraca()
        => PasswordStrength.Avaliar("123").Should().Be(ForcaSenha.Fraca);

    [Fact]
    public void Password_longa_mista_nao_e_fraca()
        => PasswordStrength.Avaliar("Senha123").Should().NotBe(ForcaSenha.Fraca);

    // ── WizardViewModel ───────────────────────────────────────────────────────

    [Fact]
    public void Wizard_passo1_invalido_com_cnpj_ruim()
    {
        var vm = new WizardViewModel { Nome = "Maria", Empresa = "ACME", Cnpj = "11222333000180" };
        vm.Passo1Valido.Should().BeFalse();
    }

    [Fact]
    public void Wizard_passo3_invalido_quando_senhas_diferem()
    {
        var vm = new WizardViewModel { Email = "m@x.com", Senha = "Senha123", SenhaConfirmacao = "Outra123" };
        vm.Passo3Valido.Should().BeFalse();
    }

    [Fact]
    public void Wizard_monta_request_com_cnpj_sem_mascara_e_horarios_formatados()
    {
        var vm = new WizardViewModel
        {
            Nome = "Maria Silva",
            Empresa = "ACME LTDA",
            Cnpj = "11.222.333/0001-81",
            Inicio = new(9, 0),
            SaidaAlmoco = new(12, 0),
            RetornoAlmoco = new(13, 0),
            Fim = new(18, 0),
            TrabalhaFds = false,
            Email = "maria@x.com",
            Senha = "Senha123",
            SenhaConfirmacao = "Senha123",
            EmailDestinatario = "rh@empresa.com",
        };
        var dto = vm.MontarRequest();
        dto.EmpresaCnpj.Should().Be("11222333000181");
        dto.HorarioInicioJornada.Should().Be("09:00:00");
        dto.HorarioFimJornada.Should().Be("18:00:00");
        dto.Senha.Should().Be(dto.SenhaConfirmacao);
    }

    // ── Saudacao ──────────────────────────────────────────────────────────────

    [Fact]
    public void Saudacao_por_faixa_horaria()
    {
        Saudacao.Para(8).Should().Be("Bom dia");
        Saudacao.Para(14).Should().Be("Boa tarde");
        Saudacao.Para(20).Should().Be("Boa noite");
    }

    // ── DialogViewModel ───────────────────────────────────────────────────────

    [Fact]
    public async Task DialogViewModel_timeout_resolve_com_TIMEOUT()
    {
        var vm = new DialogViewModel(id: "d1", kind: "PROMPT_FIM_JORNADA", segundos: 1);
        var resp = await vm.AguardarRespostaAsync();
        resp.Answer.Should().Be("TIMEOUT");
        resp.Id.Should().Be("d1");
    }
}
