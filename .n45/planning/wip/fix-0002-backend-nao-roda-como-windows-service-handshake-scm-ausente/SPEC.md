---
created_at: "2026-06-02 12:40:29"
id: fix-0002-backend-nao-roda-como-windows-service-handshake-scm-ausente
n45_version: 0.2.0
status: accepted
title: Backend faz handshake SCM como Windows Service
type: fix
updated_at: "2026-06-02 16:46:09"
---
## 1. Problema

**Goal:** Tornar `timesheet-backend.exe` capaz de fazer o handshake do Windows Service Control Manager (SCM) quando iniciado como serviço, preservando o modo console atual.

**Background:** A instalação de produção via MSI (`dist\TimesheetTerceiros.msi`) falha no passo `StartServices` com o diálogo _"Serviço 'Timesheet Backend' (TimesheetBackend) não iniciado. Verifique se você tem privilégios suficientes para iniciar os serviços do sistema."_ O `Components.wxs` registra `timesheet-backend.exe` diretamente como serviço nativo (`Type="ownProcess"`, `Account="LocalSystem"`, `ServiceControl Start="install" Wait="yes"`). O processo inicia, sobe o uvicorn e serve HTTP (segura a :8765, responde `/api/v1/health` 200 quando rodado no console), mas nunca reporta `SERVICE_RUNNING` ao SCM → o SCM atinge timeout → `StartServices` falha → diálogo de erro. No rollback, o registro do serviço é removido mas o processo fica órfão (LocalSystem) segurando a :8765.

**Comportamento atual (As Is):** `apps/api/app/launcher.py` é um entrypoint de console puro: `main()` executa `configure_logging → prepare_runtime → run_migrations → serve()`, e `serve()` chama `uvicorn.run(...)` (bloqueante). Não existe nenhuma implementação do protocolo de Windows Service (`win32serviceutil.ServiceFramework` / `servicemanager` / `StartServiceCtrlDispatcher`) em todo o `apps/api` (busca confirmou ausência). Binário não-service-aware registrado como serviço nativo = SCM nunca recebe `RUNNING` e mata o start por timeout.

**Comportamento esperado (To Be):** Quando iniciado pelo SCM como Windows Service, `timesheet-backend.exe` faz o handshake correto: reporta `SERVICE_START_PENDING` → executa o bootstrap (`prepare_runtime`/`run_migrations`) e sobe o uvicorn numa thread → reporta `SERVICE_RUNNING`; ao receber STOP, encerra o uvicorn graciosamente e reporta `SERVICE_STOPPED`. A instalação do MSI conclui sem erro, com `TimesheetBackend` em estado `RUNNING` e `/api/v1/ready` respondendo 200. Executar o exe sem contexto de SCM (console/dev) continua funcionando exatamente como hoje (`main()`).

**Impacto:** Bloqueador total de produção — o produto não instala. Severidade crítica, 100% das instalações via MSI afetadas.

## 2. Diagnóstico

**Causa raiz:** `apps/api/app/launcher.py:111-124` (`serve()`) e `:127-139` (`main()`) implementam apenas o ciclo de vida de console (uvicorn bloqueante). Não há nenhuma classe `ServiceFramework`, nem dispatcher (`servicemanager.StartServiceCtrlDispatcher` / `win32serviceutil.HandleCommandLine`), nem reporte de estado (`ReportServiceStatus`). O SCM inicia o processo e espera o handshake do protocolo de serviço, que nunca chega. Adicionalmente, o `timesheet-backend.spec` não declara os módulos do pywin32 service (`win32serviceutil`, `win32service`, `win32event`, `servicemanager`) como hidden imports — sem eles, o modo serviço quebraria no bundle congelado mesmo após implementado.

**Decisão de ativação do modo serviço:** o serviço é registrado pelo MSI passando o argumento explícito `service` no binPath (`Arguments=" service"` no `ServiceInstall`). `launcher.main()` passa a inspecionar `sys.argv`: `argv[1] == "service"` → modo serviço (dispatcher); qualquer outro caso → modo console (comportamento atual). Justificativa em §8.

**Arquivos impactados:**

| Arquivo | O que está errado |
| ------- | ----------------- |
| `apps/api/app/launcher.py` | Entrypoint só de console; sem `ServiceFramework`, dispatcher nem reporte de estado ao SCM. |
| `apps/api/app/launcher.py` (`serve()`) | `uvicorn.run(...)` é bloqueante e não expõe handle para shutdown gracioso a partir do callback de STOP do serviço. |
| `apps/api/timesheet-backend.spec` | Faltam os hidden imports do pywin32 service (`win32serviceutil`, `win32service`, `win32event`, `servicemanager`, `win32api`). |
| `apps/installer/Components.wxs` | `ServiceInstall` do `TimesheetBackend` não passa o argumento `service` no binPath que ativa o modo serviço. |
| `apps/api/tests/test_launcher.py` | Sem teste cobrindo a seleção de modo (console vs serviço) nem o ciclo de vida do serviço. |

## 3. Estratégia de Correção

Um `RF-NN` por correção verificável, na ordem de aplicação.

- **RF-01** — Em `apps/api/app/launcher.py`, refatorar `serve()` para suportar shutdown programático. Construir explicitamente um `uvicorn.Server(uvicorn.Config(create_app(), host=settings.host, port=settings.port, workers=1, log_config=None))` e expor o objeto `Server`. Adicionar uma função `run_server(server: uvicorn.Server) -> None` que chama `server.run()` (bloqueante, como hoje) e mantém `serve()` como wrapper que cria o `Server` e chama `run_server` — o modo console permanece idêntico em comportamento. O sinal de parada usa `server.should_exit = True` (mecanismo nativo do uvicorn para encerramento gracioso sem sinais do SO).

- **RF-02** — Em `apps/api/app/launcher.py`, adicionar a classe de serviço Windows guardada por import condicional de plataforma (sem quebrar import em Linux/CI não-Windows: o `import win32serviceutil` etc. fica dentro de função/bloco `try` ou guardado por `sys.platform == "win32"`). A classe `TimesheetBackendService(win32serviceutil.ServiceFramework)` deve:
  - `_svc_name_ = "TimesheetBackend"`, `_svc_display_name_ = "Timesheet Backend"`.
  - No `SvcDoRun`: logar `event="service_start_pending", svc_name="TimesheetBackend"` → `ReportServiceStatus(SERVICE_START_PENDING)` → `configure_logging()` → `prepare_runtime(settings)` → `run_migrations()` → criar o `uvicorn.Server` (RF-01) → iniciar `server.run()` numa thread daemon → aguardar `server.started` com timeout de **30 s** antes de reportar falha ao SCM → logar `event="service_running", svc_name="TimesheetBackend"` → `ReportServiceStatus(SERVICE_RUNNING)` → bloquear em `win32event.WaitForSingleObject(self._stop_event, INFINITE)`.
  - No `SvcStop`: logar `event="service_stop_pending", svc_name="TimesheetBackend"` → `ReportServiceStatus(SERVICE_STOP_PENDING)` → `server.should_exit = True` → `SetEvent(self._stop_event)` → join da thread uvicorn com timeout de **10 s**. Se o join expirar, logar `event="service_stop_timeout", svc_name="TimesheetBackend"` (nível `WARNING`) e retornar — o SCM escalará para `TerminateProcess`. Caso contrário logar `event="service_stopped", svc_name="TimesheetBackend"`. O `ServiceFramework` reporta `SERVICE_STOPPED` no retorno de `SvcDoRun`.
  - Qualquer exceção no bootstrap é logada com `logger.exception` (nível `ERROR`, campo `event="service_bootstrap_error"`, `svc_name="TimesheetBackend"`) seguido de `servicemanager.LogErrorMsg` com apenas o **tipo da exceção e a camada onde ocorreu** — nunca `str(exc)` direto quando o contexto pode conter `PRAGMA key`, connection strings com credenciais ou DPAPI blobs. Após logar, reportar stop ao SCM (em vez de travar em `START_PENDING`).
  - **Restrição de bootstrap antes do dispatcher:** no path `argv[1] == "service"` de `main()`, nenhum código privilegiado (DPAPI, migrations, uvicorn, leitura de secrets) pode ser executado antes da chamada a `servicemanager.StartServiceCtrlDispatcher()`. O bootstrap completo ocorre somente dentro de `SvcDoRun`, após o dispatcher validar que o processo foi invocado pelo SCM. Adicionar comentário explícito no código indicando essa restrição.

- **RF-03** — Em `apps/api/app/launcher.py`, alterar `main()` para rotear por `sys.argv`:
  - `len(sys.argv) > 1 and sys.argv[1] == "service"` → modo serviço: `servicemanager.Initialize()` → `servicemanager.PrepareToHostSingle(TimesheetBackendService)` → `servicemanager.StartServiceCtrlDispatcher()`. Nenhum código privilegiado antes do dispatcher.
  - Caso contrário → modo console: comportamento atual (`configure_logging → prepare_runtime → run_migrations → serve()`), inalterado.
  - O bloco do modo serviço só é alcançável em `sys.platform == "win32"`; fora disso, cair no modo console.

- **RF-04** — Em `apps/api/timesheet-backend.spec`, acrescentar aos `hiddenimports` os módulos do pywin32 service: `"win32serviceutil"`, `"win32service"`, `"win32event"`, `"servicemanager"`, `"win32api"`. Não remover nenhum import existente. Não adicionar outros módulos pywin32 além destes cinco — manter escopo mínimo para não ampliar a superfície do bundle.

- **RF-05** — Em `apps/installer/Components.wxs`, no `<ServiceInstall Id="TimesheetBackendService" ...>`, adicionar o atributo `Arguments=" service"` (espaço inicial obrigatório: o WiX concatena os argumentos ao caminho do exe no binPath). Não alterar o serviço `TimesheetAgent`.

- **RF-06** — Em `apps/api/tests/test_launcher.py`, adicionar testes que cobrem a seleção de modo e o wiring do servidor sem depender do SCM real (ver §7). Os testes do modo serviço devem ser skipados fora de `win32` (`@pytest.mark.skipif(sys.platform != "win32", ...)`) ou mockar os símbolos do pywin32, de modo que o suite continue passando no CI Linux e em `pytest` local.

### Contratos Afetados

**Interface de invocação do binário (`timesheet-backend.exe`):**

| Invocação | Antes | Depois |
| --------- | ----- | ------ |
| `timesheet-backend.exe` (sem args) | Modo console: migra + serve uvicorn | **Inalterado** — modo console |
| `timesheet-backend.exe service` | (não existia — argv ignorado, caía em console) | Modo serviço: dispatcher SCM + handshake |

**binPath do serviço (registro SCM via MSI):**

- Antes: `"C:\Program Files\TimesheetTerceiros\timesheet-backend.exe"`
- Depois: `"C:\Program Files\TimesheetTerceiros\timesheet-backend.exe" service`

Nenhuma mudança em endpoints HTTP, schema de banco ou variáveis de ambiente.

## 4. Riscos e Efeitos Colaterais

- **Import de pywin32 fora do Windows:** o `import win32serviceutil`/`servicemanager` falha em Linux. O CI (`windows-latest`) roda Windows, mas `pytest` local/dev pode ser não-Windows — os imports do modo serviço devem ser lazy/guardados por `sys.platform` para não quebrar o import de `app.launcher` nem a coleta de testes.
- **Modo console deve permanecer byte-a-byte equivalente em comportamento:** a refatoração de `serve()` (RF-01) não pode alterar host/port/workers/log_config nem a semântica bloqueante usada em dev. Regressão a vigiar: `make smoke` e os testes E2E que sobem o backend.
- **Shutdown gracioso:** se o `server.should_exit` não encerrar dentro do timeout de join de 10s no `SvcStop`, o SCM pode reportar erro de parada. O timeout está definido em código — logar `service_stop_timeout` e retornar para que o SCM possa escalar para `TerminateProcess` se necessário.
- **Sanitização de log no bootstrap:** exceções no `SvcDoRun` não devem expor `PRAGMA key`, connection strings com credenciais nem DPAPI blobs — usar apenas o tipo da exceção e a camada onde ocorreu.
- **Caminho de produção LocalSystem subsequente (fora de escopo):** após o handshake corrigido, o bootstrap roda como LocalSystem e pode falhar em pontos seguintes (DPAPI por conta de máquina, `PRAGMA key`/SQLCipher no driver padrão, ACLs de `C:\ProgramData\TimesheetTerceiros`). Este fix cobre apenas o handshake; defeitos subsequentes são tratados em fix separado. O `SvcDoRun` deve, porém, reportar falha ao SCM (em vez de travar em `START_PENDING`) se o bootstrap lançar — para tornar tais falhas observáveis.
- **Serviço `TimesheetAgent` (.NET):** não é alterado por este fix; validar no teste de instalação que continua subindo normalmente.

## 5. Boundaries

**In scope:**

- Implementar o protocolo de Windows Service em `timesheet-backend.exe` (handshake START_PENDING → RUNNING → STOPPED) preservando o modo console.
- Hidden imports do pywin32 service no PyInstaller spec (apenas os 5 módulos estritamente necessários).
- Argumento `service` no binPath do `ServiceInstall` do `TimesheetBackend` no MSI.
- Testes da seleção de modo e do wiring do servidor.
- Log estruturado dos eventos de ciclo de vida do serviço com campos `event` e `svc_name`.

**Out of scope:**

- Defeitos subsequentes do caminho de produção LocalSystem (DPAPI, SQLCipher `PRAGMA key`, ACLs de ProgramData) — fix separado.
- Qualquer alteração no serviço/UI do Agente .NET.
- Refatoração ampla do `launcher.py` além do necessário para o shutdown gracioso e a seleção de modo.
- Mudança de endpoints, schema de banco ou variáveis de ambiente.
- Novos health check probes — `/api/v1/ready` já cobre readiness pós-bootstrap e permanece inalterado.
- Thresholds de alerta, SLOs, labels Prometheus — operacional, no runbook.

## 6. Constraints

- **Backward-compatible com o modo console:** rodar `timesheet-backend.exe` sem argumentos (e `python -m app.launcher` em dev) deve manter o comportamento atual.
- **Sem migração de dados.**
- **Import cross-platform seguro:** `import app.launcher` e a coleta do pytest não podem falhar em ambiente não-Windows; símbolos do pywin32 carregados lazy/guardados por `sys.platform == "win32"`.
- **pywin32==306** já é dependência (`pyproject.toml`, `sys_platform == 'win32'`) e vai no bundle — não adicionar nova dependência.
- **Lint/type:** `ruff check apps/api` e `mypy --strict apps/api/app` devem passar; cobertura backend ≥ 80%.
- **Timeouts em código:** timeout de `server.started` ≤ 30s; timeout de join da thread uvicorn no `SvcStop` = 10s — ambos definidos explicitamente no código, nunca implícitos.
- **Sanitização de log:** mensagens passadas a `servicemanager.LogErrorMsg` e `logger.exception` no bootstrap não devem incluir valores de configuração sensíveis — usar apenas tipo da exceção e camada onde ocorreu.

## 7. Acceptance Criteria

### RF-01

- [ ] `serve()` continua subindo o uvicorn com `host=settings.host`, `port=settings.port`, `workers=1`, `log_config=None` e comportamento bloqueante idêntico ao atual (modo console inalterado).
- [ ] Existe um caminho para encerrar o servidor programaticamente (`server.should_exit = True`) sem depender de sinais do SO, exercitável por teste.

### RF-02

- [ ] Em Windows, existe a classe `TimesheetBackendService` derivada de `win32serviceutil.ServiceFramework` com `_svc_name_ = "TimesheetBackend"`.
- [ ] `SvcDoRun` loga `event="service_start_pending"` e reporta `SERVICE_START_PENDING` antes do bootstrap; loga `event="service_running"` e reporta `SERVICE_RUNNING` somente após `server.started` confirmado (timeout ≤ 30s).
- [ ] `SvcStop` loga `event="service_stop_pending"`, sinaliza shutdown gracioso do uvicorn (`server.should_exit = True`), faz join com timeout de 10s; loga `event="service_stop_timeout"` (WARNING) se o join expirar; loga `event="service_stopped"` se o join completar. O serviço termina reportando `SERVICE_STOPPED`.
- [ ] Exceção no bootstrap dentro de `SvcDoRun` é logada com `event="service_bootstrap_error"` sem expor secrets (PRAGMA key, connection strings, DPAPI blobs), reportada como falha ao SCM via `servicemanager.LogErrorMsg` com mensagem sem secrets, e não trava em `START_PENDING`.
- [ ] Nenhum código privilegiado (DPAPI, migrations, uvicorn, leitura de secrets) é executado antes da chamada a `servicemanager.StartServiceCtrlDispatcher()` no path de modo serviço.

### RF-03

- [ ] `timesheet-backend.exe service` (argv `["...", "service"]`) entra no modo serviço (dispatcher).
- [ ] `timesheet-backend.exe` sem argumentos entra no modo console (comportamento atual).
- [ ] Em plataforma não-Windows, `main()` nunca tenta o caminho de serviço.

### RF-04

- [ ] `timesheet-backend.spec` lista `win32serviceutil`, `win32service`, `win32event`, `servicemanager` e `win32api` em `hiddenimports`, sem remover imports preexistentes e sem adicionar outros módulos pywin32 além desses cinco.

### RF-05

- [ ] O `<ServiceInstall Id="TimesheetBackendService">` no `Components.wxs` inclui `Arguments=" service"`.
- [ ] O `ServiceInstall` do `TimesheetAgent` permanece sem alteração.

### RF-06

- [ ] Teste verifica que `main()` roteia para o modo serviço quando `sys.argv[1] == "service"` (com os símbolos pywin32 mockados ou skip fora de win32).
- [ ] Teste verifica que `main()` roteia para o modo console quando não há o argumento `service`.
- [ ] Os testes preexistentes de `test_launcher.py` continuam passando; o suite passa em CI não-Windows (skip/mocked) e mantém cobertura ≥ 80%.

## 8. Decisões e Trade-offs

| Decisão | Alternativa descartada | Justificativa |
| ------- | ---------------------- | ------------- |
| Ativar o modo serviço por **argumento explícito `service`** no binPath | Auto-detecção tentando `StartServiceCtrlDispatcher()` e caindo em console no erro `ERROR_FAILED_SERVICE_CONTROLLER_CONNECT (1063)` | O argumento explícito é determinístico, trivialmente testável (inspeção de `sys.argv`) e não introduz latência/efeitos do dispatcher no caminho de console. A auto-detecção acopla o start de console a uma chamada Win32 que falha lentamente e é difícil de testar sem o SCM. |
| Subir uvicorn em **thread** com `uvicorn.Server` + `should_exit` | Rodar uvicorn no processo principal e usar sinais (SIGTERM) | O `ServiceFramework` controla o ciclo de vida via callbacks `SvcDoRun`/`SvcStop` numa thread própria; o uvicorn precisa rodar fora dela para o serviço poder reportar RUNNING e tratar STOP. `should_exit` é o mecanismo nativo de shutdown gracioso do uvicorn, sem depender de sinais POSIX (inexistentes/limitados no Windows Service). |
| **pywin32** (`ServiceFramework`) | Reescrever o serviço backend em .NET ou usar um wrapper genérico (NSSM) | pywin32 já é dependência e vai no bundle; mantém um único binário Python; NSSM adicionaria um executável externo ao MSI e perderia o controle do shutdown gracioso. |
| Imports pywin32 **lazy/guardados por `sys.platform`** | Import no topo do módulo | Mantém `app.launcher` importável e o pytest coletável em CI/dev não-Windows. |
| **Timeout de join no `SvcStop` = 10s** | 15s (sugerido pelo SRE) | O timeout de 10s é mais conservador — impede que o SCM fique preso em `STOP_PENDING` por período longo e comprometa reinicializações de segurança emergenciais. 15s foi descartado por exceder o limiar aceitável de resposta do serviço a comandos stop; o SCM escalará para `TerminateProcess` se necessário. |
| **Mensagem de `LogErrorMsg` restrita ao tipo de exceção e camada** | `str(exc)` direto | Contexto de bootstrap pode conter `PRAGMA key`, connection strings com credenciais ou DPAPI blobs. Expor `str(exc)` violaria o princípio de redact de campos sensíveis do PATTERNS de Logging Backend. |

## 9. Ambiguity Report

| Dimensão            | Score | Mín   | Status | Notas |
| ------------------- | ----- | ----- | ------ | ----- |
| Goal Clarity        | 0.95  | 0.75  | OK     | Goal único e reproduzível: handshake SCM preservando console. |
| Boundary Clarity    | 0.93  | 0.70  | OK     | In/out of scope explícitos; caminho LocalSystem subsequente isolado; novos probes fora de escopo. |
| Constraint Clarity  | 0.92  | 0.65  | OK     | Backward-compat, import cross-platform, sem nova dependência, timeouts e sanitização de log explícitos. |
| Acceptance Criteria | 0.92  | 0.70  | OK     | Critérios 1:1 com RF, verificáveis sem SCM real; AC de log e sanitização adicionados. |
| **Ambiguity**       | 0.07  | ≤0.20 | OK     | Causa raiz confirmada por código; abordagem pywin32 já validada pela dependência existente; conflito de timeout resolvido. |
