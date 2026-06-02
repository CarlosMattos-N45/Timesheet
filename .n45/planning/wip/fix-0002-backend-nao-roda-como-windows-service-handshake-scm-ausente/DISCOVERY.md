---
created_at: "2026-06-02 12:32:03"
id: fix-0002-backend-nao-roda-como-windows-service-handshake-scm-ausente
n45_version: 0.2.0
title: Backend nao roda como Windows Service (handshake SCM ausente)
type: fix
---
## As Is (hoje)

A instalação de produção via MSI falha com o diálogo: _"Serviço 'Timesheet Backend' (TimesheetBackend) não iniciado. Verifique se você tem privilégios suficientes para iniciar os serviços do sistema."_

**Reprodução:** instalar `dist\TimesheetTerceiros.msi` (elevado). O passo `StartServices` registra o serviço `TimesheetBackend` (que aponta para `timesheet-backend.exe`) e aguarda (`ServiceControl Wait="yes"`) o serviço reportar `SERVICE_RUNNING` ao SCM. O processo **inicia e fica rodando** (serve HTTP, pid observado segurando a :8765), mas **nunca reporta RUNNING ao SCM** → o SCM atinge timeout → StartServices falha → diálogo de erro. Ao cancelar, o rollback remove o registro do serviço mas deixa o processo órfão (LocalSystem) na :8765.

Confirmação técnica: rodar o mesmo `timesheet-backend.exe` direto no console responde `/api/v1/health` 200 — o binário funciona; o que falta é o protocolo de serviço.

## To Be (depois)

`timesheet-backend.exe`, quando iniciado pelo SCM como Windows Service, faz o handshake correto: reporta `SERVICE_START_PENDING` → sobe o uvicorn → reporta `SERVICE_RUNNING`, e em STOP encerra o uvicorn graciosamente reportando `SERVICE_STOPPED`. A instalação do MSI conclui sem erro, com `TimesheetBackend` em estado Running e `/api/v1/ready` respondendo 200. Executar o exe sem o contexto de SCM (console/dev) continua funcionando como hoje.

## Causa raiz (provável)

`apps/api/app/launcher.py` é um entrypoint de console puro: `main()` faz `configure_logging → prepare_runtime → run_migrations → serve()`, e `serve()` chama `uvicorn.run(...)`. Não há nenhuma implementação do protocolo de Windows Service (`win32serviceutil.ServiceFramework` / `servicemanager` / `StartServiceCtrlDispatcher`) em todo o `apps/api` (busca confirmou ausência). Já `apps/installer/Components.wxs` registra o exe diretamente como serviço nativo (`Type="ownProcess"`, `Account="LocalSystem"`, `ServiceControl Start="install" Wait="yes"`). Binário não-service-aware registrado como serviço nativo = SCM nunca recebe RUNNING.

Abordagem escolhida: **pywin32** (já é dependência e já vai no bundle PyInstaller). Tornar o exe capaz de detectar quando foi iniciado pelo SCM e, nesse caso, despachar via `ServiceFramework` rodando o uvicorn numa thread; caso contrário, comportamento de console atual.

## Escopo / Arquivos afetados

- `apps/api/app/launcher.py` — adicionar modo serviço (ServiceFramework + dispatcher) preservando o modo console.
- Possivelmente `apps/api/timesheet-backend.spec` — garantir hidden imports do pywin32 service (`win32serviceutil`, `win32service`, `win32event`, `servicemanager`) no bundle.
- `apps/installer/Components.wxs` — se a ativação do modo serviço exigir argumento no binPath ou nome de serviço, ajustar o `ServiceInstall`/`Arguments`.
- Testes do backend (`apps/api/tests/`) — cobrir a seleção de modo (console vs serviço) de forma testável sem depender do SCM real.

## Efeitos colaterais

- O mesmo exe é usado em dev/console e como serviço — a detecção de modo não pode quebrar a execução de console (usada por nós em dev).
- O `prepare_runtime`/`run_migrations` roda como LocalSystem em produção (DPAPI por conta de máquina + SQLCipher derivado da KEK) — após corrigir o handshake, podem surgir falhas subsequentes nesse caminho (PRAGMA key com o sqlite padrão, ACLs de `C:\ProgramData\TimesheetTerceiros`, geração de KEK via DPAPI como LocalSystem). Este fix foca no handshake do serviço; defeitos subsequentes do caminho de produção serão tratados na sequência.
- O serviço `TimesheetAgent` (.NET) provavelmente já usa o suporte nativo a Windows Service e não é afetado — validar durante o teste de instalação.

## Validação

Build do MSI (`timesheet-backend.exe` + agente + `wix build`) → instalar elevado → `sc query TimesheetBackend` em `RUNNING` → `/api/v1/ready` 200 → parar/desinstalar limpos. Limpar antes o processo órfão atual na :8765 (reboot ou kill elevado).
