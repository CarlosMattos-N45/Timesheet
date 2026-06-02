---
checkpoint: null
complexity: M
created_at: "2026-06-02 16:44:23"
criteria:
    - done: false
      test: cd apps/api && pytest -k test_build_server_quando_chamado_deve_usar_settings_host_port_single_worker
      text: serve() sobe uvicorn com host=settings.host, port=settings.port, workers=1, log_config=None (modo console inalterado)
    - done: false
      test: cd apps/api && pytest -k test_build_server_quando_should_exit_setado_deve_permitir_shutdown_programatico
      text: Existe caminho para encerrar o servidor programaticamente via server.should_exit=True sem sinais do SO
    - done: false
      text: Em win32 existe TimesheetBackendService derivada de win32serviceutil.ServiceFramework com _svc_name_=TimesheetBackend e _svc_display_name_=Timesheet Backend
    - done: false
      text: SvcDoRun loga event=service_start_pending e reporta SERVICE_START_PENDING antes do bootstrap; loga event=service_running e reporta SERVICE_RUNNING somente apos server.started confirmado (timeout 30s)
    - done: false
      text: SvcStop loga event=service_stop_pending, seta server.should_exit=True, faz join com timeout 10s; loga event=service_stop_timeout (WARNING) se expira; loga event=service_stopped se completa; servico termina em SERVICE_STOPPED
    - done: false
      text: Excecao no bootstrap dentro de SvcDoRun loga event=service_bootstrap_error sem expor secrets (PRAGMA key, connection strings, DPAPI blobs), passa a LogErrorMsg apenas tipo da excecao e camada (nunca str(exc)), e nao trava em START_PENDING
    - done: false
      test: cd apps/api && pytest -k test_main_quando_argv_service_deve_rotear_para_dispatcher
      text: Nenhum codigo privilegiado (DPAPI, migrations, uvicorn, secrets) executado antes de servicemanager.StartServiceCtrlDispatcher() no path de modo servico
    - done: false
      test: cd apps/api && pytest -k test_main_quando_argv_service_deve_rotear_para_dispatcher
      text: main() roteia para modo servico quando sys.argv[1]==service em win32
    - done: false
      test: cd apps/api && pytest -k test_main_quando_sem_argumento_deve_rotear_para_console
      text: main() roteia para modo console quando nao ha argumento service
    - done: false
      test: cd apps/api && pytest -k test_main_quando_argv_service_em_nao_windows_deve_cair_em_console
      text: Em plataforma nao-Windows main() nunca tenta o caminho de servico
    - done: false
      text: Os 3 testes preexistentes de test_launcher.py continuam passando e o suite passa em CI nao-Windows (skip/mocked) com cobertura >= 80%
    - done: false
      text: 'Imports do pywin32 sao lazy/guardados por sys.platform==win32: import app.launcher e a coleta do pytest nao falham fora de win32'
deps: []
id: TASK-001
linter: ruff check apps/api && mypy --strict apps/api/app
n45_version: 0.2.0
persona: backend
phase: Phase 1 — Handshake SCM do Backend
roadmap: fix-0002-backend-nao-roda-como-windows-service-handshake-scm-ausente
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: cd apps/api && pytest tests/test_launcher.py
title: Modo Windows Service no launcher.py (handshake SCM) + selecao de modo console/servico + testes
updated_at: "2026-06-02 16:44:23"
---
## Contexto

O `timesheet-backend.exe` é registrado pelo MSI como Windows Service nativo (`Type="ownProcess"`, `Account="LocalSystem"`, `ServiceControl Start="install" Wait="yes"`), mas o entrypoint `apps/api/app/launcher.py` é hoje **só de console**: `main()` faz `configure_logging → prepare_runtime → run_migrations → serve()`, e `serve()` chama `uvicorn.run(...)` (bloqueante). Não existe nenhuma implementação do protocolo de Windows Service (nenhuma classe `ServiceFramework`, nenhum dispatcher, nenhum reporte de estado ao SCM). Resultado: o SCM inicia o processo, o uvicorn sobe e serve HTTP, mas o SCM **nunca recebe `SERVICE_RUNNING`** → atinge timeout → o passo `StartServices` do MSI falha com o diálogo de erro e a instalação aborta. Esta é a causa raiz de um bloqueador total de produção (o produto não instala).

Esta task implementa o handshake do SCM **preservando 100% o modo console atual**. A ativação do modo serviço é **determinística por argumento explícito**: o MSI passará `service` no binPath (`timesheet-backend.exe service`) — essa mudança no `Components.wxs` é feita em outra task; aqui basta rotear por `sys.argv`. Quando invocado sem argumentos (console/dev), o comportamento permanece idêntico.

Estado atual relevante de `launcher.py` (funções públicas que **não mudam de contrato**): `derive_db_cipher_key_hex(kek_path)`, `prepare_runtime(settings)`, `static_dir_for_bundle()`, `run_migrations()`. A config expõe `settings.host` (str) e `settings.port` (int). O logging é structlog JSON via `app.core.logging.configure_logging()`; o módulo usa `logger = logging.getLogger(__name__)`. **Cross-platform:** `pytest` roda em CI Windows (`windows-latest`) **e** em dev/Linux — `import app.launcher` e a coleta do pytest **não podem falhar** em ambiente não-Windows, logo os imports do `pywin32` (`win32serviceutil`, `win32service`, `win32event`, `servicemanager`, `win32api`) precisam ser **lazy** (dentro de função) ou guardados por `sys.platform == "win32"`. `pywin32==306` já é dependência (`sys_platform == 'win32'`) e já vai no bundle — **não adicionar dependência**.

## Comportamento Esperado

Roteamento por `sys.argv` em `main()`, refatoração de `serve()` para shutdown programático, e a classe de serviço Windows com o ciclo de vida completo.

**Exemplos (entrada → saída esperada)** — valores reais, base direta das assertions:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `main()` com `sys.argv = ["timesheet-backend.exe", "service"]` em `win32` | chama `servicemanager.Initialize()`, `servicemanager.PrepareToHostSingle(TimesheetBackendService)`, `servicemanager.StartServiceCtrlDispatcher()` nessa ordem; **não** chama `prepare_runtime`/`run_migrations`/`serve` no path do dispatcher |
| `main()` com `sys.argv = ["timesheet-backend.exe"]` (sem args) | chama `configure_logging()`, `prepare_runtime(settings)`, `run_migrations()`, `serve()` — comportamento console atual, inalterado |
| `main()` com `sys.argv = ["timesheet-backend.exe", "service"]` em `sys.platform == "linux"` | cai no modo console (nunca tenta o path de serviço) |
| `build_server()` (helper novo) | retorna um `uvicorn.Server` cujo `config` tem `host == settings.host`, `port == settings.port`, `workers == 1`, `log_config is None` |
| `run_server(server)` | chama `server.run()` (bloqueante) — wrapper para o uvicorn nativo |
| `server.should_exit = True` num `uvicorn.Server` em execução | encerra o `server.run()` graciosamente sem sinais do SO |
| `TimesheetBackendService._svc_name_` | `"TimesheetBackend"` |
| `TimesheetBackendService._svc_display_name_` | `"Timesheet Backend"` |

**Ciclo de vida do serviço (`SvcDoRun` / `SvcStop`), efeitos observáveis:**

| Momento | Efeito esperado |
| ------- | --------------- |
| Início de `SvcDoRun` | loga `event="service_start_pending", svc_name="TimesheetBackend"`; reporta `SERVICE_START_PENDING` ao SCM **antes** do bootstrap |
| Após `server.started` confirmado (timeout ≤ 30s) | loga `event="service_running", svc_name="TimesheetBackend"`; reporta `SERVICE_RUNNING` |
| `server.started` não confirma em 30s | reporta falha/stop ao SCM (não trava em `START_PENDING`) |
| `SvcStop` chamado | loga `event="service_stop_pending"`; reporta `SERVICE_STOP_PENDING`; seta `server.should_exit = True`; `SetEvent(self._stop_event)`; join da thread uvicorn com timeout 10s |
| join completa dentro de 10s | loga `event="service_stopped"`; serviço termina reportando `SERVICE_STOPPED` |
| join expira em 10s | loga `event="service_stop_timeout"` (nível WARNING) e retorna (SCM escala para `TerminateProcess`) |
| Exceção no bootstrap dentro de `SvcDoRun` | loga `event="service_bootstrap_error"` via `logger.exception` (ERROR) **sem expor secrets**; `servicemanager.LogErrorMsg` com **apenas tipo da exceção + camada** (nunca `str(exc)`); reporta stop ao SCM |

## TDD

Persona `backend` — código novo, ciclo red → green → refactor. Os testes vão em `apps/api/tests/test_launcher.py` (já existe, **preservar os testes atuais**). Os testes do modo serviço **mockam os símbolos do pywin32** (ou usam `@pytest.mark.skipif(sys.platform != "win32", ...)`) para que o suite passe em CI não-Windows e em `pytest` local. Nomenclatura: `test_<função>_quando_<condição>_deve_<resultado>` (padrão do projeto). Sob `pytest-asyncio` + httpx já configurados.

**Testes a escrever antes da implementação (devem falhar inicialmente):**

```python
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


def test_build_server_quando_chamado_deve_usar_settings_host_port_single_worker() -> None:
    from app import launcher

    server = launcher.build_server()
    cfg = server.config
    from app.core.config import settings

    assert cfg.host == settings.host
    assert cfg.port == settings.port
    assert cfg.workers == 1
    assert cfg.log_config is None


def test_build_server_quando_should_exit_setado_deve_permitir_shutdown_programatico() -> None:
    from app import launcher

    server = launcher.build_server()
    # mecanismo nativo de shutdown gracioso do uvicorn, sem sinais do SO
    server.should_exit = True
    assert server.should_exit is True


def test_main_quando_argv_service_deve_rotear_para_dispatcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["timesheet-backend.exe", "service"])
    monkeypatch.setattr(sys, "platform", "win32")
    fake_servicemanager = MagicMock()
    spies = {
        "prepare_runtime": MagicMock(),
        "run_migrations": MagicMock(),
        "serve": MagicMock(),
    }
    with patch.dict(sys.modules, {"servicemanager": fake_servicemanager}):
        from app import launcher

        monkeypatch.setattr(launcher, "prepare_runtime", spies["prepare_runtime"])
        monkeypatch.setattr(launcher, "run_migrations", spies["run_migrations"])
        monkeypatch.setattr(launcher, "serve", spies["serve"])
        # TimesheetBackendService deve ser resolvido a partir do módulo (lazy import win32)
        with patch.object(launcher, "_run_service") as run_service:
            launcher.main()
            run_service.assert_called_once()
    # nenhum código privilegiado no path do dispatcher
    spies["prepare_runtime"].assert_not_called()
    spies["run_migrations"].assert_not_called()
    spies["serve"].assert_not_called()


def test_main_quando_sem_argumento_deve_rotear_para_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["timesheet-backend.exe"])
    from app import launcher

    calls: list[str] = []
    monkeypatch.setattr(launcher, "prepare_runtime", lambda s: calls.append("prepare"))
    monkeypatch.setattr(launcher, "run_migrations", lambda: calls.append("migrate"))
    monkeypatch.setattr(launcher, "serve", lambda: calls.append("serve"))
    monkeypatch.setattr(
        "app.core.logging.configure_logging", lambda: calls.append("log")
    )
    launcher.main()
    assert calls == ["log", "prepare", "migrate", "serve"]


def test_main_quando_argv_service_em_nao_windows_deve_cair_em_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["timesheet-backend.exe", "service"])
    monkeypatch.setattr(sys, "platform", "linux")
    from app import launcher

    calls: list[str] = []
    monkeypatch.setattr(launcher, "prepare_runtime", lambda s: calls.append("prepare"))
    monkeypatch.setattr(launcher, "run_migrations", lambda: calls.append("migrate"))
    monkeypatch.setattr(launcher, "serve", lambda: calls.append("serve"))
    monkeypatch.setattr(
        "app.core.logging.configure_logging", lambda: calls.append("log")
    )
    launcher.main()
    # caiu no console, nunca tentou dispatcher
    assert "serve" in calls
```

> **Nota sobre a classe de serviço:** `TimesheetBackendService(win32serviceutil.ServiceFramework)` só pode ser definida quando o `win32serviceutil` está importável (Windows). Defini-la dentro de um bloco `if sys.platform == "win32":` (com import lazy) ou numa factory. Os testes acima validam o **roteamento** e o **wiring do server** sem o SCM real; em `win32`, adicionar um teste extra (`@pytest.mark.skipif(sys.platform != "win32", ...)`) que afirma `TimesheetBackendService._svc_name_ == "TimesheetBackend"` e `_svc_display_name_ == "Timesheet Backend"`.

**Refatoração:** após o green, manter `serve()` como wrapper fino (`build_server()` + `run_server(server)`) para zero duplicação entre console e serviço; garantir que o bloco `try/except` de `main()` console permanece idêntico em semântica (loga `logger.exception` e `sys.exit(1)`).

## O que Implementar

Refatorar `apps/api/app/launcher.py`. Código mínimo para cobrir RF-01 a RF-03 e RF-06, sem over-engineering. Não tocar `prepare_runtime`, `run_migrations`, `static_dir_for_bundle`, `derive_db_cipher_key_hex` (contratos preservados).

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/api/app/launcher.py` | Modificar | Refatorar `serve()` em `build_server()`+`run_server()`; adicionar `TimesheetBackendService` (guardada por `sys.platform == "win32"`, imports pywin32 lazy); rotear `main()` por `sys.argv`; helper `_run_service()` para o dispatcher |
| `apps/api/tests/test_launcher.py` | Modificar | Adicionar os testes de seleção de modo e wiring do server (acima), preservando os 3 testes existentes |

### Detalhamento Técnico

1. **RF-01 — `serve()` refatorado para shutdown programático.** Substituir `uvicorn.run(...)` por construção explícita do `Server`:

   - `build_server() -> "uvicorn.Server"`: importa uvicorn lazy, importa `settings` e `create_app`, monta `uvicorn.Config(create_app(), host=settings.host, port=settings.port, workers=1, log_config=None)` e retorna `uvicorn.Server(config)`.
   - `run_server(server: "uvicorn.Server") -> None`: chama `server.run()` (bloqueante, idêntico ao comportamento atual).
   - `serve() -> None`: `run_server(build_server())` — mantém a assinatura e a semântica bloqueante do console.

2. **RF-02 — Classe de serviço Windows.** Guardada por plataforma, imports pywin32 lazy (nunca no topo do módulo). O bootstrap completo (`configure_logging`/`prepare_runtime`/`run_migrations`/uvicorn) roda **somente dentro de `SvcDoRun`**, após o dispatcher validar a invocação pelo SCM.
   - `_svc_name_ = "TimesheetBackend"`, `_svc_display_name_ = "Timesheet Backend"`.
   - `__init__`: cria `self._stop_event = win32event.CreateEvent(None, 0, 0, None)`, `self._server = None`, `self._thread = None`.
   - `SvcDoRun`:
     1. `logger` loga `event="service_start_pending", svc_name="TimesheetBackend"`; `self.ReportServiceStatus(win32service.SERVICE_START_PENDING)`.
     2. dentro de `try`: `configure_logging()`; `prepare_runtime(settings)`; `run_migrations()`; `self._server = build_server()`.
     3. inicia `self._thread = threading.Thread(target=self._server.run, daemon=True)`; `self._thread.start()`.
     4. aguarda `self._server.started` (atributo do uvicorn) com **timeout de 30s** via poll curto (ex.: loop `while not self._server.started and elapsed < 30: time.sleep(0.1)`); se não confirmar, vai para o ramo de falha.
     5. confirmado: loga `event="service_running", svc_name="TimesheetBackend"`; `self.ReportServiceStatus(win32service.SERVICE_RUNNING)`; bloqueia em `win32event.WaitForSingleObject(self._stop_event, win32event.INFINITE)`.
     6. `except Exception as exc`: `logger.exception("service bootstrap falhou", extra={"event": "service_bootstrap_error", "svc_name": "TimesheetBackend"})`; `servicemanager.LogErrorMsg(f"{type(exc).__name__} durante bootstrap do serviço (camada: launcher)")` — **nunca** `str(exc)`; reporta stop ao SCM (deixa `SvcDoRun` retornar para o framework reportar `SERVICE_STOPPED`).
   - `SvcStop`:
     1. loga `event="service_stop_pending", svc_name="TimesheetBackend"`; `self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)`.
     2. se `self._server is not None`: `self._server.should_exit = True`.
     3. `win32event.SetEvent(self._stop_event)`.
     4. se `self._thread is not None`: `self._thread.join(timeout=10)`; se `self._thread.is_alive()` → loga `event="service_stop_timeout", svc_name="TimesheetBackend"` (WARNING) e retorna; senão loga `event="service_stopped", svc_name="TimesheetBackend"`.

3. **RF-03 — Roteamento em `main()`:**

   ```python
   def main() -> None:
       if sys.platform == "win32" and len(sys.argv) > 1 and sys.argv[1] == "service":
           _run_service()
           return
       _run_console()
   ```

   - `_run_console()`: corpo atual de `main()` (`configure_logging()`; `try: prepare_runtime(settings); run_migrations(); serve()`; `except Exception: logger.exception(...); sys.exit(1)`).
   - `_run_service()`: import lazy de `servicemanager` e da factory de `TimesheetBackendService`; `servicemanager.Initialize()`; `servicemanager.PrepareToHostSingle(TimesheetBackendService)`; `servicemanager.StartServiceCtrlDispatcher()`. **Comentário explícito no código:** nenhum código privilegiado (DPAPI, migrations, uvicorn, leitura de secrets) antes de `StartServiceCtrlDispatcher()` — o bootstrap só ocorre dentro de `SvcDoRun`.

4. **Imports cross-platform.** No topo do módulo manter apenas stdlib (`logging`, `os`, `sys`, `threading`, `time`, `pathlib`). Os imports de `win32serviceutil`/`win32service`/`win32event`/`servicemanager`/`win32api` ficam dentro de `_run_service()` e da definição/factory da classe de serviço, atrás de `sys.platform == "win32"`.

**Contrato com camadas adjacentes:**

```
Interface de invocação do binário (timesheet-backend.exe):
  - timesheet-backend.exe          → modo console (inalterado): migra + serve uvicorn
  - timesheet-backend.exe service  → modo serviço: dispatcher SCM + handshake START_PENDING → RUNNING → STOPPED

Consome de: app.core.config.settings (host: str, port: int)
Consome de: app.core.logging.configure_logging() — structlog JSON
Consome de: app.main.create_app() — FastAPI app
Produz para: SCM (Windows Service Control Manager) via win32serviceutil.ServiceFramework
  - SERVICE_START_PENDING → SERVICE_RUNNING (após server.started) → SERVICE_STOPPED
  - Falha de bootstrap → reporta stop (nunca trava em START_PENDING)
```

**Exemplo de implementação (núcleo):**

```python
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_SERVER_STARTED_TIMEOUT_S = 30
_STOP_JOIN_TIMEOUT_S = 10


def build_server() -> "uvicorn.Server":
    import uvicorn  # noqa: PLC0415

    from app.core.config import settings  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    config = uvicorn.Config(
        create_app(),
        host=settings.host,
        port=settings.port,
        workers=1,
        log_config=None,
    )
    return uvicorn.Server(config)


def run_server(server: "uvicorn.Server") -> None:
    server.run()


def serve() -> None:
    """Console mode — bloqueante, comportamento idêntico ao anterior."""
    run_server(build_server())


if sys.platform == "win32":
    import servicemanager  # noqa: PLC0415,E402
    import win32event  # noqa: PLC0415,E402
    import win32service  # noqa: PLC0415,E402
    import win32serviceutil  # noqa: PLC0415,E402

    class TimesheetBackendService(win32serviceutil.ServiceFramework):  # type: ignore[misc]
        _svc_name_ = "TimesheetBackend"
        _svc_display_name_ = "Timesheet Backend"

        def __init__(self, args: list[str]) -> None:
            super().__init__(args)
            self._stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._server = None
            self._thread = None

        def SvcDoRun(self) -> None:  # noqa: N802
            from app.core.config import settings  # noqa: PLC0415
            from app.core.logging import configure_logging  # noqa: PLC0415

            logger.info("service start_pending", extra={"event": "service_start_pending", "svc_name": self._svc_name_})
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            try:
                configure_logging()
                prepare_runtime(settings)
                run_migrations()
                self._server = build_server()
                self._thread = threading.Thread(target=self._server.run, daemon=True)
                self._thread.start()
                elapsed = 0.0
                while not getattr(self._server, "started", False) and elapsed < _SERVER_STARTED_TIMEOUT_S:
                    time.sleep(0.1)
                    elapsed += 0.1
                if not getattr(self._server, "started", False):
                    raise RuntimeError("uvicorn server não confirmou started no timeout")
                logger.info("service running", extra={"event": "service_running", "svc_name": self._svc_name_})
                self.ReportServiceStatus(win32service.SERVICE_RUNNING)
                win32event.WaitForSingleObject(self._stop_event, win32event.INFINITE)
            except Exception as exc:  # noqa: BLE001
                logger.exception("service bootstrap falhou", extra={"event": "service_bootstrap_error", "svc_name": self._svc_name_})
                servicemanager.LogErrorMsg(f"{type(exc).__name__} durante bootstrap do serviço (camada: launcher)")
                # não trava em START_PENDING: retorna → framework reporta STOPPED

        def SvcStop(self) -> None:  # noqa: N802
            logger.info("service stop_pending", extra={"event": "service_stop_pending", "svc_name": self._svc_name_})
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self._server is not None:
                self._server.should_exit = True
            win32event.SetEvent(self._stop_event)
            if self._thread is not None:
                self._thread.join(timeout=_STOP_JOIN_TIMEOUT_S)
                if self._thread.is_alive():
                    logger.warning("service stop_timeout", extra={"event": "service_stop_timeout", "svc_name": self._svc_name_})
                    return
            logger.info("service stopped", extra={"event": "service_stopped", "svc_name": self._svc_name_})


def _run_service() -> None:
    # RESTRIÇÃO: nenhum código privilegiado (DPAPI, migrations, uvicorn,
    # leitura de secrets) antes de StartServiceCtrlDispatcher(). O bootstrap
    # completo ocorre apenas dentro de SvcDoRun, após o dispatcher validar
    # que o processo foi invocado pelo SCM.
    servicemanager.Initialize()
    servicemanager.PrepareToHostSingle(TimesheetBackendService)
    servicemanager.StartServiceCtrlDispatcher()


def _run_console() -> None:
    from app.core.config import settings  # noqa: PLC0415
    from app.core.logging import configure_logging  # noqa: PLC0415

    configure_logging()
    try:
        prepare_runtime(settings)
        run_migrations()
        serve()
    except Exception:
        logger.exception("Bootstrap falhou — encerrando")
        sys.exit(1)


def main() -> None:
    if sys.platform == "win32" and len(sys.argv) > 1 and sys.argv[1] == "service":
        _run_service()
        return
    _run_console()


if __name__ == "__main__":
    main()
```

> **Lint/type:** `ruff check apps/api` e `mypy --strict apps/api/app` devem passar. Para `mypy --strict`, os imports do pywin32 não têm stubs — usar `# type: ignore[import-untyped]`/`[misc]` pontuais onde necessário, sem desabilitar checagem global. Cobertura backend ≥ 80%.
