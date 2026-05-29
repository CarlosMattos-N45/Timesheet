using Timesheet.Agent.Infra.Http;
using Timesheet.Agent.Ui.Validation;
using Timesheet.Agent.Ui.ViewModels;

namespace Timesheet.Agent.Ui.Views;

public partial class WizardWindow : System.Windows.Window
{
    private readonly WizardViewModel _vm = new();
    private int _passo = 1;

    public CreateTerceiroDto? Result { get; private set; }

    public WizardWindow()
    {
        InitializeComponent();
        AtualizarPasso();
    }

    private void AtualizarPasso()
    {
        PnlPasso1.Visibility = _passo == 1 ? System.Windows.Visibility.Visible : System.Windows.Visibility.Collapsed;
        PnlPasso2.Visibility = _passo == 2 ? System.Windows.Visibility.Visible : System.Windows.Visibility.Collapsed;
        PnlPasso3.Visibility = _passo == 3 ? System.Windows.Visibility.Visible : System.Windows.Visibility.Collapsed;
        TxtPassoTitulo.Text = $"Passo {_passo} de 3";
        BtnVoltar.IsEnabled = _passo > 1;
        BtnAvancar.Content = _passo == 3 ? "Finalizar" : "Avançar";
    }

    private void BtnAvancar_Click(object sender, System.Windows.RoutedEventArgs e)
    {
        if (_passo == 1)
        {
            _vm.Nome = TxtNome.Text;
            _vm.Empresa = TxtEmpresa.Text;
            _vm.Cnpj = TxtCnpj.Text;

            TxtCnpjErro.Visibility = _vm.Passo1Valido
                ? System.Windows.Visibility.Collapsed
                : System.Windows.Visibility.Visible;
            if (!_vm.Passo1Valido) return;
            _passo = 2;
        }
        else if (_passo == 2)
        {
            if (TryParseHorarios(out var inicio, out var saida, out var retorno, out var fim))
            {
                _vm.Inicio = inicio;
                _vm.SaidaAlmoco = saida;
                _vm.RetornoAlmoco = retorno;
                _vm.Fim = fim;
                _vm.TrabalhaFds = ChkFds.IsChecked == true;

                TxtHorariosErro.Visibility = _vm.Passo2Valido
                    ? System.Windows.Visibility.Collapsed
                    : System.Windows.Visibility.Visible;
                if (!_vm.Passo2Valido) return;
            }
            else
            {
                TxtHorariosErro.Visibility = System.Windows.Visibility.Visible;
                TxtHorariosErro.Text = "Formato inválido — use HH:MM";
                return;
            }
            _passo = 3;
        }
        else if (_passo == 3)
        {
            _vm.Email = TxtEmail.Text;
            _vm.Senha = PbSenha.Password;
            _vm.SenhaConfirmacao = PbSenhaConfirmacao.Password;
            _vm.EmailDestinatario = string.IsNullOrWhiteSpace(TxtEmailDestinatario.Text)
                ? null
                : TxtEmailDestinatario.Text;

            if (!_vm.Passo3Valido)
            {
                System.Windows.MessageBox.Show(
                    "Verifique a senha (mín. 8 caracteres, senhas devem coincidir).",
                    "Dados inválidos",
                    System.Windows.MessageBoxButton.OK,
                    System.Windows.MessageBoxImage.Warning);
                return;
            }

            Result = _vm.MontarRequest();
            DialogResult = true;
            Close();
            return;
        }

        AtualizarPasso();
    }

    private void BtnVoltar_Click(object sender, System.Windows.RoutedEventArgs e)
    {
        if (_passo > 1) _passo--;
        AtualizarPasso();
    }

    private bool TryParseHorarios(out TimeOnly inicio, out TimeOnly saida, out TimeOnly retorno, out TimeOnly fim)
    {
        inicio = saida = retorno = fim = default;
        return TimeOnly.TryParse(TxtInicio.Text, out inicio)
            && TimeOnly.TryParse(TxtSaidaAlmoco.Text, out saida)
            && TimeOnly.TryParse(TxtRetornoAlmoco.Text, out retorno)
            && TimeOnly.TryParse(TxtFim.Text, out fim);
    }
}
