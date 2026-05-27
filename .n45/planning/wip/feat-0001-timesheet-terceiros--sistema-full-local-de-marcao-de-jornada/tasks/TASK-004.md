---
checkpoint: null
complexity: M
created_at: "2026-05-27 14:12:29"
criteria:
    - done: false
      test: cd apps/agent && dotnet build Timesheet.Agent.sln
      text: dotnet build da solucao compila os 7 projetos sem erros
    - done: false
      test: cd apps/agent && dotnet test Timesheet.Agent.sln
      text: dotnet test executa SmokeTests e retorna 1 passed
    - done: false
      test: grep -E 'Microsoft.NET.Sdk.Worker' apps/agent/src/Timesheet.Agent.Service/Timesheet.Agent.Service.csproj
      text: Service csproj usa SDK Microsoft.NET.Sdk.Worker com TargetFramework net8.0-windows
    - done: false
      test: grep -E 'UseWPF.*true' apps/agent/src/Timesheet.Agent.Ui/Timesheet.Agent.Ui.csproj
      text: Ui csproj habilita UseWPF=true e UseWindowsForms=true
    - done: false
      test: grep -E 'net8.0</TargetFramework' apps/agent/src/Timesheet.Agent.Domain/Timesheet.Agent.Domain.csproj
      text: Domain csproj usa TargetFramework net8.0 portavel sem deps Windows-only
    - done: false
      test: grep -E 'TreatWarningsAsErrors.*true' apps/agent/Directory.Build.props
      text: Directory.Build.props impoe Nullable enable e TreatWarningsAsErrors true
    - done: false
      test: grep -E '"version".*"8' apps/agent/global.json
      text: global.json fixa SDK .NET 8
deps:
    - TASK-001
id: TASK-004
linter: cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes
n45_version: 0.2.0
persona: backend
phase: Phase 1 — Scaffold Mínimo
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: cd apps/agent && dotnet test Timesheet.Agent.sln
title: Agente .NET 8 solution scaffold em /apps/agent com 6 projetos + xUnit
updated_at: "2026-05-27 14:12:29"
---
## Contexto

Agente Desktop do TimeSheet Terceiros: aplicação Windows-native em .NET 8 (LTS) composta por um Windows Service (`Timesheet.Agent.Service`) e uma UI WPF + tray (`Timesheet.Agent.Ui`) que se comunicam via named pipes IPC. O agente coleta automaticamente as 4 marcações diárias, sincroniza com o Backend (`/apps/api`) via HTTP local, e mostra diálogos modais ao usuário.

Phase 1 entrega o scaffold da solução: `Timesheet.Agent.sln` com **6 projetos vazios** (compilam, mas sem lógica de domínio), organizados em camadas conforme decidido na Spec §2 "Padrões de código → arquitetura". Cada projeto referencia apenas as deps essenciais (multi-target friendly). Inclui `Timesheet.Agent.Tests` (xUnit + FluentAssertions + Moq) com 1 teste smoke que afirma `1+1==2` para validar o pipeline de testes.

Nenhuma lógica de domínio, IPC, HttpClient ou WPF é implementada — as 6 projetos contêm apenas um arquivo placeholder (ex.: `class AssemblyMarker {}`) com o namespace correto, permitindo que `dotnet build` e `dotnet test` passem.

A solução é gerada na pasta `apps/agent/` (criada em TASK-001). Depende de TASK-001.

## Comportamento Esperado

Após o scaffold, `dotnet restore`, `dotnet build` e `dotnet test` na raiz de `apps/agent/` retornam exit 0. A solução abre no Visual Studio / Rider sem erros. Estrutura de projetos é a definida na Spec §2 (slices de camada).

**Exemplos (entrada / ação → saída / efeito esperado)** — valores reais:

| Entrada / Ação                                                   | Saída / Efeito esperado                                                                                                                                                                                          |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dotnet restore` em `apps/agent/Timesheet.Agent.sln`             | Exit code 0; sem warnings de pacotes faltando                                                                                                                                                                    |
| `dotnet build` em `apps/agent/Timesheet.Agent.sln`               | Build succeeded; 7 projetos compilam (`Service`, `Domain`, `Infra.Http`, `Infra.Db`, `Ipc`, `Ui`, `Tests`)                                                                                                        |
| `dotnet test` em `apps/agent/Timesheet.Agent.sln`                | `Passed: 1`; teste smoke `Smoke_RuntimeCheck_Adds` passa                                                                                                                                                          |
| `dotnet format --verify-no-changes` em `apps/agent/`             | Exit code 0; código segue convenções padrão .NET 8                                                                                                                                                               |
| `ls apps/agent/src/`                                             | Linhas: `Timesheet.Agent.Domain`, `Timesheet.Agent.Infra.Db`, `Timesheet.Agent.Infra.Http`, `Timesheet.Agent.Ipc`, `Timesheet.Agent.Service`, `Timesheet.Agent.Tests`, `Timesheet.Agent.Ui`                       |
| `grep "TargetFramework" apps/agent/src/Timesheet.Agent.Service/Timesheet.Agent.Service.csproj` | Linha contém `<TargetFramework>net8.0-windows</TargetFramework>` (Service host com OutputType Exe)                                                                                                          |
| `grep "TargetFramework" apps/agent/src/Timesheet.Agent.Ui/Timesheet.Agent.Ui.csproj`           | Linha contém `<TargetFramework>net8.0-windows</TargetFramework>` e `<UseWPF>true</UseWPF>`                                                                                                                  |
| `grep "TargetFramework" apps/agent/src/Timesheet.Agent.Domain/Timesheet.Agent.Domain.csproj`   | Linha contém `<TargetFramework>net8.0</TargetFramework>` (Domain é cross-platform-friendly, sem deps Windows-only)                                                                                          |

## TDD

**Testes a escrever antes da implementação:**

`apps/agent/src/Timesheet.Agent.Tests/SmokeTests.cs`:

```csharp
using FluentAssertions;
using Xunit;

namespace Timesheet.Agent.Tests;

public class SmokeTests
{
    [Fact]
    public void Smoke_RuntimeCheck_Adds()
    {
        // Valida pipeline de testes — xUnit + FluentAssertions + Moq disponíveis.
        var result = 1 + 1;
        result.Should().Be(2);
    }

    [Fact]
    public void Smoke_DomainAssembly_IsLoaded()
    {
        // Garante que a referência de projeto Domain está resolvida.
        var asm = typeof(Timesheet.Agent.Domain.AssemblyMarker).Assembly;
        asm.Should().NotBeNull();
        asm.GetName().Name.Should().Be("Timesheet.Agent.Domain");
    }
}
```

**Refatoração:** Nenhuma — testes mínimos para validar pipeline.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                                                                            | Ação      | Descrição                                                                                                                                                                                                                                                |
| ---------------------------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/agent/Timesheet.Agent.sln`                                                   | Criar     | Solution com referências aos 7 projetos abaixo                                                                                                                                                                                                           |
| `apps/agent/global.json`                                                           | Criar     | `{"sdk":{"version":"8.0.0","rollForward":"latestFeature"}}` — fixa .NET 8 SDK                                                                                                                                                                            |
| `apps/agent/Directory.Build.props`                                                 | Criar     | Properties comuns: `<Nullable>enable</Nullable>`, `<ImplicitUsings>enable</ImplicitUsings>`, `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>`, `<LangVersion>latest</LangVersion>`                                                                   |
| `apps/agent/src/Timesheet.Agent.Domain/Timesheet.Agent.Domain.csproj`              | Criar     | SDK `Microsoft.NET.Sdk`. `TargetFramework=net8.0`. Sem refs externas. Sem deps Windows-only — Domain é portável                                                                                                                                          |
| `apps/agent/src/Timesheet.Agent.Domain/AssemblyMarker.cs`                          | Criar     | Classe pública vazia `public class AssemblyMarker {}` no namespace `Timesheet.Agent.Domain` — serve para forçar geração de assembly e ancorar testes                                                                                                     |
| `apps/agent/src/Timesheet.Agent.Infra.Http/Timesheet.Agent.Infra.Http.csproj`      | Criar     | SDK `Microsoft.NET.Sdk`. `TargetFramework=net8.0`. ProjectReference para `Domain`. Sem PackageReference nesta task (Polly e HttpClient ficam em Phase 5)                                                                                                 |
| `apps/agent/src/Timesheet.Agent.Infra.Http/AssemblyMarker.cs`                      | Criar     | `public class AssemblyMarker {}` no namespace `Timesheet.Agent.Infra.Http`                                                                                                                                                                                |
| `apps/agent/src/Timesheet.Agent.Infra.Db/Timesheet.Agent.Infra.Db.csproj`          | Criar     | SDK `Microsoft.NET.Sdk`. `TargetFramework=net8.0`. ProjectReference para `Domain`. Sem deps de EF Core ainda (Phase 5)                                                                                                                                   |
| `apps/agent/src/Timesheet.Agent.Infra.Db/AssemblyMarker.cs`                        | Criar     | `public class AssemblyMarker {}` no namespace `Timesheet.Agent.Infra.Db`                                                                                                                                                                                  |
| `apps/agent/src/Timesheet.Agent.Ipc/Timesheet.Agent.Ipc.csproj`                    | Criar     | SDK `Microsoft.NET.Sdk`. `TargetFramework=net8.0-windows` (named pipes seguros usam ACL Windows). ProjectReference para `Domain`                                                                                                                          |
| `apps/agent/src/Timesheet.Agent.Ipc/AssemblyMarker.cs`                             | Criar     | `public class AssemblyMarker {}` no namespace `Timesheet.Agent.Ipc`                                                                                                                                                                                       |
| `apps/agent/src/Timesheet.Agent.Service/Timesheet.Agent.Service.csproj`            | Criar     | SDK `Microsoft.NET.Sdk.Worker`. `TargetFramework=net8.0-windows`. `OutputType=Exe`. PackageReference para `Microsoft.Extensions.Hosting==8.0.*`, `Microsoft.Extensions.Hosting.WindowsServices==8.0.*`. ProjectReferences: `Domain`, `Infra.Http`, `Infra.Db`, `Ipc` |
| `apps/agent/src/Timesheet.Agent.Service/Program.cs`                                | Criar     | Hosting genérico mínimo: `Host.CreateApplicationBuilder(args).UseWindowsService(opts => opts.ServiceName = "TimesheetAgent").Build().Run()`. **Sem BackgroundService ainda** — apenas valida que o host inicializa                                       |
| `apps/agent/src/Timesheet.Agent.Service/appsettings.json`                          | Criar     | `{"Logging":{"LogLevel":{"Default":"Information"}},"BackendBaseUrl":"http://127.0.0.1:8765"}`                                                                                                                                                              |
| `apps/agent/src/Timesheet.Agent.Ui/Timesheet.Agent.Ui.csproj`                      | Criar     | SDK `Microsoft.NET.Sdk`. `TargetFramework=net8.0-windows`. `<UseWPF>true</UseWPF>`. `<UseWindowsForms>true</UseWindowsForms>` (para `NotifyIcon` tray). `OutputType=WinExe`. ProjectReferences: `Domain`, `Ipc`                                            |
| `apps/agent/src/Timesheet.Agent.Ui/App.xaml`                                       | Criar     | WPF Application shell mínima                                                                                                                                                                                                                              |
| `apps/agent/src/Timesheet.Agent.Ui/App.xaml.cs`                                    | Criar     | `public partial class App : Application {}` — sem startup window ainda                                                                                                                                                                                    |
| `apps/agent/src/Timesheet.Agent.Tests/Timesheet.Agent.Tests.csproj`                | Criar     | SDK `Microsoft.NET.Sdk`. `TargetFramework=net8.0-windows`. PackageReferences: `Microsoft.NET.Test.Sdk==17.11.*`, `xunit==2.9.*`, `xunit.runner.visualstudio==2.8.*`, `FluentAssertions==6.12.*`, `Moq==4.20.*`. ProjectReferences: `Domain`, `Infra.Http`, `Infra.Db`, `Ipc` |
| `apps/agent/src/Timesheet.Agent.Tests/SmokeTests.cs`                               | Criar     | Conforme TDD acima                                                                                                                                                                                                                                        |
| `apps/agent/.editorconfig`                                                         | Criar     | Convenções .NET padrão: indent_size 4 para `.cs`, severities apropriadas                                                                                                                                                                                  |
| `apps/agent/README.md`                                                             | Criar     | Como buildar (`dotnet build`), testar (`dotnet test`), abrir solução                                                                                                                                                                                      |
| `Makefile` (raiz)                                                                  | Modificar | Adicionar targets `agent-build` (dotnet build), `agent-test` (dotnet test), `agent-format` (dotnet format). Atualizar `help`                                                                                                                              |

### Detalhamento Técnico

1. **Decisões de TargetFramework:**
   - `Domain`, `Infra.Http`, `Infra.Db` → `net8.0` (portáveis, sem deps Windows-only — facilita testes de domínio em CI Linux)
   - `Ipc` → `net8.0-windows` (named pipes com ACL precisam de `System.IO.Pipes.AccessControl` Windows-only)
   - `Service`, `Ui`, `Tests` → `net8.0-windows` (Service usa `UseWindowsService`; Ui usa WPF + NotifyIcon; Tests precisa instanciar IPC nos testes futuros)

2. **`Timesheet.Agent.sln`** layout — usar `dotnet new sln` + `dotnet sln add` para gerar (ou criar manualmente seguindo o formato). Garantir que **todos os 7 csproj** estão referenciados.

3. **`Directory.Build.props`** centraliza propriedades comuns para todos os projetos do `apps/agent/`. Reduz duplicação e impõe `Nullable enable` + `TreatWarningsAsErrors` desde o início:

   ```xml
   <Project>
     <PropertyGroup>
       <Nullable>enable</Nullable>
       <ImplicitUsings>enable</ImplicitUsings>
       <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
       <LangVersion>latest</LangVersion>
       <RootNamespace>$(MSBuildProjectName)</RootNamespace>
     </PropertyGroup>
   </Project>
   ```

4. **`Service/Program.cs`** (chave) — apenas valida que o host inicializa. **Sem BackgroundService** — esse virá em Phase 5:

   ```csharp
   using Microsoft.Extensions.Hosting;

   var builder = Host.CreateApplicationBuilder(args);
   builder.Services.AddWindowsService(opts =>
   {
       opts.ServiceName = "TimesheetAgent";
   });
   var host = builder.Build();
   host.Run();
   ```

5. **`Ui/App.xaml`** (mínimo):

   ```xml
   <Application x:Class="Timesheet.Agent.Ui.App"
                xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
       <Application.Resources>
       </Application.Resources>
   </Application>
   ```

   **Sem `StartupUri`** — Phase 5 define janela de wizard / dialogs. O app **compila e empacota**, mas não tem janela default (intencional).

6. **AssemblyMarker** — padrão consagrado: cada projeto vazio recebe uma classe pública vazia no namespace raiz para que o compilador gere o assembly e os testes possam referenciar tipos. Sem essa classe, projetos vazios geram um assembly válido mas sem `Type` exportado, dificultando smoke tests.

7. **Makefile (adições):**

   ```makefile
   .PHONY: agent-build agent-test agent-format

   AGENT_DIR := apps/agent

   agent-build:
   	cd $(AGENT_DIR) && dotnet build Timesheet.Agent.sln -c Debug

   agent-test:
   	cd $(AGENT_DIR) && dotnet test Timesheet.Agent.sln -c Debug --no-restore

   agent-format:
   	cd $(AGENT_DIR) && dotnet format Timesheet.Agent.sln --verify-no-changes
   ```

8. **Estrutura de pastas** dentro de `apps/agent/src/` segue a Spec literalmente:

   ```
   apps/agent/
     Timesheet.Agent.sln
     global.json
     Directory.Build.props
     .editorconfig
     README.md
     src/
       Timesheet.Agent.Domain/
       Timesheet.Agent.Infra.Db/
       Timesheet.Agent.Infra.Http/
       Timesheet.Agent.Ipc/
       Timesheet.Agent.Service/
       Timesheet.Agent.Tests/
       Timesheet.Agent.Ui/
   ```

**Refatoração:** Nenhuma — estrutura inicial, sem código a simplificar.
