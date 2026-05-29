---
checkpoint: null
complexity: M
created_at: "2026-05-29 09:29:47"
criteria:
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Complete_resolves_pending_task_with_answer
      text: DialogCorrelator.Complete resolve a task pendente com o Answer recebido
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Timeout_resolves_with_TIMEOUT_answer
      text: Timeout resolve com DialogResponse Answer=TIMEOUT preservando o Id
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Complete_unknown_id_is_ignored
      text: Complete com Id desconhecido e ignorado sem excecao
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Complete_only_resolves_matching_id
      text: Complete resolve apenas a task do Id correspondente
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~SendAsync_writes_serialized_toast_to_channel
      text: IpcServer.SendAsync escreve no canal o ToastMessage serializado terminado em newline
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~SendDialogRequest_resolves_when_response_frame_arrives
      text: SendDialogRequestAsync resolve quando o frame DIALOG_RESPONSE correlacionado chega
    - done: true
      text: Solution compila e testes de Ipc passam
    - done: true
      text: Cobertura DialogCorrelator/IpcServer >= 70%
deps:
    - TASK-028
id: TASK-032
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
tests: cd apps/agent && dotnet test Timesheet.Agent.sln -c Debug --filter FullyQualifiedName~Ipc
title: 'IPC named pipe: DialogCorrelator (correlação + timeout 60s), IpcServer/IpcClient sobre IDuplexChannel, NamedPipeChannel com ACL owner-only + IdentityGuard'
updated_at: "2026-05-29 10:11:23"
---
## Contexto

O Agente roda em dois processos: o **Service** (`TimesheetAgent`, contexto de sessão Windows, detecta input e gerencia jornada) e a **UI WPF** (tray + diálogos modais + toast). Eles se comunicam por **named pipe** `\\.\pipe\TimesheetAgent`, frames JSON delimitados por newline. Esta task implementa a camada de transporte IPC bidirecional em `Timesheet.Agent.Ipc`: servidor (lado Service) e cliente (lado WPF), reusando os records de mensagem e `IpcSerializer` criados na Fundação (TASK-028).

Requisitos de segurança (Spec §4 e §7): a ACL do pipe é **restrita ao SID do Service** + verificação de identidade do processo cliente via `GetNamedPipeClientProcessId` (impedir injeção de processo malicioso). O servidor cria o pipe com `PipeSecurity` permitindo apenas o owner; ao aceitar conexão, valida que o PID do cliente pertence à mesma sessão/usuário esperado.

A Fundação (TASK-028) já forneceu: `IpcMessage` (records polimórficos `DialogRequest`, `DialogResponse`, `ToastMessage`, `StatusPush`), `IpcSerializer.Serialize/Deserialize`. Esta task **consome** esses tipos — não os recria.

O fluxo de diálogo (Spec §4): o Service envia `DIALOG_REQUEST` e aguarda `DIALOG_RESPONSE` correlacionada por `Id`, com **timeout de 60s** (timeout → resposta sintética `TIMEOUT`). Service também envia `TOAST` (fire-and-forget) e `STATUS_PUSH` (estado + contagem de pendentes para o tray).

## Comportamento Esperado

`IpcServer` (lado Service): aceita 1 conexão WPF, lê frames, expõe `SendDialogRequestAsync(DialogRequest, timeout)` que resolve com a `DialogResponse` correlacionada por `Id` (ou `DIALOG_RESPONSE` sintético com `Answer="TIMEOUT"` no estouro), e `SendAsync(ToastMessage|StatusPush)`. `IpcClient` (lado WPF): conecta, recebe `IpcMessage`s e expõe um evento por mensagem recebida; envia `DialogResponse` de volta. A correlação e o timeout são a lógica testável (sem pipe real, via um `IDuplexChannel` abstrato em memória).

**Exemplos (entrada → saída esperada)** — `DialogCorrelator` (lógica de correlação testável, sem pipe):

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `correlator.Register(id="d1")` retorna `Task<DialogResponse>` pendente | Task não-completa enquanto não houver resposta |
| `correlator.Complete(new DialogResponse("d1","SIM"))` | a Task de `d1` completa com `Answer=="SIM"` |
| `correlator.Complete(DialogResponse("desconhecido","SIM"))` | nenhuma exceção; nenhuma task afetada ( id não registrado é ignorado) |
| `Register("d2")` + timeout 50ms sem `Complete` | Task completa com `DialogResponse(Id="d2", Answer="TIMEOUT")` |
| 2 registros `d3`,`d4` + `Complete(d4,"NAO")` | só a task de `d4` completa (`"NAO"`); `d3` segue pendente |
| `IpcServer.SendAsync(ToastMessage)` com canal fake | o canal recebe a string serializada terminada em `\n` contendo `"type":"TOAST"` |
| `IpcClient.OnMessage` ao receber frame `STATUS_PUSH` | dispara evento com `StatusPush` desserializado (`PendentesCount` correto) |
| `IdentityGuard.IsTrusted(clientPid, expectedSessionId)` quando PID está na sessão esperada | `true` |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`Timesheet.Agent.Tests/Ipc/`):

```csharp
// DialogCorrelatorTests.cs
[Fact]
public async Task Complete_resolves_pending_task_with_answer()
{
    var c = new DialogCorrelator();
    var task = c.Register("d1", timeout: TimeSpan.FromSeconds(5));
    c.Complete(new DialogResponse("d1", "SIM"));
    (await task).Answer.Should().Be("SIM");
}

[Fact]
public async Task Timeout_resolves_with_TIMEOUT_answer()
{
    var c = new DialogCorrelator();
    var task = c.Register("d2", timeout: TimeSpan.FromMilliseconds(50));
    var resp = await task;
    resp.Id.Should().Be("d2");
    resp.Answer.Should().Be("TIMEOUT");
}

[Fact]
public void Complete_unknown_id_is_ignored()
{
    var c = new DialogCorrelator();
    var act = () => c.Complete(new DialogResponse("ghost", "SIM"));
    act.Should().NotThrow();
}

[Fact]
public async Task Complete_only_resolves_matching_id()
{
    var c = new DialogCorrelator();
    var t3 = c.Register("d3", TimeSpan.FromSeconds(5));
    var t4 = c.Register("d4", TimeSpan.FromSeconds(5));
    c.Complete(new DialogResponse("d4", "NAO"));
    (await t4).Answer.Should().Be("NAO");
    t3.IsCompleted.Should().BeFalse();
}

// IpcServerTests.cs — usa IDuplexChannel fake (em memória), nao NamedPipe real
[Fact]
public async Task SendAsync_writes_serialized_toast_to_channel()
{
    var channel = new FakeChannel();
    var server = new IpcServer(channel, new DialogCorrelator());
    await server.SendAsync(new ToastMessage("Bom dia", "Maria", 10));
    channel.Written.Should().ContainSingle()
        .Which.Should().Contain("\"type\":\"TOAST\"").And.EndWith("\n");
}

[Fact]
public async Task SendDialogRequest_resolves_when_response_frame_arrives()
{
    var channel = new FakeChannel();
    var server = new IpcServer(channel, new DialogCorrelator());
    var pending = server.SendDialogRequestAsync(
        new DialogRequest("d9", "PROMPT_FIM_JORNADA", new()), TimeSpan.FromSeconds(5));
    // simula o WPF respondendo
    channel.Inject(IpcSerializer.Serialize(new DialogResponse("d9", "SIM")));
    (await pending).Answer.Should().Be("SIM");
}
```

> Os testes não abrem `NamedPipeServerStream` real (frágil em CI). O `IpcServer`/`IpcClient` dependem de `IDuplexChannel` (abstração de leitura/escrita de linhas); a impl concreta `NamedPipeChannel` (P/Invoke de ACL + `GetNamedPipeClientProcessId`) é fina e fica fora da meta de cobertura.

**Refatoração:** após green, extrair `FakeChannel` para `Timesheet.Agent.Tests/Ipc/FakeChannel.cs` reutilizável entre server e client tests.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/agent/src/Timesheet.Agent.Ipc/IDuplexChannel.cs` | Criar | `interface { Task WriteLineAsync(string); IAsyncEnumerable<string> ReadLinesAsync(CancellationToken); }` |
| `apps/agent/src/Timesheet.Agent.Ipc/DialogCorrelator.cs` | Criar | Registro de `Id→TaskCompletionSource<DialogResponse>` com timeout → resposta `TIMEOUT` |
| `apps/agent/src/Timesheet.Agent.Ipc/IpcServer.cs` | Criar | Lado Service: `SendAsync(IpcMessage)`, `SendDialogRequestAsync(DialogRequest, timeout)`, loop de leitura que roteia `DialogResponse` ao correlator |
| `apps/agent/src/Timesheet.Agent.Ipc/IpcClient.cs` | Criar | Lado WPF: `event Action<IpcMessage> OnMessage`, `SendAsync(DialogResponse)`, loop de leitura |
| `apps/agent/src/Timesheet.Agent.Ipc/NamedPipeChannel.cs` | Criar | Impl real do `IDuplexChannel` sobre `NamedPipeServerStream`/`NamedPipeClientStream` com `PipeSecurity` (ACL owner-only) |
| `apps/agent/src/Timesheet.Agent.Ipc/IdentityGuard.cs` | Criar | `GetNamedPipeClientProcessId` (P/Invoke) + `IsTrusted(pid, expectedSessionId)` |
| `apps/agent/src/Timesheet.Agent.Ipc/Timesheet.Agent.Ipc.csproj` | Modificar | Add `System.IO.Pipes.AccessControl` 8.0.* (PipeSecurity ACL no Windows) |

### Detalhamento Técnico

1. **`DialogCorrelator`** — dicionário thread-safe `ConcurrentDictionary<string, TaskCompletionSource<DialogResponse>>`. `Register(id, timeout)`: cria TCS, agenda `CancellationTokenSource(timeout)` que, ao disparar, faz `TrySetResult(new DialogResponse(id, "TIMEOUT"))` e remove do dicionário. Retorna `tcs.Task`. `Complete(resp)`: se `TryRemove(resp.Id)` → `tcs.TrySetResult(resp)`; id desconhecido → no-op.

```csharp
public Task<DialogResponse> Register(string id, TimeSpan timeout)
{
    var tcs = new TaskCompletionSource<DialogResponse>(TaskCreationOptions.RunContinuationsAsynchronously);
    _pending[id] = tcs;
    var cts = new CancellationTokenSource(timeout);
    cts.Token.Register(() =>
    {
        if (_pending.TryRemove(id, out var t)) t.TrySetResult(new DialogResponse(id, "TIMEOUT"));
    });
    return tcs.Task;
}
public void Complete(DialogResponse resp)
{
    if (_pending.TryRemove(resp.Id, out var tcs)) tcs.TrySetResult(resp);
}
```

2. **`IpcServer`** — construtor `(IDuplexChannel channel, DialogCorrelator correlator)`. `SendAsync(IpcMessage m)` → `channel.WriteLineAsync(IpcSerializer.Serialize(m))`. `SendDialogRequestAsync(req, timeout)` → registra `correlator.Register(req.Id, timeout)`, envia o request, retorna a task. `StartReadLoopAsync(ct)`: `await foreach line in channel.ReadLinesAsync(ct)` → `IpcSerializer.Deserialize(line)` → se `DialogResponse` → `correlator.Complete(dr)`.

3. **`IpcClient`** (WPF) — construtor `(IDuplexChannel channel)`. Loop de leitura dispara `OnMessage(msg)` por frame. `SendAsync(DialogResponse)` → escreve serializado. WPF assina `OnMessage` para abrir o diálogo/toast correto.

4. **`NamedPipeChannel`** — servidor: `NamedPipeServerStream("TimesheetAgent", PipeDirection.InOut, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous, ...)` criado via `NamedPipeServerStreamAcl.Create` com `PipeSecurity` concedendo `FullControl` apenas ao `WindowsIdentity.GetCurrent().Owner` e negando todo o resto. Cliente: `NamedPipeClientStream(".", "TimesheetAgent", PipeDirection.InOut, PipeOptions.Asynchronous)`. `ReadLinesAsync` usa `StreamReader.ReadLineAsync`; `WriteLineAsync` usa `StreamWriter` com `AutoFlush=true` escrevendo a string (que já termina em `\n` via serializer — usar `Write`, não `WriteLine`, para não duplicar quebra). `[SupportedOSPlatform("windows")]`.

5. **`IdentityGuard`** — P/Invoke `GetNamedPipeClientProcessId(SafePipeHandle, out uint pid)`. `IsTrusted(uint pid, int expectedSessionId)`: abre `Process.GetProcessById((int)pid)`, compara `process.SessionId == expectedSessionId`. Após `WaitForConnection`, o servidor chama `IsTrusted`; se falso, fecha a conexão e loga. (O teste cobre a comparação de sessão com um pid/sessão controlados; o P/Invoke real fica fora da cobertura.)

**Contrato com camadas adjacentes:**

```
Produz para: Service host (TASK-033)
  - IpcServer.SendDialogRequestAsync(DialogRequest, 60s) → DialogResponse (Answer: SIM|NAO|TIMEOUT) — usado para CONFIRM_INICIO_ANTECIPADO, CONFIRM_RETORNO_FORA_JANELA, PROMPT_FIM_JORNADA
  - IpcServer.SendAsync(ToastMessage) — saudação RF-001 / toast de sync
  - IpcServer.SendAsync(StatusPush) — atualiza badge do tray (pendentes)
Produz para: WPF (TASK-034)
  - IpcClient.OnMessage(IpcMessage) — WPF abre diálogo/toast conforme tipo; responde via SendAsync(DialogResponse)
Consome de: Fundação (TASK-028) — IpcMessage records + IpcSerializer
Segurança: NamedPipeChannel cria pipe com ACL owner-only; IdentityGuard valida PID/sessão do cliente antes de confiar (Spec §7)
```
