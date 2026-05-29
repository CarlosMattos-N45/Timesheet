using System.Diagnostics;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Timesheet.Agent.Infra.Db;
using Timesheet.Agent.Infra.Http;
using Timesheet.Agent.Ipc;
using Timesheet.Agent.Ui.Common;
using Timesheet.Agent.Ui.Views;
// Qualificar explicitamente para evitar ambiguidade com System.Windows.Forms.Application
using WpfApp = System.Windows.Application;
using WpfExitEventArgs = System.Windows.ExitEventArgs;
using WpfShutdownMode = System.Windows.ShutdownMode;
using WpfStartupEventArgs = System.Windows.StartupEventArgs;

namespace Timesheet.Agent.Ui;

public partial class App : WpfApp
{
    private TrayIcon? _tray;
    private IpcClient? _ipcClient;

    protected override async void OnStartup(WpfStartupEventArgs e)
    {
        base.OnStartup(e);

        // Infra: DI simples para este processo
        var services = new ServiceCollection();
        services.AddDbContext<AgentDbContext>(o =>
            o.UseSqlite("Data Source=timesheet-agent.db"));
        services.AddScoped<ConfiguracaoLocalRepository>();
        services.AddHttpClient<IBackendClient, BackendClient>(c =>
            c.BaseAddress = new Uri("http://127.0.0.1:8765"));
        var sp = services.BuildServiceProvider();

        var repo = sp.GetRequiredService<ConfiguracaoLocalRepository>();
        var backend = sp.GetRequiredService<IBackendClient>();

        // Verifica se o cadastro já foi realizado
        var cfg = await repo.GetAsync();
        bool cadastroFeito = cfg?.JwtAccessToken != null;

        if (!cadastroFeito)
        {
            var wizard = new WizardWindow();
            var ok = wizard.ShowDialog();
            if (ok != true || wizard.Result is null)
            {
                Shutdown();
                return;
            }

            try
            {
                await backend.CreateTerceiroAsync(wizard.Result);
                var auth = await backend.LoginAsync(wizard.Result.EmailContato, wizard.Result.Senha);

                var novaCfg = new Timesheet.Agent.Domain.ConfiguracaoLocal
                {
                    BackendBaseUrl = "http://127.0.0.1:8765",
                    JwtAccessToken = auth.AccessToken,
                    JwtRefreshToken = auth.RefreshToken,
                    ExpiraEm = DateTimeOffset.UtcNow.AddSeconds(auth.ExpiresIn).ToString("o"),
                };
                await repo.UpsertAsync(novaCfg);
            }
            catch (AuthException ex)
            {
                System.Windows.MessageBox.Show($"Erro no cadastro: {ex.Message}", "Erro",
                    System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
                Shutdown();
                return;
            }
        }

        // Ativa tray
        _tray = new TrayIcon(
            onOpenWeb: AbrirBrowser,
            onExit: () => Shutdown());
        _tray.Show();

        // Inicia IPC em background
        _ = Task.Run(async () =>
        {
            try
            {
                var channel = await NamedPipeChannel.CreateClientAsync();
                _ipcClient = new IpcClient(channel);
                _ipcClient.OnMessage += OnIpcMessage;
                await _ipcClient.StartReadLoopAsync();
            }
            catch
            {
                // IPC indisponível — UI continua sem mensagens do Service
            }
        });

        // Toast de saudação
        var hora = DateTime.Now.Hour;
        _tray.ShowBalloon("Timesheet Terceiros", Saudacao.Para(hora));

        AbrirBrowser();

        ShutdownMode = WpfShutdownMode.OnExplicitShutdown;
    }

    private void OnIpcMessage(IpcMessage msg)
    {
        Dispatcher.Invoke(() =>
        {
            switch (msg)
            {
                case DialogRequest req:
                    var win = new DialogWindow(req);
                    win.Loaded += async (_, _) =>
                    {
                        var resp = await win.AguardarRespostaAsync();
                        if (_ipcClient is not null)
                            await _ipcClient.SendAsync(resp);
                    };
                    win.Show();
                    break;

                case ToastMessage toast:
                    _tray?.ShowBalloon(toast.Title, toast.Body, toast.DurationS * 1000);
                    break;

                case StatusPush push:
                    _tray?.SetBadge(push.PendentesCount);
                    break;
            }
        });
    }

    private static void AbrirBrowser()
        => Process.Start(new ProcessStartInfo("http://127.0.0.1:8765/login") { UseShellExecute = true });

    protected override void OnExit(WpfExitEventArgs e)
    {
        _tray?.Dispose();
        base.OnExit(e);
    }
}
