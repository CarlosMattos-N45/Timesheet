# Timesheet Agent

Agente Desktop do TimeSheet Terceiros: Windows Service + UI WPF/tray em .NET 8.

## Pré-requisitos

- .NET 8 SDK (8.0.0+)
- Windows 10/11

## Comandos

### Build

```bash
cd apps/agent
dotnet build Timesheet.Agent.sln
```

### Testes

```bash
cd apps/agent
dotnet test Timesheet.Agent.sln
```

### Format (verificação)

```bash
cd apps/agent
dotnet format Timesheet.Agent.sln --verify-no-changes
```

### Abrir no Visual Studio / Rider

Abrir o arquivo `apps/agent/Timesheet.Agent.sln`.

## Estrutura

```
apps/agent/
  Timesheet.Agent.sln
  global.json
  Directory.Build.props
  .editorconfig
  src/
    Timesheet.Agent.Domain/        # Domínio portável (net8.0)
    Timesheet.Agent.Infra.Db/      # Persistência SQLite (net8.0)
    Timesheet.Agent.Infra.Http/    # Cliente HTTP backend (net8.0)
    Timesheet.Agent.Ipc/           # Named pipes IPC (net8.0-windows)
    Timesheet.Agent.Service/       # Windows Service host (net8.0-windows)
    Timesheet.Agent.Ui/            # WPF + tray UI (net8.0-windows)
    Timesheet.Agent.Tests/         # Testes xUnit (net8.0-windows)
```
