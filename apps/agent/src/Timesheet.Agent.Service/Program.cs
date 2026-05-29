using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Serilog;
using Serilog.Formatting.Compact;
using Timesheet.Agent.Infra.Db;
using Timesheet.Agent.Infra.Http;
using Timesheet.Agent.Ipc;
using Timesheet.Agent.Service.Input;
using Timesheet.Agent.Service.Journey;
using Timesheet.Agent.Service.Sync;

// ── Serilog: JSON rotativo com redact de campos sensíveis ──────────────────
var logPath = Path.Combine(
    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
    "TimesheetAgent", "logs", "agent-.jsonl");

Log.Logger = new LoggerConfiguration()
    .Enrich.FromLogContext()
    .Destructure.ByTransforming<object>(v => v) // identidade — filtro feito abaixo
    .WriteTo.File(
        new CompactJsonFormatter(),
        logPath,
        rollingInterval: RollingInterval.Day,
        fileSizeLimitBytes: 5 * 1024 * 1024,
        retainedFileCountLimit: 20,
        rollOnFileSizeLimit: true)
    .CreateLogger();

// Campos sensíveis NÃO devem aparecer nos logs: jwt_access_token, jwt_refresh_token, senha.
// A camada HTTP não loga esses campos; qualquer log de config deve omiti-los.

var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddWindowsService(opts =>
{
    opts.ServiceName = "TimesheetAgent";
});

builder.Services.AddSerilog();

// ── Configuração ──────────────────────────────────────────────────────────
var dbPath = Path.Combine(
    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
    "TimesheetAgent", "agent.db");

var backendBaseUrl = builder.Configuration["BackendBaseUrl"] ?? "http://127.0.0.1:8765";

// ── Infra ─────────────────────────────────────────────────────────────────
builder.Services.AddAgentInfra(dbPath);
builder.Services.AddAgentHttp(backendBaseUrl);

// ── IPC ───────────────────────────────────────────────────────────────────
builder.Services.AddSingleton<DialogCorrelator>();
builder.Services.AddSingleton<IDuplexChannel, NamedPipeChannel>();
builder.Services.AddSingleton<IpcServer>();

// ── Input (Win32) ─────────────────────────────────────────────────────────
#pragma warning disable CA1416 // Windows-only — agente só roda em Windows
builder.Services.AddSingleton<ILastInputProvider, Win32LastInputProvider>();
builder.Services.AddSingleton<ISessionMonitor, WindowsSessionMonitor>();
#pragma warning restore CA1416

// ── BackgroundServices ────────────────────────────────────────────────────
builder.Services.AddHostedService<SyncHostedService>();
builder.Services.AddHostedService<JourneyHostedService>();

var host = builder.Build();

// ── Migrate DB on startup ─────────────────────────────────────────────────
using (var scope = host.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AgentDbContext>();
    await db.Database.MigrateAsync();
}

// ── Flush Serilog on shutdown ─────────────────────────────────────────────
var lifetime = host.Services.GetRequiredService<IHostApplicationLifetime>();
lifetime.ApplicationStopping.Register(() => Log.CloseAndFlush());

await host.RunAsync();
