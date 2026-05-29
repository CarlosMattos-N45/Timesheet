---
checkpoint: null
complexity: G
created_at: "2026-05-29 09:33:12"
criteria:
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Cnpj_validates_check_digits
      text: CnpjValidator valida digitos verificadores modulo 11, rejeita repetidos e comprimento != 14
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Cnpj_OnlyDigits_strips_mask
      text: CnpjValidator.OnlyDigits remove a mascara
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Horarios_fora_de_ordem_falham
      text: HorariosValidator aceita ordem cronologica e rejeita fora de ordem
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Password_curta_e_fraca
      text: PasswordStrength classifica <8 chars como Fraca e senha longa mista como nao-Fraca
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Wizard_passo3_invalido_quando_senhas_diferem
      text: WizardViewModel.Passo1Valido false com CNPJ ruim; Passo3Valido false com senhas diferentes
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Wizard_monta_request_com_cnpj_sem_mascara_e_horarios_formatados
      text: WizardViewModel.MontarRequest produz CreateTerceiroDto com CNPJ sem mascara e horarios HH:MM:SS
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Saudacao_por_faixa_horaria
      text: Saudacao.Para retorna Bom dia (0-11)/Boa tarde (12-17)/Boa noite (18-23)
    - done: false
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~DialogViewModel_timeout_resolve_com_TIMEOUT
      text: DialogViewModel sem interacao expira e resolve com Answer=TIMEOUT preservando o Id
    - done: false
      test: cd apps/agent && dotnet build Timesheet.Agent.sln -c Debug
      text: Solution compila (agent-build) e testes de Ui passam
    - done: false
      text: Cobertura dos validadores+ViewModels (excluindo XAML/NotifyIcon) >= 70%
deps:
    - TASK-029
    - TASK-032
id: TASK-034
linter: cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes
n45_version: 0.2.0
persona: frontend
phase: Phase 5 — Agente Desktop
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: cd apps/agent && dotnet test Timesheet.Agent.sln -c Debug --filter FullyQualifiedName~Ui
title: 'WPF UI: wizard de cadastro (RF-002, CNPJ módulo 11 + horários cronológicos), diálogos modais 60s (RF-003/005/006), toast saudação (RF-001), tray NotifyIcon, IpcClient + onboarding via BackendClient'
updated_at: "2026-05-29 09:33:12"
---
## Contexto

Esta task implementa a **UI WPF do Agente** (`Timesheet.Agent.Ui`): o processo de interface que roda na sessão do usuário, com tray icon (`NotifyIcon` WinForms), o wizard de cadastro inicial (RF-002), os diálogos modais com progress bar de 60s (RF-003 antecipação, RF-005 retorno fora de janela, RF-006 fim + atividade) e o toast de saudação (RF-001). A UI conecta ao Service via `IpcClient` (named pipe, TASK-032) e ao Backend via `IBackendClient` (TASK-029) apenas no onboarding (criar Terceiro + login).

Hoje `App.xaml.cs` é um shell vazio. O scaffold já tem `UseWPF=true` + `UseWindowsForms=true` (para `NotifyIcon`) e referencia Domain + Ipc; adicionar referência a Infra.Http para o onboarding.

Fluxo (Spec §5 "Tela do Agente Desktop" + "Onboarding"):
1. Ao iniciar, a UI verifica se o Terceiro já existe (cadastro local presente em `ConfiguracaoLocal` ou `POST /terceiros` devolve 403 SETUP_ALREADY_DONE). Se não → abre o **wizard 3 passos**; se sim → ativa tray e abre browser em `http://127.0.0.1:8765/login`.
2. Wizard passo 1 (nome, empresa, CNPJ com máscara + validação dígitos módulo 11 em tempo real), passo 2 (4 TimePickers cronológicos + toggle fim de semana), passo 3 (e-mail, senha ≥8 + indicador de força, confirmar, e-mail destinatário opcional). Finalizar → `POST /api/v1/terceiros` (201) → login → persiste tokens (via TokenManager/DPAPI) e os 4 horários em `ConfiguracaoLocal` → fecha wizard → tray ativo → abre browser.
3. Diálogos: a UI assina `IpcClient.OnMessage`; ao receber `DialogRequest`, abre o modal correspondente com progress bar 60s; responde `DialogResponse(Id, "SIM"|"NAO"|"TIMEOUT", payload)`. Ao receber `ToastMessage`, exibe notificação nativa (10s). Ao receber `StatusPush`, atualiza badge do tray (pendentes) e tooltip.

A lógica visual WPF (XAML, code-behind, NotifyIcon) **não** entra na meta de cobertura (quality gate exclui UI WPF — Spec §7/§9). O que é **testável e deve ser TDD'd** vive em ViewModels/validadores puros: validação de CNPJ módulo 11 client-side (constraint da Spec — também no Agente), validação cronológica dos 4 horários, força de senha, e o `WizardViewModel` (avançar habilitado só com passo válido). Esses ficam em classes sem dependência de `System.Windows`.

Dependências: TASK-029 (`IBackendClient`, `TokenManager`, `CreateTerceiroDto`, `AuthException`), TASK-032 (`IpcClient`, `DialogRequest`/`DialogResponse`/`ToastMessage`/`StatusPush`), TASK-028 (`MarcacaoTipo` constantes — não usadas direto aqui; `ConfiguracaoLocalRepository` para persistir horários).

## Comportamento Esperado

Os validadores e o `WizardViewModel` são o alvo de teste.

**Exemplos (entrada → saída esperada)** — valores reais:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `CnpjValidator.IsValid("11222333000181")` | `true` (dígitos verificadores corretos) |
| `CnpjValidator.IsValid("11222333000180")` | `false` (DV incorreto) |
| `CnpjValidator.IsValid("11111111111111")` | `false` (todos iguais — rejeitado) |
| `CnpjValidator.IsValid("112223330001")` | `false` (≠ 14 dígitos) |
| `CnpjValidator.OnlyDigits("11.222.333/0001-81")` | `"11222333000181"` (remove máscara) |
| `HorariosValidator.SaoCronologicos(09:00,12:00,13:00,18:00)` | `true` |
| `HorariosValidator.SaoCronologicos(09:00,13:00,12:00,18:00)` | `false` (saída_almoço ≥ retorno) |
| `PasswordStrength.Avaliar("Senha123")` | `Forte`/`Media` (≥8 chars, mistura) — enum não-`Fraca` |
| `PasswordStrength.Avaliar("123")` | `Fraca` (< 8 chars) |
| `WizardViewModel.Passo1Valido` com nome="Maria", empresa="ACME", cnpj válido | `true` |
| `WizardViewModel.Passo1Valido` com CNPJ inválido | `false` (bloqueia "Avançar") |
| `WizardViewModel.Passo3Valido` com senha≠confirmação | `false` |
| `WizardViewModel.MontarRequest()` (todos passos válidos) | `CreateTerceiroDto` com cnpj sem máscara, horários `HH:MM:SS`, `senha==senha_confirmacao` |
| `DialogViewModel.SegundosRestantes` decrementa de 60→0 | ao chegar a 0 → `Answer=="TIMEOUT"` (equivalente a NÃO/PENDENTE) |
| `Saudacao.Para(8)` | `"Bom dia"`; `Saudacao.Para(14)` → `"Boa tarde"`; `Saudacao.Para(20)` → `"Boa noite"` |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`Timesheet.Agent.Tests/Ui/`):

```csharp
[Theory]
[InlineData("11222333000181", true)]
[InlineData("11222333000180", false)]
[InlineData("11111111111111", false)]
[InlineData("112223330001", false)]
public void Cnpj_validates_check_digits(string cnpj, bool expected)
    => CnpjValidator.IsValid(cnpj).Should().Be(expected);

[Fact]
public void Cnpj_OnlyDigits_strips_mask()
    => CnpjValidator.OnlyDigits("11.222.333/0001-81").Should().Be("11222333000181");

[Fact]
public void Horarios_cronologicos_ok()
    => HorariosValidator.SaoCronologicos(new(9,0), new(12,0), new(13,0), new(18,0)).Should().BeTrue();

[Fact]
public void Horarios_fora_de_ordem_falham()
    => HorariosValidator.SaoCronologicos(new(9,0), new(13,0), new(12,0), new(18,0)).Should().BeFalse();

[Fact]
public void Password_curta_e_fraca()
    => PasswordStrength.Avaliar("123").Should().Be(ForcaSenha.Fraca);

[Fact]
public void Password_longa_mista_nao_e_fraca()
    => PasswordStrength.Avaliar("Senha123").Should().NotBe(ForcaSenha.Fraca);

[Fact]
public void Wizard_passo1_invalido_com_cnpj_ruim()
{
    var vm = new WizardViewModel { Nome = "Maria", Empresa = "ACME", Cnpj = "11222333000180" };
    vm.Passo1Valido.Should().BeFalse();
}

[Fact]
public void Wizard_passo3_invalido_quando_senhas_diferem()
{
    var vm = new WizardViewModel { Email = "m@x.com", Senha = "Senha123", SenhaConfirmacao = "Outra123" };
    vm.Passo3Valido.Should().BeFalse();
}

[Fact]
public void Wizard_monta_request_com_cnpj_sem_mascara_e_horarios_formatados()
{
    var vm = new WizardViewModel
    {
        Nome = "Maria Silva", Empresa = "ACME LTDA", Cnpj = "11.222.333/0001-81",
        Inicio = new(9,0), SaidaAlmoco = new(12,0), RetornoAlmoco = new(13,0), Fim = new(18,0),
        TrabalhaFds = false, Email = "maria@x.com", Senha = "Senha123",
        SenhaConfirmacao = "Senha123", EmailDestinatario = "rh@empresa.com",
    };
    var dto = vm.MontarRequest();
    dto.EmpresaCnpj.Should().Be("11222333000181");
    dto.HorarioInicioJornada.Should().Be("09:00:00");
    dto.HorarioFimJornada.Should().Be("18:00:00");
    dto.Senha.Should().Be(dto.SenhaConfirmacao);
}

[Fact]
public void Saudacao_por_faixa_horaria()
{
    Saudacao.Para(8).Should().Be("Bom dia");
    Saudacao.Para(14).Should().Be("Boa tarde");
    Saudacao.Para(20).Should().Be("Boa noite");
}

[Fact]
public async Task DialogViewModel_timeout_resolve_com_TIMEOUT()
{
    var vm = new DialogViewModel(id: "d1", kind: "PROMPT_FIM_JORNADA", segundos: 1);
    var resp = await vm.AguardarRespostaAsync(); // sem interação → expira
    resp.Answer.Should().Be("TIMEOUT");
    resp.Id.Should().Be("d1");
}
```

**Refatoração:** após green, reusar `CnpjValidator` se já houver lógica equivalente; consolidar máscara/parse de `TimeOnly→"HH:MM:SS"` num formatter único.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/agent/src/Timesheet.Agent.Ui/Validation/CnpjValidator.cs` | Criar | `IsValid(string)` (módulo 11, rejeita repetidos e ≠14) + `OnlyDigits(string)` |
| `apps/agent/src/Timesheet.Agent.Ui/Validation/HorariosValidator.cs` | Criar | `SaoCronologicos(TimeOnly,TimeOnly,TimeOnly,TimeOnly)` |
| `apps/agent/src/Timesheet.Agent.Ui/Validation/PasswordStrength.cs` | Criar | `enum ForcaSenha { Fraca, Media, Forte }` + `Avaliar(string)` |
| `apps/agent/src/Timesheet.Agent.Ui/Common/Saudacao.cs` | Criar | `Para(int hora)` → "Bom dia/Boa tarde/Boa noite" (faixas 0–11/12–17/18–23) |
| `apps/agent/src/Timesheet.Agent.Ui/ViewModels/WizardViewModel.cs` | Criar | Propriedades dos 3 passos + `Passo1/2/3Valido` + `MontarRequest()→CreateTerceiroDto` |
| `apps/agent/src/Timesheet.Agent.Ui/ViewModels/DialogViewModel.cs` | Criar | `SegundosRestantes`, `AguardarRespostaAsync()` (timeout→TIMEOUT), `Responder(answer, payload)` |
| `apps/agent/src/Timesheet.Agent.Ui/Views/WizardWindow.xaml(.cs)` | Criar | Janela WPF do wizard 3 passos (binda WizardViewModel) |
| `apps/agent/src/Timesheet.Agent.Ui/Views/DialogWindow.xaml(.cs)` | Criar | Modal com progress bar 60s + (para PROMPT_FIM) textarea atividade ≥10 chars |
| `apps/agent/src/Timesheet.Agent.Ui/TrayIcon.cs` | Criar | `NotifyIcon` WinForms: ícone, badge de pendentes, menu (Abrir Web / Sair), toast nativo |
| `apps/agent/src/Timesheet.Agent.Ui/App.xaml(.cs)` | Modificar | Startup: decide onboarding vs tray; cria `IpcClient` (NamedPipeChannel cliente); roteia `OnMessage` para abrir Dialog/Toast/StatusPush; onboarding chama `IBackendClient` |
| `apps/agent/src/Timesheet.Agent.Ui/Timesheet.Agent.Ui.csproj` | Modificar | Add ProjectReference para `Infra.Http` e `Infra.Db`; `Hardcodet.NotifyIcon.Wpf`? Não — usar `System.Windows.Forms.NotifyIcon` (já habilitado via UseWindowsForms) |

### Detalhamento Técnico

1. **`CnpjValidator.IsValid`** — algoritmo módulo 11 (constraint Spec §7, mesma regra do backend `stdnum.br.cnpj` e do Web): `OnlyDigits`; rejeita se `len != 14` ou todos os dígitos iguais; calcula DV1 com pesos `[5,4,3,2,9,8,7,6,5,4,3,2]` e DV2 com `[6,5,4,3,2,9,8,7,6,5,4,3,2]`; compara com os 2 últimos dígitos.

```csharp
public static bool IsValid(string raw)
{
    var s = OnlyDigits(raw);
    if (s.Length != 14 || s.Distinct().Count() == 1) return false;
    int Dv(int len, int[] pesos)
    {
        int sum = 0;
        for (int i = 0; i < len; i++) sum += (s[i] - '0') * pesos[i];
        int r = sum % 11;
        return r < 2 ? 0 : 11 - r;
    }
    var d1 = Dv(12, new[]{5,4,3,2,9,8,7,6,5,4,3,2});
    var d2 = Dv(13, new[]{6,5,4,3,2,9,8,7,6,5,4,3,2});
    return d1 == s[12]-'0' && d2 == s[13]-'0';
}
public static string OnlyDigits(string raw) => new(raw.Where(char.IsDigit).ToArray());
```

2. **`WizardViewModel`** — POCO com `INotifyPropertyChanged` opcional (não exigido para o teste). `Passo1Valido` = `!string.IsNullOrWhiteSpace(Nome) && !string.IsNullOrWhiteSpace(Empresa) && CnpjValidator.IsValid(Cnpj)`. `Passo2Valido` = `HorariosValidator.SaoCronologicos(...)`. `Passo3Valido` = email não-vazio && `PasswordStrength.Avaliar(Senha) != Fraca` && `Senha == SenhaConfirmacao`. `MontarRequest()` → `CreateTerceiroDto` (record de TASK-029) com `EmpresaCnpj = CnpjValidator.OnlyDigits(Cnpj)`, horários formatados `t.ToString("HH:mm:ss")`, `EmailDestinatarioRelatorio` nullable.

   > Usar exatamente o `CreateTerceiroDto` produzido por TASK-029. Se os nomes de propriedade lá diferirem, alinhar ao real (consumidor segue o contrato real).

3. **`DialogViewModel`** — `AguardarRespostaAsync()`: `TaskCompletionSource<DialogResponse>`; um timer de 1s decrementa `SegundosRestantes` (binda na progress bar); ao chegar a 0 sem `Responder` → `TrySetResult(new DialogResponse(Id, "TIMEOUT"))`. `Responder(answer, payload)` → `TrySetResult(new DialogResponse(Id, answer, payload))`. Para `PROMPT_FIM_JORNADA`, o botão "Salvar e encerrar" só habilita com atividade ≥ 10 chars; ao confirmar, `payload["atividade"]` carrega o texto.

4. **`App.xaml.cs` startup** — `OnStartup`: instancia `NamedPipeChannel` cliente + `IpcClient`; decide onboarding (consultar `ConfiguracaoLocalRepository.GetAsync()` ou tentar `CreateTerceiroAsync` que devolve 403 se já feito). Onboarding concluído → persistir os 4 horários e tokens em `ConfiguracaoLocal`, `TrayIcon.Show()`, `Process.Start(new ProcessStartInfo("http://127.0.0.1:8765/login"){UseShellExecute=true})`. `IpcClient.OnMessage`: `DialogRequest`→abre `DialogWindow`, ao resolver `await vm.AguardarRespostaAsync()` → `ipcClient.SendAsync(response)`; `ToastMessage`→`TrayIcon.ShowBalloon(title, body, 10s)`; `StatusPush`→`TrayIcon.SetBadge(pendentesCount)`.

5. **TrayIcon** — `System.Windows.Forms.NotifyIcon`; badge vermelho quando cadastro incompleto (Spec RF-002) ou quando há pendentes; `ShowBalloonTip(10000, title, body, ToolTipIcon.Info)` para o toast nativo (auto-fecha ~10s). Menu de contexto: "Abrir Timesheet" (browser), "Sair".

> Cobertura: validadores, `WizardViewModel`, `DialogViewModel`, `Saudacao` são cobertos por testes. `WizardWindow`/`DialogWindow`/`App`/`TrayIcon` (XAML + WinForms + Process.Start) são UI WPF/WinForms — **fora** da meta de cobertura (Spec §9: cobertura mede Domain+Infra, excluindo UI WPF).

**Contrato com camadas adjacentes:**

```
Consome de: TASK-029 — IBackendClient.CreateTerceiroAsync (201 / 403 SETUP_ALREADY_DONE / 422 VALIDATION_ERROR com details[].field) + LoginAsync; CreateTerceiroDto (body real); TokenManager (persistir tokens DPAPI)
Consome de: TASK-032 — IpcClient.OnMessage(IpcMessage) e SendAsync(DialogResponse); records DialogRequest/DialogResponse/ToastMessage/StatusPush
Consome de: TASK-028 — ConfiguracaoLocalRepository (persistir 4 horários + base url); IpcMessage records
Contrato de validação client-side (Spec §7): CNPJ módulo 11 + horários cronológicos + senha ≥8 — espelha as validações server-side do backend (apps/api), bloqueando avanço no wizard antes do POST
```
