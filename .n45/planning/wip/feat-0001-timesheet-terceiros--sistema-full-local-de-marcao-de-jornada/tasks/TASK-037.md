---
checkpoint: null
complexity: M
created_at: "2026-05-29 11:46:46"
criteria:
    - done: false
      test: cd apps/agent && dotnet publish src/Timesheet.Agent.Service -c Release -r win-x64 --self-contained -p:PublishSingleFile=true -o dist/service
      text: dotnet publish do Service gera apps/agent/dist/service/TimesheetAgent.exe self-contained single-file win-x64
    - done: false
      test: cd apps/agent && dotnet publish src/Timesheet.Agent.Ui -c Release -r win-x64 --self-contained -p:PublishSingleFile=true -o dist/ui
      text: dotnet publish da UI gera apps/agent/dist/ui/TimesheetAgentUi.exe self-contained single-file win-x64
    - done: false
      test: cd apps/agent && dotnet test Timesheet.Agent.sln -c Release --no-restore
      text: Solution compila em Release com os novos RuntimeIdentifier/AssemblyName e todos os testes existentes continuam passando
    - done: false
      text: publish-agent.ps1 falha com exit !=0 se algum dos 2 .exe nao for produzido
deps:
    - TASK-036
id: TASK-037
linter: cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes
n45_version: 0.2.0
persona: devops
phase: Phase 6 — Empacotamento Windows (PyInstaller + WiX MSI)
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: cd apps/agent && dotnet test Timesheet.Agent.sln -c Release --no-restore
title: Publish .NET self-contained single-file do Agente (Service TimesheetAgent + UI)
updated_at: "2026-05-29 11:46:46"
---
## Contexto

Segunda task da Phase 6 (Empacotamento Windows). O Agente .NET (`apps/agent`) hoje só compila/testa em modo `Debug` via Makefile (`agent-build` = `dotnet build ... -c Debug`). Para o MSI (TASK-038) instalar o Agente sem exigir o .NET Runtime na máquina do Terceiro (Spec §2: ".NET 8 runtime embarcado"; §10: "Electron pesaria 300+ MB" — manter footprint baixo), precisamos publicar os dois executáveis em **self-contained single-file**, prontos para o WiX referenciar.

Estado atual relevante (fatos do código):
- A solution `apps/agent/Timesheet.Agent.sln` tem 6 projetos + testes. Dois são **entrypoints executáveis**:
  - `Timesheet.Agent.Service` — Windows Service `TimesheetAgent`. `Program.cs` usa `Host.CreateApplicationBuilder` + `AddWindowsService(opts => opts.ServiceName = "TimesheetAgent")`, roda `db.Database.MigrateAsync()` no startup, banco em `%LOCALAPPDATA%\TimesheetAgent\agent.db`, lê `BackendBaseUrl` da config (default `http://127.0.0.1:8765`), Serilog JSON rotativo em `%LOCALAPPDATA%\TimesheetAgent\logs\agent-.jsonl`.
  - `Timesheet.Agent.Ui` — processo WPF (tray + wizard + diálogos) que roda na sessão do usuário. `UseWPF=true` + `UseWindowsForms=true` (NotifyIcon).
- O Service e a UI comunicam por named pipe `\\.\pipe\TimesheetAgent` (TASK-032). O Service NÃO abre UI; a UI é iniciada na sessão do usuário (logon) — o MSI (TASK-038) configura o autostart da UI via Run key / Startup, e o Service como Windows Service.
- Não há `RuntimeIdentifier`, `PublishSingleFile` nem perfis de publish definidos nos `.csproj` ainda.

Esta task **não** muda regra de negócio nem UI — apenas adiciona os parâmetros de publish e um script que gera os dois executáveis em `apps/agent/dist/`.

## Comportamento Esperado

O alvo verificável é o **resultado do publish**: dois executáveis self-contained, win-x64, single-file, que existem e iniciam. Não há lógica testável nova (é configuração de build/publish — persona devops); a verificação é por comando (`dotnet publish` + presença do `.exe` + `--version`/start sem crash imediato).

**Exemplos (entrada / ação → saída esperada)** — valores reais:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `dotnet publish src/Timesheet.Agent.Service -c Release -r win-x64 --self-contained -p:PublishSingleFile=true` | gera `apps/agent/dist/service/TimesheetAgent.exe` (1 arquivo, sem dependência de .NET instalado) |
| `dotnet publish src/Timesheet.Agent.Ui -c Release -r win-x64 --self-contained -p:PublishSingleFile=true` | gera `apps/agent/dist/ui/TimesheetAgentUi.exe` |
| `dotnet build Timesheet.Agent.sln -c Release` | compila sem erro com os novos `RuntimeIdentifiers`/props |
| `dotnet test Timesheet.Agent.sln -c Release` | todos os testes existentes continuam passando (publish não altera comportamento) |
| Rodar `TimesheetAgent.exe` em máquina **sem** .NET 8 instalado | inicia (self-contained); sem `FileNotFoundException` de runtime |

## O que Implementar

> Persona devops — sem seção TDD. Verificação por `dotnet publish`/`dotnet test` (comandos no critério).

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/agent/src/Timesheet.Agent.Service/Timesheet.Agent.Service.csproj` | Modificar | Adicionar `<RuntimeIdentifier>win-x64</RuntimeIdentifier>`, `<SelfContained>true</SelfContained>`, `<PublishSingleFile>true</PublishSingleFile>`, `<AssemblyName>TimesheetAgent</AssemblyName>`, `<Version>1.0.0</Version>`. Manter `<OutputType>Exe</OutputType>` |
| `apps/agent/src/Timesheet.Agent.Ui/Timesheet.Agent.Ui.csproj` | Modificar | Mesmas props de publish + `<AssemblyName>TimesheetAgentUi</AssemblyName>`, `<Version>1.0.0</Version>`. Manter `UseWPF`/`UseWindowsForms`/`OutputType=WinExe` |
| `apps/agent/Directory.Build.props` | Criar | Centraliza `<RuntimeIdentifiers>win-x64</RuntimeIdentifiers>` e `<TargetFramework>net8.0-windows</TargetFramework>` comuns; evita repetir em cada csproj. Não aplicar `SelfContained` aqui (só nos 2 entrypoints) |
| `apps/agent/scripts/publish-agent.ps1` | Criar | Publica os 2 entrypoints em `apps/agent/dist/service` e `apps/agent/dist/ui`; falha (exit ≠ 0) se algum `.exe` não for produzido |

### Detalhamento Técnico

1. **Service `.csproj`** — props de publish:
   ```xml
   <PropertyGroup>
     <OutputType>Exe</OutputType>
     <TargetFramework>net8.0-windows</TargetFramework>
     <Nullable>enable</Nullable>
     <AssemblyName>TimesheetAgent</AssemblyName>
     <Version>1.0.0</Version>
     <RuntimeIdentifier>win-x64</RuntimeIdentifier>
     <SelfContained>true</SelfContained>
     <PublishSingleFile>true</PublishSingleFile>
     <IncludeNativeLibrariesForSelfExtract>true</IncludeNativeLibrariesForSelfExtract>
   </PropertyGroup>
   ```
   Preservar `PackageReference` existentes (Serilog, EF Core, Polly, etc). EF Core SQLite traz `e_sqlite3` nativo — `IncludeNativeLibrariesForSelfExtract=true` garante extração no single-file.

2. **UI `.csproj`** — mesmas props de publish; manter `<OutputType>WinExe</OutputType>`, `<UseWPF>true</UseWPF>`, `<UseWindowsForms>true</UseWindowsForms>`, `<AssemblyName>TimesheetAgentUi</AssemblyName>`.

3. **`Directory.Build.props`** (na raiz de `apps/agent/`) — só o que é comum a todos os projetos:
   ```xml
   <Project>
     <PropertyGroup>
       <RuntimeIdentifiers>win-x64</RuntimeIdentifiers>
       <Nullable>enable</Nullable>
       <ImplicitUsings>enable</ImplicitUsings>
     </PropertyGroup>
   </Project>
   ```
   Não declarar `SelfContained`/`PublishSingleFile` aqui (não pode vazar para a lib de testes nem para as bibliotecas).

4. **`publish-agent.ps1`**:
   ```powershell
   $ErrorActionPreference = "Stop"
   $root = Split-Path $PSScriptRoot -Parent
   dotnet publish "$root/src/Timesheet.Agent.Service" -c Release -r win-x64 --self-contained -p:PublishSingleFile=true -o "$root/dist/service"
   dotnet publish "$root/src/Timesheet.Agent.Ui" -c Release -r win-x64 --self-contained -p:PublishSingleFile=true -o "$root/dist/ui"
   if (-not (Test-Path "$root/dist/service/TimesheetAgent.exe")) { Write-Error "TimesheetAgent.exe nao gerado"; exit 1 }
   if (-not (Test-Path "$root/dist/ui/TimesheetAgentUi.exe")) { Write-Error "TimesheetAgentUi.exe nao gerado"; exit 1 }
   Write-Host "[publish-agent] OK: service + ui"
   ```

5. **`dist/` no `.gitignore`** — `apps/agent/dist/` é artefato de build; garantir que está coberto pelo `.gitignore` raiz (já ignora `bin`/`obj`; adicionar `apps/agent/dist/` se ainda não coberto). Verificar antes via `git check-ignore`.

> **Nota de fronteira (produzido para TASK-038):** o WiX referencia `apps/agent/dist/service/TimesheetAgent.exe` (instalado como Windows Service `TimesheetAgent`, conta `LocalSystem` ou `NetworkService`, start `auto`) e `apps/agent/dist/ui/TimesheetAgentUi.exe` (instalado em `Program Files` e registrado para autostart na sessão do usuário via Run key `HKCU\...\Run` ou atalho em Startup). Os dois são self-contained — o MSI **não** precisa instalar o .NET Runtime.

**Contrato com camadas adjacentes:**

```
Produz para: TASK-038 (WiX MSI)
  - apps/agent/dist/service/TimesheetAgent.exe  → Windows Service "TimesheetAgent" (start auto)
  - apps/agent/dist/ui/TimesheetAgentUi.exe     → processo de sessão de usuário (autostart no logon)
Consome de: nada novo — só os projetos existentes da solution (Phase 5)
Invariante: publish self-contained → MSI não depende de .NET 8 pré-instalado
```
