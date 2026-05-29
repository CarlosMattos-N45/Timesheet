using Timesheet.Agent.Ipc;
using Timesheet.Agent.Ui.ViewModels;

namespace Timesheet.Agent.Ui.Views;

public partial class DialogWindow : System.Windows.Window
{
    private readonly DialogViewModel _vm;
    private readonly int _totalSegundos;
    private System.Windows.Threading.DispatcherTimer? _uiTimer;

    public DialogWindow(DialogRequest request, int segundos = 60)
    {
        InitializeComponent();
        _vm = new DialogViewModel(request.Id, request.Kind, segundos);
        _totalSegundos = segundos;

        TxtMensagem.Text = FormatarMensagem(request.Kind);
        PbContagem.Maximum = segundos;
        PbContagem.Value = segundos;
        TxtSegundos.Text = $"{segundos}s";

        if (request.Kind == "PROMPT_FIM_JORNADA")
        {
            TxtAtividade.Visibility = System.Windows.Visibility.Visible;
            BtnSim.Content = "Salvar e encerrar";
            BtnSim.IsEnabled = false;
            TxtAtividade.TextChanged += (_, _) =>
                BtnSim.IsEnabled = TxtAtividade.Text.Length >= 10;
        }

        Loaded += OnLoaded;
    }

    private async void OnLoaded(object sender, System.Windows.RoutedEventArgs e)
    {
        _uiTimer = new System.Windows.Threading.DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(1)
        };
        _uiTimer.Tick += UiTimer_Tick;
        _uiTimer.Start();

        await _vm.AguardarRespostaAsync();
        _uiTimer?.Stop();
        Close();
    }

    private void UiTimer_Tick(object? sender, EventArgs e)
    {
        var restantes = _vm.SegundosRestantes;
        PbContagem.Value = restantes;
        TxtSegundos.Text = $"{restantes}s";
    }

    private void BtnSim_Click(object sender, System.Windows.RoutedEventArgs e)
    {
        Dictionary<string, string>? payload = null;
        if (_vm.Kind == "PROMPT_FIM_JORNADA")
            payload = new Dictionary<string, string> { ["atividade"] = TxtAtividade.Text };

        _vm.Responder("SIM", payload);
    }

    private void BtnNao_Click(object sender, System.Windows.RoutedEventArgs e)
        => _vm.Responder("NAO");

    public Task<DialogResponse> AguardarRespostaAsync() => _vm.AguardarRespostaAsync();

    private static string FormatarMensagem(string kind) => kind switch
    {
        "CONFIRM_INICIO_ANTECIPADO" => "Deseja registrar entrada antecipada?",
        "CONFIRM_RETORNO_FORA_JANELA" => "Você retornou fora da janela configurada. Confirmar retorno?",
        "PROMPT_FIM_JORNADA" => "Informe a atividade realizada para encerrar a jornada:",
        "PROMPT_ATIVIDADE" => "Informe a atividade realizada:",
        _ => kind
    };
}
