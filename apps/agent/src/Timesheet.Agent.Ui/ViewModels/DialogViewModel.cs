using Timesheet.Agent.Ipc;

namespace Timesheet.Agent.Ui.ViewModels;

public sealed class DialogViewModel
{
    private readonly TaskCompletionSource<DialogResponse> _tcs = new();
    private readonly int _segundosTotal;
    private int _segundosRestantes;
    private System.Threading.Timer? _timer;

    public string Id { get; }
    public string Kind { get; }

    public int SegundosRestantes
    {
        get => _segundosRestantes;
        private set => _segundosRestantes = value;
    }

    public DialogViewModel(string id, string kind, int segundos = 60)
    {
        Id = id;
        Kind = kind;
        _segundosTotal = segundos;
        _segundosRestantes = segundos;
    }

    /// <summary>
    /// Aguarda a resposta do usuário ou o timeout.
    /// Inicia o timer de contagem regressiva automaticamente.
    /// </summary>
    public Task<DialogResponse> AguardarRespostaAsync()
    {
        _timer = new System.Threading.Timer(Tick, null, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(1));
        return _tcs.Task;
    }

    /// <summary>
    /// Registra a resposta do usuário e cancela o timer.
    /// </summary>
    public void Responder(string answer, Dictionary<string, string>? payload = null)
    {
        _timer?.Dispose();
        _tcs.TrySetResult(new DialogResponse(Id, answer, payload));
    }

    private void Tick(object? state)
    {
        _segundosRestantes--;
        if (_segundosRestantes <= 0)
        {
            _timer?.Dispose();
            _tcs.TrySetResult(new DialogResponse(Id, "TIMEOUT"));
        }
    }
}
