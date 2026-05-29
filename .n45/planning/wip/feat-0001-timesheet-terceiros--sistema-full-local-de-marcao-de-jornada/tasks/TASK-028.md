---
checkpoint: null
complexity: G
created_at: "2026-05-29 09:23:56"
criteria:
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~ClockTests
      text: FakeClock retorna instante fixo e SystemClock.NowLocal usa offset -03:00
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Constants_match_backend_contract
      text: Constantes MarcacaoTipo/OrigemMarcacao casam com o CHECK do banco e o Literal do backend (INICIO_JORNADA, AGENTE_AUTOMATICO, etc)
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~GetPendentes_returns_only_unsynced_ordered_by_criadoEm
      text: MarcacaoLocalRepository.GetPendentesOrdenadasAsync retorna apenas Sincronizada=false ordenadas por CriadoEm asc
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~MarcarSincronizada_removes_from_pendentes
      text: MarcarSincronizadaAsync remove a marcacao da fila de pendentes
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Upsert_twice_keeps_single_row
      text: ConfiguracaoLocalRepository.UpsertAsync chamado 2x mantem 1 unica linha (singleton Id=1)
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Serialize_toast_is_newline_terminated_json
      text: IpcSerializer.Serialize(ToastMessage) produz JSON terminado em newline contendo "type":"TOAST"
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Deserialize_dialog_response_roundtrips_answer
      text: IpcSerializer.Deserialize de DIALOG_RESPONSE retorna DialogResponse com Answer=SIM
    - done: true
      text: Solution compila e dotnet test passa (todos os testes verdes)
    - done: true
      text: Cobertura Domain+Infra >= 70%
deps: []
id: TASK-028
linter: cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes
n45_version: 0.2.0
persona: backend
phase: Phase 5 — Agente Desktop
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: true
    red: true
    refactor: true
tests: cd apps/agent && dotnet test Timesheet.Agent.sln -c Debug
title: 'Fundação Agente: IClock + constantes de domínio, 3 repositórios concretos, contrato IPC + serializer, AddAgentInfra (DI)'
updated_at: "2026-05-29 09:49:33"
---
## Contexto

O Agente Desktop .NET 8 (`/apps/agent`) já tem o scaffold pronto: solution com 6 projetos (`Timesheet.Agent.Domain`, `Timesheet.Agent.Infra.Db`, `Timesheet.Agent.Infra.Http`, `Timesheet.Agent.Ipc`, `Timesheet.Agent.Ui`, `Timesheet.Agent.Service`) + `Timesheet.Agent.Tests` (xUnit + FluentAssertions + Moq). O `Domain` já contém as POCOs `MarcacaoLocal`, `EstadoJornadaAtual`, `ConfiguracaoLocal`; o `Infra.Db` já tem `AgentDbContext` (DbSets `MarcacoesLocais`, `EstadoJornadaAtual`, `ConfiguracaoLocal`), `AgentDbContextFactory` e a migration `Initial`.

Esta é a **Fundação do Agente** — task `G` sequencial da qual todas as outras tasks da Phase 5 dependem. Ela cria o transversal compartilhado e **decide explicitamente os padrões arquiteturais** do Agente inteiro, para que nenhuma task de feature recrie helper próprio ou escolha padrão divergente:

1. **Abstração de tempo** (`IClock`) — toda regra de jornada (janelas de tolerância ±30min, inatividade) precisa de relógio injetável para ser testável sem `DateTime.Now` real. Fuso fixo `America/Sao_Paulo` (constraint da Spec).
2. **Padrão de repository** — classe concreta sobre `AgentDbContext`, injetada via construtor (DI manual no Service host). Nunca repository estático nem Active Record na POCO.
3. **Padrão de DI** — `Microsoft.Extensions.DependencyInjection` (já transitivo via `Microsoft.Extensions.Hosting` no Service). Registro centralizado num método de extensão `AddAgentInfra`.
4. **Contrato IPC** (tipos de mensagem named-pipe) como records compartilhados em `Timesheet.Agent.Ipc`, com serialização JSON newline-delimited.
5. **Enums/constantes de domínio** (`MarcacaoTipo`, `OrigemMarcacao`, `EstadoJornada`) — hoje são strings soltas espalhadas; centralizar como `static class` de constantes para evitar typo divergente entre state machine, repositório e HTTP client.

As tasks subsequentes (state machine, HTTP sync, detectores Win32, IPC server, Service host, WPF) consomem esta fundação e **nunca** recriam relógio, repositório, contrato IPC ou constante de tipo.

## Comportamento Esperado

O `Domain` ganha abstração de tempo e constantes; o `Infra.Db` ganha 3 repositórios concretos; o `Ipc` ganha os records de contrato + serializer; um método `AddAgentInfra(IServiceCollection, string dbPath)` registra tudo. Tudo compila e os testes passam.

**Exemplos (entrada → saída esperada)** — valores reais, base direta das assertions:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `new SystemClock().NowUtc` (após `t0`) | `DateTimeOffset` em UTC ≥ `t0`; `Kind`/`Offset` == zero offset |
| `new SystemClock().NowLocal` | `DateTimeOffset` no fuso `America/Sao_Paulo` (offset `-03:00`) |
| `FakeClock(fixed: 2026-05-27T12:00:00Z).NowUtc` | `2026-05-27T12:00:00+00:00` (exato, controlável em teste) |
| `repo.EnqueueAsync(marcacao)` depois `repo.GetPendentesOrdenadasAsync()` | retorna a marcação com `Sincronizada=false`, ordenada por `CriadoEm` asc |
| `repo.MarcarSincronizadaAsync(id)` | a marcação fica `Sincronizada=true`; `GetPendentesOrdenadasAsync()` não a retorna mais |
| `configRepo.GetAsync()` quando tabela vazia | `null` |
| `configRepo.UpsertAsync(cfg)` 2× com mesmos dados | exatamente 1 linha em `ConfiguracaoLocal` (singleton Id=1) |
| `estadoRepo.GetAsync()` após `UpsertAsync(estado EM_JORNADA)` | `Status == "EM_JORNADA"`, `Id == 1` |
| `IpcSerializer.Serialize(new ToastMessage("Bom dia","corpo",10))` | string JSON terminada em `\n` contendo `"type":"TOAST"` |
| `IpcSerializer.Deserialize<IpcMessage>(json)` de um `DIALOG_RESPONSE` | record `DialogResponse` com `Answer=="SIM"` |
| `MarcacaoTipo.InicioJornada` | constante string `"INICIO_JORNADA"` (igual ao CHECK do banco e ao enum do backend) |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (projeto `Timesheet.Agent.Tests`, em `Domain/`, `InfraDb/`, `Ipc/`):

```csharp
// Timesheet.Agent.Tests/Domain/ClockTests.cs
[Fact]
public void FakeClock_returns_fixed_instant()
{
    var clock = new FakeClock(DateTimeOffset.Parse("2026-05-27T12:00:00Z"));
    clock.NowUtc.Should().Be(DateTimeOffset.Parse("2026-05-27T12:00:00+00:00"));
}

[Fact]
public void SystemClock_NowLocal_uses_sao_paulo_offset()
{
    var clock = new SystemClock();
    clock.NowLocal.Offset.Should().Be(TimeSpan.FromHours(-3));
}

[Fact]
public void Constants_match_backend_contract()
{
    MarcacaoTipo.InicioJornada.Should().Be("INICIO_JORNADA");
    MarcacaoTipo.SaidaAlmoco.Should().Be("SAIDA_ALMOCO");
    MarcacaoTipo.RetornoAlmoco.Should().Be("RETORNO_ALMOCO");
    MarcacaoTipo.FimJornada.Should().Be("FIM_JORNADA");
    OrigemMarcacao.AgenteAutomatico.Should().Be("AGENTE_AUTOMATICO");
    OrigemMarcacao.AgenteConfirmado.Should().Be("AGENTE_CONFIRMADO");
}

// Timesheet.Agent.Tests/InfraDb/MarcacaoRepositoryTests.cs  (usar SqliteConnection :memory: + MigrateAsync, igual a AgentDbContextTests existente)
[Fact]
public async Task GetPendentes_returns_only_unsynced_ordered_by_criadoEm()
{
    await _repo.EnqueueAsync(Mk("b", criadoEm: "2026-05-27T13:00:00Z"));
    await _repo.EnqueueAsync(Mk("a", criadoEm: "2026-05-27T12:00:00Z"));
    var pend = await _repo.GetPendentesOrdenadasAsync();
    pend.Select(m => m.Id).Should().Equal("a", "b");
}

[Fact]
public async Task MarcarSincronizada_removes_from_pendentes()
{
    await _repo.EnqueueAsync(Mk("x", criadoEm: "2026-05-27T12:00:00Z"));
    await _repo.MarcarSincronizadaAsync("x");
    (await _repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
}

// Timesheet.Agent.Tests/InfraDb/ConfigRepositoryTests.cs
[Fact]
public async Task Upsert_twice_keeps_single_row()
{
    await _configRepo.UpsertAsync(new ConfiguracaoLocal { BackendBaseUrl = "http://127.0.0.1:8765" });
    await _configRepo.UpsertAsync(new ConfiguracaoLocal { BackendBaseUrl = "http://127.0.0.1:8765" });
    (await _ctx.ConfiguracaoLocal.CountAsync()).Should().Be(1);
}

// Timesheet.Agent.Tests/Ipc/IpcSerializerTests.cs
[Fact]
public void Serialize_toast_is_newline_terminated_json()
{
    var json = IpcSerializer.Serialize(new ToastMessage("Bom dia", "corpo", 10));
    json.Should().EndWith("\n");
    json.Should().Contain("\"type\":\"TOAST\"");
}

[Fact]
public void Deserialize_dialog_response_roundtrips_answer()
{
    var json = "{\"type\":\"DIALOG_RESPONSE\",\"id\":\"abc\",\"answer\":\"SIM\"}\n";
    var msg = IpcSerializer.Deserialize(json);
    msg.Should().BeOfType<DialogResponse>().Which.Answer.Should().Be("SIM");
}
```

**Refatoração:** após green, extrair helper `Mk(...)` de criação de `MarcacaoLocal` para um fixture compartilhado em `Timesheet.Agent.Tests/TestData.cs` se duplicado em ≥2 arquivos de teste; remover duplicação de setup `SqliteConnection :memory:` para uma base `SqliteInMemoryFixture`.

## O que Implementar

Código mínimo para os testes passarem. Sem over-engineering.

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/agent/src/Timesheet.Agent.Domain/IClock.cs` | Criar | Interface `IClock` + `SystemClock` + `FakeClock` (teste usa) + `TimeZoneConstants.SaoPaulo` |
| `apps/agent/src/Timesheet.Agent.Domain/DomainConstants.cs` | Criar | `static class MarcacaoTipo`, `OrigemMarcacao`, `EstadoJornada` com as constantes string |
| `apps/agent/src/Timesheet.Agent.Infra.Db/MarcacaoLocalRepository.cs` | Criar | Repositório concreto: `EnqueueAsync`, `GetPendentesOrdenadasAsync`, `MarcarSincronizadaAsync`, `RegistrarFalhaSyncAsync`, `GetByIdAsync` |
| `apps/agent/src/Timesheet.Agent.Infra.Db/ConfiguracaoLocalRepository.cs` | Criar | `GetAsync` (nullable), `UpsertAsync` (singleton Id=1) |
| `apps/agent/src/Timesheet.Agent.Infra.Db/EstadoJornadaRepository.cs` | Criar | `GetAsync` (nullable), `UpsertAsync` (singleton Id=1) |
| `apps/agent/src/Timesheet.Agent.Infra.Db/ServiceCollectionExtensions.cs` | Criar | `AddAgentInfra(this IServiceCollection, string dbPath)` — registra `AgentDbContext` (UseSqlite), os 3 repos, `IClock→SystemClock` |
| `apps/agent/src/Timesheet.Agent.Ipc/IpcMessages.cs` | Criar | Records do contrato IPC + `JsonPolymorphic` por `type` |
| `apps/agent/src/Timesheet.Agent.Ipc/IpcSerializer.cs` | Criar | `Serialize(IpcMessage)→string\n` e `Deserialize(string)→IpcMessage` |
| `apps/agent/src/Timesheet.Agent.Infra.Db/Timesheet.Agent.Infra.Db.csproj` | Modificar | Adicionar `<PackageReference Include="Microsoft.Extensions.DependencyInjection.Abstractions" Version="8.0.*" />` |
| `apps/agent/src/Timesheet.Agent.Domain/AssemblyMarker.cs` | (manter) | Já existe — não remover (SmokeTests referencia) |

### Detalhamento Técnico

1. **`IClock`** — interface com `DateTimeOffset NowUtc` e `DateTimeOffset NowLocal`. `SystemClock` retorna `DateTimeOffset.UtcNow` e converte para o fuso via `TimeZoneInfo.FindSystemTimeZoneById("America/Sao_Paulo")` (Windows aceita IANA desde .NET 6 via ICU). `FakeClock(DateTimeOffset fixed)` retorna sempre o mesmo instante (campo settable para avançar em testes).

```csharp
namespace Timesheet.Agent.Domain;

public interface IClock
{
    DateTimeOffset NowUtc { get; }
    DateTimeOffset NowLocal { get; }
}

public sealed class SystemClock : IClock
{
    private static readonly TimeZoneInfo Tz =
        TimeZoneInfo.FindSystemTimeZoneById(TimeZoneConstants.SaoPaulo);
    public DateTimeOffset NowUtc => DateTimeOffset.UtcNow;
    public DateTimeOffset NowLocal => TimeZoneInfo.ConvertTime(DateTimeOffset.UtcNow, Tz);
}

public sealed class FakeClock(DateTimeOffset now) : IClock
{
    public DateTimeOffset NowUtc { get; set; } = now.ToUniversalTime();
    public DateTimeOffset NowLocal => TimeZoneInfo.ConvertTime(
        NowUtc, TimeZoneInfo.FindSystemTimeZoneById(TimeZoneConstants.SaoPaulo));
}

public static class TimeZoneConstants { public const string SaoPaulo = "America/Sao_Paulo"; }
```

2. **`DomainConstants`** — constantes string que casam EXATAMENTE com o CHECK do `AgentDbContext` e com os enums `Literal` do backend (`MarcacaoTipo`/`OrigemAgente` em `apps/api/app/modules/marcacoes/schema.py`):

```csharp
public static class MarcacaoTipo
{
    public const string InicioJornada = "INICIO_JORNADA";
    public const string SaidaAlmoco = "SAIDA_ALMOCO";
    public const string RetornoAlmoco = "RETORNO_ALMOCO";
    public const string FimJornada = "FIM_JORNADA";
}
public static class OrigemMarcacao
{
    public const string AgenteAutomatico = "AGENTE_AUTOMATICO";
    public const string AgenteConfirmado = "AGENTE_CONFIRMADO";
}
public static class EstadoJornada
{
    public const string AguardandoInicio = "AGUARDANDO_INICIO";
    public const string EmJornada = "EM_JORNADA";
    public const string EmAlmoco = "EM_ALMOCO";
    public const string AguardandoFim = "AGUARDANDO_FIM";
    public const string Fechada = "FECHADA";
}
```

3. **`MarcacaoLocalRepository`** — recebe `AgentDbContext` no construtor.

```csharp
public sealed class MarcacaoLocalRepository(AgentDbContext ctx)
{
    public async Task EnqueueAsync(MarcacaoLocal m) { ctx.MarcacoesLocais.Add(m); await ctx.SaveChangesAsync(); }
    public Task<List<MarcacaoLocal>> GetPendentesOrdenadasAsync() =>
        ctx.MarcacoesLocais.Where(m => !m.Sincronizada).OrderBy(m => m.CriadoEm).ToListAsync();
    public async Task MarcarSincronizadaAsync(string id)
    {
        var m = await ctx.MarcacoesLocais.SingleAsync(x => x.Id == id);
        m.Sincronizada = true; await ctx.SaveChangesAsync();
    }
    public async Task RegistrarFalhaSyncAsync(string id, string erro, string proximaTentativaEm)
    {
        var m = await ctx.MarcacoesLocais.SingleAsync(x => x.Id == id);
        m.TentativasSync += 1; m.UltimoErroSync = erro; m.ProximaTentativaEm = proximaTentativaEm;
        await ctx.SaveChangesAsync();
    }
    public Task<MarcacaoLocal?> GetByIdAsync(string id) =>
        ctx.MarcacoesLocais.SingleOrDefaultAsync(m => m.Id == id);
}
```

4. **`ConfiguracaoLocalRepository` / `EstadoJornadaRepository`** — singleton upsert: `GetAsync` retorna `FirstOrDefaultAsync()`; `UpsertAsync` faz `find Id==1` → atualiza campos ou `Add` com `Id=1`. Forçar `Id=1` sempre.

5. **`ServiceCollectionExtensions.AddAgentInfra`**:

```csharp
public static IServiceCollection AddAgentInfra(this IServiceCollection services, string dbPath)
{
    services.AddDbContext<AgentDbContext>(o => o.UseSqlite($"Data Source={dbPath}"));
    services.AddScoped<MarcacaoLocalRepository>();
    services.AddScoped<ConfiguracaoLocalRepository>();
    services.AddScoped<EstadoJornadaRepository>();
    services.AddSingleton<IClock, SystemClock>();
    return services;
}
```

6. **Contrato IPC** — records polimórficos serializados por `type`, frames JSON newline-delimited (Spec §4 "Contrato IPC Service ↔ WPF"). Usar `System.Text.Json` com `[JsonPolymorphic(TypeDiscriminatorPropertyName = "type")]` e `[JsonDerivedType(..., "TOAST")]`.

```csharp
namespace Timesheet.Agent.Ipc;

[JsonPolymorphic(TypeDiscriminatorPropertyName = "type")]
[JsonDerivedType(typeof(DialogRequest), "DIALOG_REQUEST")]
[JsonDerivedType(typeof(DialogResponse), "DIALOG_RESPONSE")]
[JsonDerivedType(typeof(ToastMessage), "TOAST")]
[JsonDerivedType(typeof(StatusPush), "STATUS_PUSH")]
public abstract record IpcMessage;

// kind: CONFIRM_INICIO_ANTECIPADO | CONFIRM_RETORNO_FORA_JANELA | PROMPT_FIM_JORNADA | PROMPT_ATIVIDADE
public sealed record DialogRequest(string Id, string Kind, Dictionary<string, string> Payload) : IpcMessage;
// answer: SIM | NAO | TIMEOUT ; payload opcional (ex.: atividade do PROMPT_FIM_JORNADA)
public sealed record DialogResponse(string Id, string Answer, Dictionary<string, string>? Payload = null) : IpcMessage;
public sealed record ToastMessage(string Title, string Body, int DurationS) : IpcMessage;
public sealed record StatusPush(string Estado, int PendentesCount) : IpcMessage;
```

`IpcSerializer`:

```csharp
public static class IpcSerializer
{
    private static readonly JsonSerializerOptions Opts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };
    public static string Serialize(IpcMessage msg) =>
        JsonSerializer.Serialize(msg, Opts) + "\n";
    public static IpcMessage Deserialize(string line) =>
        JsonSerializer.Deserialize<IpcMessage>(line.Trim(), Opts)
        ?? throw new FormatException("Frame IPC inválido");
}
```

> Atenção: o discriminador `type` deve serializar em MAIÚSCULAS (`TOAST`, `DIALOG_RESPONSE`) — o `JsonDerivedType` define o valor literal, então `CamelCase` não afeta o discriminador. Garantir nos testes que `"type":"TOAST"` aparece exatamente.

**Contrato com camadas adjacentes** (esta task PRODUZ infra para todas as outras):

```
Produz para: state machine (TASK-030), HTTP sync (TASK-029), Service host (TASK-033)
  - IClock: regras de tempo injetam IClock, nunca DateTime.Now direto
  - MarcacaoTipo/OrigemMarcacao/EstadoJornada: constantes — nenhuma task redefine string literal de tipo
  - MarcacaoLocalRepository/ConfiguracaoLocalRepository/EstadoJornadaRepository: única porta de acesso ao SQLite local
Produz para: IPC server (TASK-032) e WPF (TASK-034)
  - IpcMessage/IpcSerializer: contrato de mensagens named-pipe; ambos os lados usam estes records
```
