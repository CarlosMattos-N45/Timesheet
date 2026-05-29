---
checkpoint: null
complexity: M
created_at: "2026-05-29 09:29:36"
criteria:
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Idle_below_threshold_is_not_inactive
      text: Idle abaixo do limiar (30s) nao marca inativo
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Crossing_threshold_marks_inactive_and_records_start
      text: Cruzar o limiar marca inativo e registra InicioInatividade = agora - idleMs
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Continuous_inactivity_keeps_original_start_and_grows_duration
      text: Inatividade continua mantem o inicio original e cresce a duracao
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Return_to_activity_raises_event_with_window
      text: Retorno de atividade dispara OnRetornoDeInatividade com inicio e fim corretos
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~PrimeiroInputAposInatividade_true_once_then_false
      text: PrimeiroInputAposInatividade e true exatamente 1x e depois false
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Win32Provider_returns_nonnegative_idle
      text: Win32LastInputProvider.GetIdleMilliseconds retorna valor >= 0 sem excecao
    - done: false
      text: Solution compila e testes do InactivityTracker passam
    - done: false
      text: Cobertura do InactivityTracker (logica pura) >= 70%
deps:
    - TASK-028
id: TASK-031
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
tests: cd apps/agent && dotnet test Timesheet.Agent.sln -c Debug --filter FullyQualifiedName~InactivityTrackerTests
title: 'Detecção de input: InactivityTracker (lógica pura) + Win32LastInputProvider (GetLastInputInfo P/Invoke) + SessionMonitor (SessionLogon)'
updated_at: "2026-05-29 09:29:36"
---
## Contexto

O Agente precisa observar dois sinais do Windows para alimentar a máquina de estados (TASK-030): (1) **inatividade do usuário** — tempo desde o último input de teclado/mouse, via Win32 `GetLastInputInfo` (P/Invoke), com polling de 30s; (2) **evento de login da sessão Windows** — para disparar `INICIO_JORNADA` (RF-003) e o toast de saudação (RF-001).

Esta task implementa a camada de **detecção de input** dentro de `Timesheet.Agent.Service` (o Service host é o único projeto que roda no contexto Windows com acesso a sessão). Os detectores são abstraídos por interface para permitir teste sem o SO real: a lógica de "quanto tempo de inatividade contínua" e "houve transição de input?" é testável com um provider de "ticks de último input" fake; o P/Invoke fica numa implementação fina não-coberta por teste unitário (excluída da meta de cobertura, que mira Domain+Infra).

A Spec §2 define: "Inatividade: Win32 `GetLastInputInfo` via P/Invoke, polling 30s". A máquina de estados (TASK-030) consome `AvaliarInatividade(inicioInatividade, duracaoMin, horarios)` — então o detector precisa rastrear **quando** a inatividade começou e **por quanto tempo** ela durou continuamente, e detectar o **primeiro input após inatividade** (para RF-005 RETORNO_ALMOCO).

A Fundação (TASK-028) já forneceu `IClock`. O detector usa `IClock` para timestamps, nunca `DateTime.Now`.

## Comportamento Esperado

`InactivityTracker` é uma classe pura testável: recebe leituras periódicas de "milissegundos desde o último input" (vindas do `ILastInputProvider`) e mantém estado de inatividade contínua. `SessionMonitor` expõe um evento `SessionLogon`. Win32 fica em `Win32LastInputProvider` (P/Invoke) e `WindowsSessionMonitor` (SystemEvents/SessionSwitch), finos.

**Exemplos (entrada → saída esperada)** — `InactivityTracker` alimentado por `FakeClock` + sequência de leituras (idleMs = ms desde último input):

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `tracker.Observe(idleMs=0, agora=12:00:00)` | `EstaInativo == false`; `InicioInatividade == null` |
| `Observe(idleMs=30_000, agora=12:00:30)` (30s ocioso) | `EstaInativo == true`; `InicioInatividade == 12:00:00` (agora − idle) |
| após inativo, `Observe(idleMs=600_000, agora=12:10:00)` | `DuracaoInatividadeContinuaMin >= 10`; `InicioInatividade` permanece o original (≈12:00:00) |
| após inativo, `Observe(idleMs=0, agora=12:11:00)` (voltou input) | `EstaInativo == false`; dispara `RetornoDeInatividade(inicioInatividade≈12:00:00, fimInatividade=12:11:00)` |
| `Observe(idleMs=5_000)` várias vezes sem cruzar limiar | nunca marca inativo (idle < 30s configurável) |
| `tracker.PrimeiroInputAposInatividade` após `RetornoDeInatividade` | `true` exatamente 1× (no instante do retorno), depois `false` |
| `Win32LastInputProvider.GetIdleMilliseconds()` (impl real) | retorna `uint ≥ 0` sem exceção |
| `SessionMonitor` recebe `SessionSwitchReason.SessionLogon` | dispara evento `SessionLogon` exatamente 1× |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`Timesheet.Agent.Tests/Service/InactivityTrackerTests.cs`):

```csharp
private static DateTimeOffset At(int h,int m,int s) => new(2026,5,27,h,m,s,TimeSpan.FromHours(-3));

[Fact]
public void Idle_below_threshold_is_not_inactive()
{
    var t = new InactivityTracker(limiarInatividadeSeg: 30);
    t.Observe(idleMs: 5_000, agora: At(12,0,5));
    t.EstaInativo.Should().BeFalse();
    t.InicioInatividade.Should().BeNull();
}

[Fact]
public void Crossing_threshold_marks_inactive_and_records_start()
{
    var t = new InactivityTracker(30);
    t.Observe(idleMs: 30_000, agora: At(12,0,30));
    t.EstaInativo.Should().BeTrue();
    // inicio = agora - idle = 12:00:00
    t.InicioInatividade!.Value.Should().Be(At(12,0,0));
}

[Fact]
public void Continuous_inactivity_keeps_original_start_and_grows_duration()
{
    var t = new InactivityTracker(30);
    t.Observe(30_000, At(12,0,30));
    var inicio = t.InicioInatividade;
    t.Observe(600_000, At(12,10,0));
    t.InicioInatividade.Should().Be(inicio);
    t.DuracaoInatividadeContinuaMin.Should().BeGreaterThanOrEqualTo(10);
}

[Fact]
public void Return_to_activity_raises_event_with_window()
{
    var t = new InactivityTracker(30);
    RetornoDeInatividade? capturado = null;
    t.OnRetornoDeInatividade += e => capturado = e;
    t.Observe(30_000, At(12,0,30));     // inativo, inicio 12:00:00
    t.Observe(0, At(12,11,0));          // voltou input
    t.EstaInativo.Should().BeFalse();
    capturado.Should().NotBeNull();
    capturado!.InicioInatividade.Should().Be(At(12,0,0));
    capturado.FimInatividade.Should().Be(At(12,11,0));
}

[Fact]
public void PrimeiroInputAposInatividade_true_once_then_false()
{
    var t = new InactivityTracker(30);
    t.Observe(30_000, At(12,0,30));
    t.Observe(0, At(12,11,0));
    t.PrimeiroInputAposInatividade.Should().BeTrue();
    t.Observe(0, At(12,11,30));
    t.PrimeiroInputAposInatividade.Should().BeFalse();
}

[Fact]
public void Win32Provider_returns_nonnegative_idle()  // roda em Windows
{
    var p = new Win32LastInputProvider();
    p.GetIdleMilliseconds().Should().BeGreaterThanOrEqualTo(0u);
}
```

**Refatoração:** após green, extrair `At(h,m,s)` para `TestData` se compartilhado; isolar o cálculo `inicio = agora − TimeSpan.FromMilliseconds(idleMs)` num método privado nomeado.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/agent/src/Timesheet.Agent.Service/Input/ILastInputProvider.cs` | Criar | `interface { uint GetIdleMilliseconds(); }` |
| `apps/agent/src/Timesheet.Agent.Service/Input/Win32LastInputProvider.cs` | Criar | P/Invoke `GetLastInputInfo` + `Environment.TickCount`; `[SupportedOSPlatform("windows")]` |
| `apps/agent/src/Timesheet.Agent.Service/Input/InactivityTracker.cs` | Criar | Estado de inatividade contínua + evento `OnRetornoDeInatividade` + `RetornoDeInatividade` record |
| `apps/agent/src/Timesheet.Agent.Service/Input/ISessionMonitor.cs` | Criar | `interface { event Action SessionLogon; void Start(); void Stop(); }` |
| `apps/agent/src/Timesheet.Agent.Service/Input/WindowsSessionMonitor.cs` | Criar | `SystemEvents.SessionSwitch` → filtra `SessionLogon`/`SessionUnlock`; `[SupportedOSPlatform("windows")]` |

### Detalhamento Técnico

1. **`Win32LastInputProvider`** — P/Invoke real:

```csharp
[SupportedOSPlatform("windows")]
public sealed class Win32LastInputProvider : ILastInputProvider
{
    [StructLayout(LayoutKind.Sequential)]
    private struct LASTINPUTINFO { public uint cbSize; public uint dwTime; }

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);

    public uint GetIdleMilliseconds()
    {
        var lii = new LASTINPUTINFO { cbSize = (uint)Marshal.SizeOf<LASTINPUTINFO>() };
        if (!GetLastInputInfo(ref lii)) return 0;
        return unchecked((uint)Environment.TickCount) - lii.dwTime;
    }
}
```

2. **`InactivityTracker`** — recebe `int limiarInatividadeSeg` (30 default). Mantém: `bool EstaInativo`, `DateTimeOffset? InicioInatividade`, `bool PrimeiroInputAposInatividade`. `Observe(uint idleMs, DateTimeOffset agora)`:
   - `inativoAgora = idleMs >= limiar*1000`.
   - Transição **inativo→inativo (continua):** mantém `InicioInatividade`.
   - Transição **ativo→inativo:** seta `InicioInatividade = agora − idleMs`, `EstaInativo=true`.
   - Transição **inativo→ativo:** `EstaInativo=false`, `PrimeiroInputAposInatividade=true`, dispara `OnRetornoDeInatividade(new RetornoDeInatividade(InicioInatividade.Value, agora))`, **mas mantém o `InicioInatividade` da última inatividade** disponível até o próximo Observe ativo (que reseta para null e `PrimeiroInput=false`).
   - `DuracaoInatividadeContinuaMin` = `(agora − InicioInatividade).TotalMinutes` quando inativo, senão 0.

```csharp
public sealed record RetornoDeInatividade(DateTimeOffset InicioInatividade, DateTimeOffset FimInatividade);
```

> Importante: `PrimeiroInputAposInatividade` deve ser `true` apenas na primeira leitura ativa após uma inatividade; o segundo `Observe(0,...)` consecutivo o zera. Implementar com flag setada no retorno e limpa no `Observe` ativo subsequente.

3. **`WindowsSessionMonitor`** — assina `Microsoft.Win32.SystemEvents.SessionSwitch`; quando `e.Reason == SessionSwitchReason.SessionLogon || SessionUnlock` → invoca `SessionLogon`. `Start()` registra o handler; `Stop()` desregistra (evitar leak — `SystemEvents` é estático). Requer `Microsoft.Win32.SystemEvents` (já vem com `net8.0-windows` + WinForms; o projeto Service já é `net8.0-windows`).

> Nota de cobertura: `Win32LastInputProvider` e `WindowsSessionMonitor` (P/Invoke / SystemEvents) são camada de adaptação fina e dependem do SO — não contam para a meta de 70% (que é Domain+Infra). O `InactivityTracker` (lógica pura) é o alvo coberto exaustivamente.

**Contrato com camadas adjacentes:**

```
Produz para: Service host (TASK-033)
  - InactivityTracker.Observe(idle, agora) chamado a cada 30s pelo loop; quando DuracaoInatividadeContinuaMin cruza 10 dentro da janela de almoço, o host chama JourneyStateMachine.AvaliarInatividade
  - OnRetornoDeInatividade(inicio, fim): host usa o fim como T do RETORNO_ALMOCO (RF-005)
  - ISessionMonitor.SessionLogon: host dispara fluxo de INICIO_JORNADA (RF-003) + toast saudação (RF-001)
Consome de: Fundação (TASK-028) — IClock (timestamps); ILastInputProvider (Win32 real ou fake em teste)
```
