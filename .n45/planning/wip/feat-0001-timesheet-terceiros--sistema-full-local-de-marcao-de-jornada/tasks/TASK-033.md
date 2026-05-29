---
checkpoint: null
complexity: G
created_at: "2026-05-29 09:31:33"
criteria:
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Drains_pending_in_chronological_order_and_marks_synced
      text: Drena pendentes em ordem cronologica (CriadoEm asc) e marca Sincronizada=true
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~TransientFailure_keeps_pending_and_increments_attempts
      text: TransientFailure mantem pendente, incrementa TentativasSync e preenche ProximaTentativaEm
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~DiscardLocal_and_AlreadyExists_both_mark_synced
      text: DiscardLocal (AJUSTE_WEB venceu) e AlreadyExists (409 CONFLICT) ambos marcam sincronizada
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Does_not_post_when_backend_down
      text: Nao chama PostMarcacaoAsync quando backend down (IsHealthyAsync=false) e fila fica intacta
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~RegistrarAutomatico_inicio_enqueues_and_sets_state_em_jornada
      text: RegistrarAutomatico(INICIO_JORNADA) enfileira MarcacaoLocal com Id UUID v4 e seta estado EM_JORNADA
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~ExigeDialogo_does_not_enqueue
      text: ExigeDialogo nao enfileira marcacao (resolvido via IPC)
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Fechar_sets_state_fechada_and_enqueues_fim
      text: Fechar enfileira FIM_JORNADA e seta estado FECHADA
    - done: false
      test: cd apps/agent && dotnet build Timesheet.Agent.sln -c Debug
      text: Solution compila, agent-build ok e testes de SyncProcessor/DecisionApplier passam
    - done: false
      text: Cobertura SyncProcessor+DecisionApplier >= 70%
deps:
    - TASK-028
    - TASK-029
    - TASK-030
    - TASK-031
    - TASK-032
    - TASK-035
id: TASK-033
linter: cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes
n45_version: 0.2.0
persona: backend
phase: Phase 5 — Agente Desktop
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: cd apps/agent && dotnet test Timesheet.Agent.sln -c Debug --filter "FullyQualifiedName~SyncProcessorTests|FullyQualifiedName~DecisionApplierTests"
title: 'Service host: SyncProcessor (drena fila RN-012 + backoff), DecisionApplier (decisão→marcação+estado), JourneyHostedService + SyncHostedService, Program.cs wiring + Serilog'
updated_at: "2026-05-29 10:33:44"
---
## Contexto

Esta task amarra todas as camadas do Agente no **Service host** (`Timesheet.Agent.Service`, Windows Service `TimesheetAgent`). Hoje o `Program.cs` só registra o `WindowsService` vazio. Aqui criamos os `BackgroundService`s que orquestram o ciclo de vida real:

1. **`JourneyHostedService`** — assina `ISessionMonitor.SessionLogon` (RF-003/RF-001), faz polling 30s do `InactivityTracker` (RF-004), trata retorno de inatividade (RF-005), monitora horário de fim (RF-006) e auto-encerramento. Traduz cada `DecisaoJornada` da máquina (TASK-030) em efeito: persistir `MarcacaoLocal` via repositório (TASK-028), atualizar `EstadoJornadaAtual`, e — quando a decisão é `ExigeDialogo` — chamar `IpcServer.SendDialogRequestAsync` (TASK-032) e resolver com a máquina.
2. **`SyncHostedService`** — loop 30s (RF-011): se `IsHealthyAsync` (e `IsReadyAsync` no primeiro ciclo), drena a fila `GetPendentesOrdenadasAsync` em ordem cronológica, faz `PostMarcacaoAsync` (TASK-029) com token válido (`TokenManager`), e aplica o `SyncOutcome`: `Created`/`AlreadyExists`/`DiscardLocal`/`Rejected` → `MarcarSincronizadaAsync`; `TransientFailure` → `RegistrarFalhaSyncAsync` + `proxima_tentativa_em` (backoff). Empurra `StatusPush` (contagem de pendentes) ao tray.

As dependências (todas done nesta fase):
- TASK-028: `IClock`, constantes, repositórios, `AddAgentInfra`.
- TASK-029: `IBackendClient`, `TokenManager`, `AddAgentHttp`, `SyncOutcome`.
- TASK-030: `JourneyStateMachine`, `DecisaoJornada`, `HorariosJornada`.
- TASK-031: `InactivityTracker`, `ILastInputProvider`, `ISessionMonitor`.
- TASK-032: `IpcServer`, `NamedPipeChannel`, `IpcMessage`.

O Service host **não** reimplementa regra de jornada, parsing HTTP, P/Invoke nem serialização IPC — apenas coordena. A lógica testável aqui é a **tradução decisão→efeito** e a **aplicação de `SyncOutcome`**, extraídas em classes puras (`DecisionApplier`, `SyncProcessor`) injetáveis com repositório e client mockados (Moq).

## Comportamento Esperado

`SyncProcessor.ProcessarFilaAsync` e `DecisionApplier.AplicarAsync` são o alvo de teste (com `MarcacaoLocalRepository` sobre SQLite :memory: e `IBackendClient` mock).

**Exemplos (entrada → saída esperada)** — valores reais:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Fila com 2 pendentes (`a`@12:00, `b`@13:00); client retorna `Created` para ambas | ambas viram `Sincronizada=true`; client chamado 2× na ordem `a` depois `b` |
| Pendente; client retorna `TransientFailure` | marcação continua `Sincronizada=false`; `TentativasSync` incrementa; `ProximaTentativaEm` preenchido (futuro) |
| Pendente; client retorna `DiscardLocal` (AJUSTE_WEB venceu) | marcação `Sincronizada=true` (descartada localmente, não reenfileira) |
| Pendente; client retorna `AlreadyExists` (409 CONFLICT) | marcação `Sincronizada=true` (idempotência: sucesso) |
| `ProcessarFilaAsync` quando `IsHealthyAsync()==false` | client.PostMarcacaoAsync **nunca** é chamado; fila intacta |
| `DecisionApplier.AplicarAsync(RegistrarAutomatico(INICIO_JORNADA, 09:02, AGENTE_AUTOMATICO))` | 1 `MarcacaoLocal` enfileirada com `Tipo=INICIO_JORNADA`, `Origem=AGENTE_AUTOMATICO`, `Id`=UUID v4, `Sincronizada=false`; `EstadoJornadaAtual.Status=EM_JORNADA` |
| `AplicarAsync(RegistrarPendente(RETORNO_ALMOCO, 14:30))` | `MarcacaoLocal` enfileirada; estado da jornada marcado conforme (retorno → EM_JORNADA), mas a marcação carrega flag pendente para a Web detectar |
| `AplicarAsync(ExigeDialogo(...))` | **nenhuma** marcação enfileirada (decisão de diálogo é resolvida pelo host via IPC, não persiste direto) |
| `AplicarAsync(Fechar(FIM_JORNADA, 18:05, "atividade..."))` | `MarcacaoLocal(FIM_JORNADA)` enfileirada; `EstadoJornadaAtual.Status=FECHADA` |

## EstratégiaDeTeste (host = código novo; aplicar TDD nas classes puras)

> As classes `DecisionApplier` e `SyncProcessor` são **código novo** — aplicar TDD red→green. Os `BackgroundService`s (`JourneyHostedService`, `SyncHostedService`) são camada de orquestração fina (timers, wiring de eventos) e ficam fora da meta de cobertura, igual aos adaptadores Win32/pipe.

**Testes a escrever antes da implementação** (`Timesheet.Agent.Tests/Service/`):

```csharp
// SyncProcessorTests.cs — repo real (SQLite :memory:), IBackendClient via Moq
[Fact]
public async Task Drains_pending_in_chronological_order_and_marks_synced()
{
    await _repo.EnqueueAsync(Mk("b", criadoEm: "2026-05-27T13:00:00Z"));
    await _repo.EnqueueAsync(Mk("a", criadoEm: "2026-05-27T12:00:00Z"));
    _client.Setup(c => c.IsHealthyAsync(It.IsAny<CancellationToken>())).ReturnsAsync(true);
    var seq = new List<string>();
    _client.Setup(c => c.PostMarcacaoAsync(It.IsAny<MarcacaoLocal>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
        .Callback<MarcacaoLocal,string,CancellationToken>((m,_,__) => seq.Add(m.Id))
        .ReturnsAsync(SyncOutcome.Created);

    await _sut.ProcessarFilaAsync(CancellationToken.None);

    seq.Should().Equal("a", "b");
    (await _repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
}

[Fact]
public async Task TransientFailure_keeps_pending_and_increments_attempts()
{
    await _repo.EnqueueAsync(Mk("x", criadoEm: "2026-05-27T12:00:00Z"));
    _client.Setup(c => c.IsHealthyAsync(It.IsAny<CancellationToken>())).ReturnsAsync(true);
    _client.Setup(c => c.PostMarcacaoAsync(It.IsAny<MarcacaoLocal>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
        .ReturnsAsync(SyncOutcome.TransientFailure);

    await _sut.ProcessarFilaAsync(CancellationToken.None);

    var pend = await _repo.GetPendentesOrdenadasAsync();
    pend.Should().ContainSingle();
    pend[0].TentativasSync.Should().Be(1);
    pend[0].ProximaTentativaEm.Should().NotBeNull();
}

[Fact]
public async Task DiscardLocal_and_AlreadyExists_both_mark_synced()
{
    await _repo.EnqueueAsync(Mk("d", criadoEm: "2026-05-27T12:00:00Z"));
    await _repo.EnqueueAsync(Mk("e", criadoEm: "2026-05-27T12:30:00Z"));
    _client.Setup(c => c.IsHealthyAsync(It.IsAny<CancellationToken>())).ReturnsAsync(true);
    _client.SetupSequence(c => c.PostMarcacaoAsync(It.IsAny<MarcacaoLocal>(), It.IsAny<string>(), It.IsAny<CancellationToken>()))
        .ReturnsAsync(SyncOutcome.DiscardLocal).ReturnsAsync(SyncOutcome.AlreadyExists);

    await _sut.ProcessarFilaAsync(CancellationToken.None);
    (await _repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
}

[Fact]
public async Task Does_not_post_when_backend_down()
{
    await _repo.EnqueueAsync(Mk("z", criadoEm: "2026-05-27T12:00:00Z"));
    _client.Setup(c => c.IsHealthyAsync(It.IsAny<CancellationToken>())).ReturnsAsync(false);

    await _sut.ProcessarFilaAsync(CancellationToken.None);

    _client.Verify(c => c.PostMarcacaoAsync(It.IsAny<MarcacaoLocal>(), It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
    (await _repo.GetPendentesOrdenadasAsync()).Should().ContainSingle();
}

// DecisionApplierTests.cs — repo real (:memory:), IClock = FakeClock
[Fact]
public async Task RegistrarAutomatico_inicio_enqueues_and_sets_state_em_jornada()
{
    await _applier.AplicarAsync(new RegistrarAutomatico(
        MarcacaoTipo.InicioJornada, At(9,2), OrigemMarcacao.AgenteAutomatico));
    var pend = await _repo.GetPendentesOrdenadasAsync();
    pend.Should().ContainSingle();
    pend[0].Tipo.Should().Be("INICIO_JORNADA");
    pend[0].Origem.Should().Be("AGENTE_AUTOMATICO");
    Guid.TryParse(pend[0].Id, out _).Should().BeTrue();    // UUID v4 = idempotency_key
    (await _estadoRepo.GetAsync())!.Status.Should().Be("EM_JORNADA");
}

[Fact]
public async Task ExigeDialogo_does_not_enqueue()
{
    await _applier.AplicarAsync(new ExigeDialogo("PROMPT_FIM_JORNADA", At(18,0)));
    (await _repo.GetPendentesOrdenadasAsync()).Should().BeEmpty();
}

[Fact]
public async Task Fechar_sets_state_fechada_and_enqueues_fim()
{
    await _applier.AplicarAsync(new Fechar(MarcacaoTipo.FimJornada, At(18,5), "Atividade do dia ok"));
    (await _estadoRepo.GetAsync())!.Status.Should().Be("FECHADA");
    (await _repo.GetPendentesOrdenadasAsync()).Should().ContainSingle()
        .Which.Tipo.Should().Be("FIM_JORNADA");
}
```

**Controle negativo (red brownfield):** N/A — `DecisionApplier`/`SyncProcessor` são código novo; o red vem natural (classe não existe).

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/agent/src/Timesheet.Agent.Service/Sync/SyncProcessor.cs` | Criar | Drena fila pendente, aplica `SyncOutcome`, backoff em falha |
| `apps/agent/src/Timesheet.Agent.Service/Journey/DecisionApplier.cs` | Criar | Traduz `DecisaoJornada` → enfileirar `MarcacaoLocal` + atualizar `EstadoJornadaAtual` |
| `apps/agent/src/Timesheet.Agent.Service/Journey/JourneyHostedService.cs` | Criar | `BackgroundService`: session logon + polling 30s + fim/auto-encerramento; resolve diálogos via IpcServer |
| `apps/agent/src/Timesheet.Agent.Service/Sync/SyncHostedService.cs` | Criar | `BackgroundService`: loop 30s chamando `SyncProcessor` + `StatusPush` ao tray |
| `apps/agent/src/Timesheet.Agent.Service/Program.cs` | Modificar | `AddAgentInfra(dbPath)` + `AddAgentHttp(baseUrl)` + registrar `SyncProcessor`, `DecisionApplier`, `InactivityTracker`, `IpcServer`(NamedPipeChannel), `ISessionMonitor`, os 2 hosted services; `Serilog` JSON rotativo + `Log.CloseAndFlush()` no shutdown |
| `apps/agent/src/Timesheet.Agent.Service/Timesheet.Agent.Service.csproj` | Modificar | Add `Serilog.Extensions.Hosting`, `Serilog.Sinks.File`, `Serilog.Formatting.Compact` (8.0.*/latest); já referencia Domain/Infra.Http/Infra.Db/Ipc |

### Detalhamento Técnico

1. **`DecisionApplier`** — construtor `(MarcacaoLocalRepository repo, EstadoJornadaRepository estadoRepo, IClock clock)`. `AplicarAsync(DecisaoJornada d)` via `switch`:
   - `RegistrarAutomatico`/`RegistrarConfirmado`/`RegistrarPendente` → cria `MarcacaoLocal { Id = Guid.NewGuid().ToString(), Tipo, HorarioRegistrado = horario.ToUniversalTime().ToString("o"), HorarioEfetivo = horario..., Origem, DataJornada = horario.LocalDateTime.Date ISO, CriadoEm = clock.NowUtc "o", Sincronizada=false }` → `EnqueueAsync`. Atualiza `EstadoJornadaAtual` (INICIO→EM_JORNADA, SAIDA_ALMOCO→EM_ALMOCO, RETORNO→EM_JORNADA).
   - `ExigeDialogo`/`Relembrar`/`NenhumaAcao` → no-op (não persiste; o host trata o diálogo via IPC e re-chama a máquina com a resposta).
   - `Fechar`/`FecharPendente` → enfileira `FIM_JORNADA`; `EstadoJornadaAtual.Status = FECHADA`. (A atividade do `Fechar` não vai ao backend pelo contrato de marcações — ver nota de fronteira abaixo.)

2. **`SyncProcessor`** — construtor `(MarcacaoLocalRepository repo, IBackendClient client, TokenManager tokens, IClock clock)`. `ProcessarFilaAsync(ct)`:
   - Se `!await client.IsHealthyAsync(ct)` → retorna (não toca a fila).
   - `var token = await tokens.GetValidAccessTokenAsync()`; em `AuthException` → loga e retorna (sync pausa até novo login).
   - `foreach m in await repo.GetPendentesOrdenadasAsync()`: `var outcome = await client.PostMarcacaoAsync(m, token, ct)`; `switch`:
     - `Created|AlreadyExists|DiscardLocal|Rejected` → `await repo.MarcarSincronizadaAsync(m.Id)`.
     - `TransientFailure` → `await repo.RegistrarFalhaSyncAsync(m.Id, "sync transient", proxima)` onde `proxima = clock.NowUtc.AddSeconds(backoff(m.TentativasSync+1)).ToString("o")` (backoff exponencial 1→2→4…s, teto 30s); **break** o loop (circuito provavelmente aberto — não martelar).
   - Retorna a contagem de pendentes restante (para o `StatusPush`).

3. **`SyncHostedService`** — `ExecuteAsync`: `using var timer = new PeriodicTimer(TimeSpan.FromSeconds(30))`; a cada tick cria um `IServiceScope` (repos são `Scoped`), resolve `SyncProcessor`, chama `ProcessarFilaAsync`, e envia `StatusPush(estado, pendentes)` via `IpcServer`. Trata exceção sem derrubar o loop (loga via Serilog).

4. **`JourneyHostedService`** — `ExecuteAsync`: inicia `ISessionMonitor.Start()`, assina `SessionLogon` → ao logar: lê `HorariosJornada` do cadastro (via `IBackendClient.GetMe`? não — o Agente já tem os horários do cadastro local; persistir os 4 horários em `ConfiguracaoLocal` no onboarding (TASK-034) ou buscar de `terceiros/me`). **Decisão:** os 4 horários ficam disponíveis ao host; para esta task, ler de um `IHorariosProvider` simples que lê de `ConfiguracaoLocal` (estender o repo) — manter o host fino. Disparar `JourneyStateMachine.AvaliarLogin(...)`; `RegistrarAutomatico` com atraso → `IpcServer.SendAsync(ToastMessage(saudacao+atraso))`; sempre `DecisionApplier.AplicarAsync`. `ExigeDialogo` → `await IpcServer.SendDialogRequestAsync(req, 60s)` → resolve com `JourneyStateMachine.Resolver...` → `AplicarAsync`. Polling 30s: `InactivityTracker.Observe(provider.GetIdleMilliseconds(), clock.NowUtc)`; checar janela almoço/fim/auto-encerramento.

> **Fronteira documentada:** a atividade (≥10 chars) capturada no `PROMPT_FIM_JORNADA` **não** é enviada pelo Agente — o contrato `POST /api/v1/marcacoes` não tem campo atividade (Spec §4: Agente envia só marcações). O Agente registra `FIM_JORNADA`; a atividade é persistida pela Web via `POST /jornadas/{id}/atividade`. Na v1.0 o Agente captura a atividade no diálogo para UX, mas não a sincroniza. Comentar isso no `DecisionApplier`.

5. **Saudação (RF-001)** — toast `"Bom dia/Boa tarde/Boa noite, {nome}. Início registrado às {hora}."` conforme `clock.NowLocal.Hour` (0–11 / 12–17 / 18–23), nome preservando acentos. `duration_s = 10`.

6. **Serilog** — `Log.Logger = new LoggerConfiguration().WriteTo.File(new CompactJsonFormatter(), path, rollingInterval: Day, fileSizeLimitBytes: 5MB, retainedFileCountLimit: 20, rollOnFileSizeLimit: true).CreateLogger()`. Redact obrigatório de `jwt_access_token`, `jwt_refresh_token`, `senha` (não logar esses campos). `Log.CloseAndFlush()` no `IHostApplicationLifetime.ApplicationStopping`.

**Contrato com camadas adjacentes:**

```
Consome de: TASK-028 (repos, IClock, EstadoJornada constantes), TASK-029 (IBackendClient, TokenManager, SyncOutcome, AuthException), TASK-030 (JourneyStateMachine, DecisaoJornada), TASK-031 (InactivityTracker, ILastInputProvider, ISessionMonitor), TASK-032 (IpcServer, NamedPipeChannel, ToastMessage/DialogRequest)
Produz para: WPF (TASK-034) — via IpcServer envia DialogRequest/Toast/StatusPush; recebe DialogResponse
Efeito de RN-012 no host: DiscardLocal (AJUSTE_WEB venceu) ⇒ marca sincronizada sem reenfileirar; demais conflitos idempotentes (AlreadyExists) ⇒ sucesso
```

> Nota: `IBackendClient.PostMarcacaoAsync` assinatura usada `(MarcacaoLocal m, string accessToken, CancellationToken ct)` e `IsHealthyAsync(CancellationToken ct)`. Se TASK-029 expôs assinatura levemente diferente, usar a real da TASK-029 (este é o consumidor — alinhar ao contrato real produzido lá, sem inventar).
