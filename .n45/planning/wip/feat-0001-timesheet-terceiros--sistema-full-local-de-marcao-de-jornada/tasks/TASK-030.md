---
checkpoint: code-review
complexity: M
created_at: "2026-05-29 09:27:21"
criteria:
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Login_dentro_da_janela_registra_automatico_sem_dialogo
      text: Login dentro da janela [h_ini+-30min] registra automatico sem dialogo nem atraso
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Login_em_atraso_registra_e_emite_toast_de_atraso
      text: Login em atraso registra T e expoe AtrasoMinutos=45
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Login_antecipado_exige_dialogo_com_fallback_h_ini
      text: Login antecipado exige CONFIRM_INICIO_ANTECIPADO com fallback=h_ini
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~ResolverInicioAntecipado_timeout_usa_h_ini
      text: ResolverInicioAntecipado TIMEOUT usa h_ini
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Login_em_fim_de_semana_sem_trabalho_nao_registra
      text: Login em fim de semana sem trabalhaFds nao registra
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Inatividade_na_janela_de_almoco_registra_saida
      text: Inatividade >=10min intersectando janela de almoco registra SAIDA_ALMOCO no inicio da inatividade
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Inatividade_fora_da_janela_nao_registra
      text: Inatividade fora da janela ou <10min nao registra
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Retorno_negado_gera_marcacao_pendente
      text: Retorno fora da janela exige CONFIRM_RETORNO_FORA_JANELA; negado gera marcacao PENDENTE
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Fim_timeout_reagenda_em_30min
      text: Fim com SIM e atividade>=10 fecha jornada com T_confirmacao; TIMEOUT reagenda em 30min
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~AutoEncerramento_apos_60min_inatividade_fecha_pendente
      text: Auto-encerramento >=60min inatividade pos-fim fecha PENDENTE no ultimo input; <60min nao age
    - done: true
      text: Solution compila e todos os testes da JourneyStateMachine passam
    - done: true
      text: Cobertura Domain >= 70%
deps:
    - TASK-028
id: TASK-030
linter: cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes
n45_version: 0.2.0
persona: backend
phase: Phase 5 — Agente Desktop
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: true
    red: true
    refactor: true
tests: cd apps/agent && dotnet test Timesheet.Agent.sln -c Debug --filter FullyQualifiedName~JourneyStateMachineTests
title: 'Domain: máquina de estados de jornada pura (RF-003/004/005/006) com janelas de tolerância, antecipação/atraso, inatividade, retorno fora de janela, fim e auto-encerramento'
updated_at: "2026-05-29 10:04:26"
worktree:
    base_sha: 446ecde37508c3cee0c57751bf65413574f6eed1
    branch: worktree-agent-f1ff1a547f666304
    path: .n45\worktree\agent-f1ff1a547f666304
---
## Contexto

O coração do Agente é a **máquina de estados de jornada** (camada `Timesheet.Agent.Domain`): regras puras, determinísticas e sem dependência de Win32/IPC/HTTP, que decidem — dadas as marcações do dia, os horários cadastrados e o instante atual — qual marcação criar, se exige diálogo de confirmação, e qual o próximo estado. Mantê-la pura (apenas `IClock` injetado) é o que permite testá-la exaustivamente, atingindo o quality gate de 70% sem tocar UI.

Esta task implementa as regras dos RF-003, RF-004, RF-005, RF-006:
- **RF-003 (INICIO_JORNADA):** login do Windows às `T`. Dentro de `[h_ini−30min, h_ini+30min]` → registra `T` automático sem prompt. Em atraso (`T > h_ini+30min`) → registra `T` automático + toast informativo "Atraso de N min". Em antecipação (`T < h_ini−30min`) → exige diálogo `CONFIRM_INICIO_ANTECIPADO` (SIM → `T`; NÃO/TIMEOUT → `h_ini`). Em fim de semana com `trabalha_fim_de_semana=false` → nenhum registro.
- **RF-004 (SAIDA_ALMOCO):** inatividade contínua ≥ 10min cuja janela intersecta `[h_alm_saida−30min, h_alm_saida+30min]` → registra início da inatividade, automático, sem prompt. Fora da janela → não registra.
- **RF-005 (RETORNO_ALMOCO):** primeiro input após SAIDA_ALMOCO. Dentro de `[h_alm_retorno−30min, h_alm_retorno+30min]` → registra `T` sem prompt. Fora → exige diálogo `CONFIRM_RETORNO_FORA_JANELA` (SIM → `T` confirmado; NÃO/TIMEOUT → marcação `PENDENTE` + jornada `PENDENTE`).
- **RF-006 (FIM_JORNADA):** ao atingir `h_fim` → diálogo `PROMPT_FIM_JORNADA`. SIM → form atividade (≥10 chars) → `FIM_JORNADA = T_confirmacao`, jornada `FECHADA`. TIMEOUT/NÃO → "lembrar em 30 min" (re-prompt). Inatividade ≥ 60min após `h_fim` sem confirmação → `FIM_JORNADA = último_input`, jornada `PENDENTE`, sem atividade.

A Fundação (TASK-028) já forneceu `IClock`, `MarcacaoTipo`, `OrigemMarcacao`, `EstadoJornada`. A máquina **não** persiste nem chama rede — apenas retorna decisões; o Service host (TASK-033) aplica os efeitos (persistir via repositório, enviar IPC).

## Comportamento Esperado

A entrada da máquina são os horários cadastrados (`HorariosJornada`), o estado atual (`EstadoJornada`), o instante do evento e flags; a saída é uma `DecisaoJornada` declarativa. Os testes exercitam todas as faixas com `FakeClock`.

**Exemplos (entrada → saída esperada)** — valores reais (horários cadastrados: ini=09:00, saída_alm=12:00, ret_alm=13:00, fim=18:00, fuso BRT):

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `AvaliarLogin(T=09:02, h_ini=09:00, fimDeSemana=false, trabalhaFds=false)` | `RegistrarAutomatico(tipo=INICIO_JORNADA, horario=09:02, origem=AGENTE_AUTOMATICO)`, sem diálogo, sem toast de atraso |
| `AvaliarLogin(T=09:45, h_ini=09:00)` (atraso 45min) | `RegistrarAutomatico(INICIO_JORNADA, 09:45, AGENTE_AUTOMATICO)` + `ToastAtraso(minutos=45)` |
| `AvaliarLogin(T=06:45, h_ini=09:00)` (antecipação) | `ExigeDialogo(kind=CONFIRM_INICIO_ANTECIPADO, horarioProposto=06:45, fallback=09:00)` |
| `ResolverInicioAntecipado(answer=SIM, T=06:45, h_ini=09:00)` | `RegistrarConfirmado(INICIO_JORNADA, 06:45, AGENTE_CONFIRMADO)` |
| `ResolverInicioAntecipado(answer=TIMEOUT, T=06:45, h_ini=09:00)` | `RegistrarConfirmado(INICIO_JORNADA, 09:00, AGENTE_CONFIRMADO)` (fallback = h_ini) |
| `AvaliarLogin(T=10:00, h_ini=09:00, ehFimDeSemana=true, trabalhaFds=false)` | `NenhumaAcao` (sábado/domingo sem trabalho de fds) |
| `AvaliarInatividade(inicioInat=12:05, duracaoMin=13, h_alm_saida=12:00)` | `RegistrarAutomatico(SAIDA_ALMOCO, 12:05, AGENTE_AUTOMATICO)` (janela [11:30,12:30] intersecta) |
| `AvaliarInatividade(inicioInat=15:00, duracaoMin=13, h_alm_saida=12:00)` | `NenhumaAcao` (fora da janela de almoço) |
| `AvaliarInatividade(inicioInat=12:05, duracaoMin=8, h_alm_saida=12:00)` | `NenhumaAcao` (< 10min) |
| `AvaliarRetorno(T=13:10, h_alm_retorno=13:00)` | `RegistrarAutomatico(RETORNO_ALMOCO, 13:10, AGENTE_AUTOMATICO)` (dentro de [12:30,13:30]) |
| `AvaliarRetorno(T=14:30, h_alm_retorno=13:00)` | `ExigeDialogo(CONFIRM_RETORNO_FORA_JANELA, horarioProposto=14:30)` |
| `ResolverRetornoForaJanela(answer=NAO, T=14:30)` | `RegistrarPendente(RETORNO_ALMOCO, 14:30)` (marcação PENDENTE → jornada PENDENTE) |
| `AvaliarFim(T=18:00, h_fim=18:00)` | `ExigeDialogo(PROMPT_FIM_JORNADA, horarioProposto=18:00)` |
| `ResolverFim(answer=SIM, atividade="Desenvolvi a feature X", T=18:05)` | `Fechar(FIM_JORNADA, 18:05, atividade="Desenvolvi a feature X")` |
| `ResolverFim(answer=TIMEOUT, T=18:00)` | `Relembrar(em=18:30)` (re-prompt em 30 min) |
| `AvaliarAutoEncerramento(ultimoInput=18:02, agora=19:05, h_fim=18:00)` | `FecharPendente(FIM_JORNADA=18:02)` (inatividade ≥ 60min pós-fim, jornada PENDENTE, sem atividade) |
| `AvaliarAutoEncerramento(ultimoInput=18:02, agora=18:40, h_fim=18:00)` | `NenhumaAcao` (apenas 38min de inatividade) |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`Timesheet.Agent.Tests/Domain/JourneyStateMachineTests.cs`):

```csharp
private static HorariosJornada Horarios() => new(
    Inicio: new TimeOnly(9,0), SaidaAlmoco: new TimeOnly(12,0),
    RetornoAlmoco: new TimeOnly(13,0), Fim: new TimeOnly(18,0));

private static DateTimeOffset At(int h, int m) =>
    new(2026, 5, 27, h, m, 0, TimeSpan.FromHours(-3)); // quarta-feira, BRT

[Fact]
public void Login_dentro_da_janela_registra_automatico_sem_dialogo()
{
    var d = JourneyStateMachine.AvaliarLogin(At(9,2), Horarios(), ehFimDeSemana: false, trabalhaFds: false);
    d.Should().BeOfType<RegistrarAutomatico>();
    var r = (RegistrarAutomatico)d;
    r.Tipo.Should().Be(MarcacaoTipo.InicioJornada);
    r.Horario.Should().Be(At(9,2));
    r.Origem.Should().Be(OrigemMarcacao.AgenteAutomatico);
}

[Fact]
public void Login_em_atraso_registra_e_emite_toast_de_atraso()
{
    var d = JourneyStateMachine.AvaliarLogin(At(9,45), Horarios(), false, false);
    var r = d.Should().BeOfType<RegistrarAutomatico>().Subject;
    r.Horario.Should().Be(At(9,45));
    r.AtrasoMinutos.Should().Be(45);
}

[Fact]
public void Login_antecipado_exige_dialogo_com_fallback_h_ini()
{
    var d = JourneyStateMachine.AvaliarLogin(At(6,45), Horarios(), false, false);
    var dlg = d.Should().BeOfType<ExigeDialogo>().Subject;
    dlg.Kind.Should().Be("CONFIRM_INICIO_ANTECIPADO");
    dlg.HorarioProposto.Should().Be(At(6,45));
    dlg.Fallback.Should().Be(At(9,0));
}

[Fact]
public void ResolverInicioAntecipado_timeout_usa_h_ini()
{
    var r = JourneyStateMachine.ResolverInicioAntecipado("TIMEOUT", At(6,45), At(9,0));
    r.Horario.Should().Be(At(9,0));
    r.Origem.Should().Be(OrigemMarcacao.AgenteConfirmado);
}

[Fact]
public void Login_em_fim_de_semana_sem_trabalho_nao_registra()
{
    JourneyStateMachine.AvaliarLogin(At(10,0), Horarios(), ehFimDeSemana: true, trabalhaFds: false)
        .Should().BeOfType<NenhumaAcao>();
}

[Fact]
public void Inatividade_na_janela_de_almoco_registra_saida()
{
    var d = JourneyStateMachine.AvaliarInatividade(inicioInatividade: At(12,5), duracaoMin: 13, Horarios());
    var r = d.Should().BeOfType<RegistrarAutomatico>().Subject;
    r.Tipo.Should().Be(MarcacaoTipo.SaidaAlmoco);
    r.Horario.Should().Be(At(12,5));
}

[Fact]
public void Inatividade_fora_da_janela_nao_registra()
{
    JourneyStateMachine.AvaliarInatividade(At(15,0), 13, Horarios()).Should().BeOfType<NenhumaAcao>();
}

[Fact]
public void Inatividade_menor_que_10min_nao_registra()
{
    JourneyStateMachine.AvaliarInatividade(At(12,5), 8, Horarios()).Should().BeOfType<NenhumaAcao>();
}

[Fact]
public void Retorno_dentro_da_janela_registra_automatico()
{
    JourneyStateMachine.AvaliarRetorno(At(13,10), Horarios())
        .Should().BeOfType<RegistrarAutomatico>()
        .Which.Horario.Should().Be(At(13,10));
}

[Fact]
public void Retorno_fora_da_janela_exige_dialogo()
{
    JourneyStateMachine.AvaliarRetorno(At(14,30), Horarios())
        .Should().BeOfType<ExigeDialogo>()
        .Which.Kind.Should().Be("CONFIRM_RETORNO_FORA_JANELA");
}

[Fact]
public void Retorno_negado_gera_marcacao_pendente()
{
    JourneyStateMachine.ResolverRetornoForaJanela("NAO", At(14,30))
        .Should().BeOfType<RegistrarPendente>()
        .Which.Tipo.Should().Be(MarcacaoTipo.RetornoAlmoco);
}

[Fact]
public void Fim_com_sim_e_atividade_fecha_jornada()
{
    var r = JourneyStateMachine.ResolverFim("SIM", "Desenvolvi a feature X", At(18,5))
        .Should().BeOfType<Fechar>().Subject;
    r.Horario.Should().Be(At(18,5));
    r.Atividade.Should().Be("Desenvolvi a feature X");
}

[Fact]
public void Fim_timeout_reagenda_em_30min()
{
    JourneyStateMachine.ResolverFim("TIMEOUT", null, At(18,0))
        .Should().BeOfType<Relembrar>()
        .Which.Em.Should().Be(At(18,30));
}

[Fact]
public void AutoEncerramento_apos_60min_inatividade_fecha_pendente()
{
    var r = JourneyStateMachine.AvaliarAutoEncerramento(ultimoInput: At(18,2), agora: At(19,5), Horarios())
        .Should().BeOfType<FecharPendente>().Subject;
    r.Horario.Should().Be(At(18,2));
}

[Fact]
public void AutoEncerramento_antes_de_60min_nao_age()
{
    JourneyStateMachine.AvaliarAutoEncerramento(At(18,2), At(18,40), Horarios())
        .Should().BeOfType<NenhumaAcao>();
}
```

**Refatoração:** após green, extrair o cálculo de janela `[h−30, h+30]` para um helper privado `JanelaTolerancia(TimeOnly, DateOnly)` reutilizado pelos 3 avaliadores; consolidar a constante de 30min/10min/60min em `static class RegrasJornada`.

## O que Implementar

Decisões como hierarquia de records (`abstract record DecisaoJornada`) — a máquina é `static class` de funções puras (sem estado interno; estado vive em `EstadoJornadaAtual` persistido pelo host).

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/agent/src/Timesheet.Agent.Domain/HorariosJornada.cs` | Criar | Record `HorariosJornada(TimeOnly Inicio, SaidaAlmoco, RetornoAlmoco, Fim)` |
| `apps/agent/src/Timesheet.Agent.Domain/DecisaoJornada.cs` | Criar | `abstract record DecisaoJornada` + `NenhumaAcao`, `RegistrarAutomatico`, `RegistrarConfirmado`, `RegistrarPendente`, `ExigeDialogo`, `Fechar`, `FecharPendente`, `Relembrar` |
| `apps/agent/src/Timesheet.Agent.Domain/JourneyStateMachine.cs` | Criar | `static class` com `AvaliarLogin`, `ResolverInicioAntecipado`, `AvaliarInatividade`, `AvaliarRetorno`, `ResolverRetornoForaJanela`, `AvaliarFim`, `ResolverFim`, `AvaliarAutoEncerramento` |
| `apps/agent/src/Timesheet.Agent.Domain/RegrasJornada.cs` | Criar | Constantes: `ToleranciaMin=30`, `InatividadeAlmocoMin=10`, `AutoEncerramentoMin=60`, `ReprompFimMin=30`, `MinCharsAtividade=10` |

### Detalhamento Técnico

1. **`DecisaoJornada`** — records de saída. `RegistrarAutomatico` carrega `int? AtrasoMinutos` (não-nulo apenas quando há atraso, dispara toast). `ExigeDialogo` carrega `Kind`, `HorarioProposto`, `DateTimeOffset? Fallback`. `Fechar` carrega `Horario` + `Atividade`. `Relembrar` carrega `Em`.

```csharp
public abstract record DecisaoJornada;
public sealed record NenhumaAcao : DecisaoJornada;
public sealed record RegistrarAutomatico(string Tipo, DateTimeOffset Horario, string Origem, int? AtrasoMinutos = null) : DecisaoJornada;
public sealed record RegistrarConfirmado(string Tipo, DateTimeOffset Horario, string Origem) : DecisaoJornada;
public sealed record RegistrarPendente(string Tipo, DateTimeOffset Horario) : DecisaoJornada;
public sealed record ExigeDialogo(string Kind, DateTimeOffset HorarioProposto, DateTimeOffset? Fallback = null) : DecisaoJornada;
public sealed record Fechar(string Tipo, DateTimeOffset Horario, string Atividade) : DecisaoJornada;
public sealed record FecharPendente(string Tipo, DateTimeOffset Horario) : DecisaoJornada;
public sealed record Relembrar(DateTimeOffset Em) : DecisaoJornada;
```

2. **Janela de tolerância** — para um `TimeOnly h` no dia de `T`, calcular `inicio = T.Date + h − 30min`, `fim = T.Date + h + 30min`; "dentro" = `inicio ≤ T ≤ fim`. Para inatividade (RF-004), a *janela da inatividade* `[inicioInat, inicioInat+duracao]` deve **intersectar** `[h_alm_saida−30, h_alm_saida+30]` (não exigir que o ponto inicial esteja dentro): interseção quando `inicioInat ≤ janelaFim && (inicioInat+duracao) ≥ janelaInicio`.

3. **`AvaliarLogin`** — ordem: se `ehFimDeSemana && !trabalhaFds` → `NenhumaAcao`. Senão computar diferença `T − h_ini`: `|diff| ≤ 30min` → `RegistrarAutomatico(..., AtrasoMinutos: null)`. `diff > 30min` (atraso) → `RegistrarAutomatico(..., AtrasoMinutos: (int)diff.TotalMinutes)`. `diff < −30min` (antecipação) → `ExigeDialogo("CONFIRM_INICIO_ANTECIPADO", T, fallback: h_ini_as_DateTimeOffset)`.

4. **`ResolverInicioAntecipado(answer, T, hIni)`** → `RegistrarConfirmado(INICIO_JORNADA, answer=="SIM" ? T : hIni, AGENTE_CONFIRMADO)`. `NAO`/`TIMEOUT` usam `hIni`.

5. **`AvaliarInatividade(inicioInatividade, duracaoMin, horarios)`** → se `duracaoMin < 10` → `NenhumaAcao`; senão se interseção com janela de almoço → `RegistrarAutomatico(SAIDA_ALMOCO, inicioInatividade, AGENTE_AUTOMATICO)`; senão `NenhumaAcao`.

6. **`AvaliarRetorno(T, horarios)`** → dentro de `[ret−30, ret+30]` → `RegistrarAutomatico(RETORNO_ALMOCO, T, AGENTE_AUTOMATICO)`; fora → `ExigeDialogo("CONFIRM_RETORNO_FORA_JANELA", T)`. `ResolverRetornoForaJanela(answer, T)` → `SIM` → `RegistrarConfirmado(RETORNO_ALMOCO, T, AGENTE_CONFIRMADO)`; `NAO`/`TIMEOUT` → `RegistrarPendente(RETORNO_ALMOCO, T)`.

7. **`AvaliarFim(T, horarios)`** → quando `T ≥ h_fim` → `ExigeDialogo("PROMPT_FIM_JORNADA", h_fim_as_offset_no_dia)`. `ResolverFim(answer, atividade, T)` → `SIM` (atividade ≥ 10 chars) → `Fechar(FIM_JORNADA, T, atividade)`; `NAO`/`TIMEOUT` → `Relembrar(T + 30min)`. Se `SIM` mas atividade < 10 chars → lançar `ArgumentException` (a UI já bloqueia, mas a máquina valida defensivamente — testar com FluentAssertions `Throw`).

8. **`AvaliarAutoEncerramento(ultimoInput, agora, horarios)`** → se `agora ≥ h_fim_no_dia` E `(agora − ultimoInput) ≥ 60min` → `FecharPendente(FIM_JORNADA, ultimoInput)`; senão `NenhumaAcao`.

**Refatoração:** "Nenhuma além de extrair helpers de janela/constantes citados acima."

**Contrato com camadas adjacentes:**

```
Produz para: Service host (TASK-033)
  - DecisaoJornada (records): o host traduz cada decisão em efeito —
    RegistrarAutomatico/Confirmado/Pendente ⇒ MarcacaoLocalRepository.EnqueueAsync + atualizar EstadoJornadaAtual;
    ExigeDialogo ⇒ enviar DialogRequest via IPC e aguardar DialogResponse;
    Fechar/FecharPendente ⇒ enfileirar FIM_JORNADA + (atividade não vai ao Agente: atividade é enviada pela Web; o Agente só marca FIM);
    Relembrar ⇒ reagendar prompt.
Consome de: Fundação (TASK-028) — MarcacaoTipo, OrigemMarcacao, EstadoJornada (constantes); IClock não é injetado aqui (funções recebem o instante T explicitamente para máxima testabilidade).
```

> Nota: a atividade (≥10 chars) capturada no `PROMPT_FIM_JORNADA` fica fora do contrato `POST /api/v1/marcacoes` (que não tem campo atividade). O host registra apenas a marcação FIM_JORNADA; a persistência da atividade na jornada é responsabilidade da Web (`POST /jornadas/{id}/atividade`) — o Agente captura mas não a sincroniza na v1.0 (a Spec §4 mostra o Agente enviando só marcações). Documentar essa fronteira no host (TASK-033).
