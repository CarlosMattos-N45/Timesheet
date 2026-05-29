using System.Windows.Forms;

namespace Timesheet.Agent.Ui;

public sealed class TrayIcon : IDisposable
{
    private readonly NotifyIcon _notifyIcon;
    private readonly Action _onOpenWeb;
    private readonly Action _onExit;

    public TrayIcon(Action onOpenWeb, Action onExit)
    {
        _onOpenWeb = onOpenWeb;
        _onExit = onExit;

        _notifyIcon = new NotifyIcon
        {
            Text = "Timesheet Terceiros",
            Visible = false,
            Icon = System.Drawing.SystemIcons.Application,
        };

        var menu = new ContextMenuStrip();
        menu.Items.Add("Abrir Timesheet", null, (_, _) => _onOpenWeb());
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Sair", null, (_, _) => _onExit());

        _notifyIcon.ContextMenuStrip = menu;
        _notifyIcon.DoubleClick += (_, _) => _onOpenWeb();
    }

    public void Show() => _notifyIcon.Visible = true;

    public void Hide() => _notifyIcon.Visible = false;

    /// <summary>Atualiza o tooltip do tray com a contagem de pendentes.</summary>
    public void SetBadge(int pendentesCount)
    {
        _notifyIcon.Text = pendentesCount > 0
            ? $"Timesheet Terceiros — {pendentesCount} pendente(s)"
            : "Timesheet Terceiros";
    }

    /// <summary>Exibe uma notificação balloon nativa por ~durationMs milissegundos.</summary>
    public void ShowBalloon(string title, string body, int durationMs = 10000)
        => _notifyIcon.ShowBalloonTip(durationMs, title, body, ToolTipIcon.Info);

    public void Dispose()
    {
        _notifyIcon.Visible = false;
        _notifyIcon.Dispose();
    }
}
