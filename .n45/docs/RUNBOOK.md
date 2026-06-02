---
health_checks:
    - command: curl -fsS http://localhost:8025
      service: mailhog
      type: infra
    - command: curl -fsS http://127.0.0.1:8765/api/v1/health
      service: TimesheetBackend
      type: app
    - command: curl -fsS http://127.0.0.1:8765/api/v1/ready
      service: TimesheetBackend-ready
      type: app
infra_down: make smtp-down
infra_up: make smtp-up
n45_version: 0.2.0
services:
    - description: Servidor SMTP fake (Mailhog) para desenvolvimento
      name: mailhog-smtp
      port: 1025
    - description: Interface web do Mailhog para inspecionar e-mails enviados
      name: mailhog-ui
      port: 8025
    - description: Windows Service do backend HTTP (produção, porta configurável via TIMESHEET_PORT)
      name: TimesheetBackend
      port: 8765
    - description: Windows Service do agente .NET (produção)
      name: TimesheetAgent
      port: null
setup: make data-dir && make smtp-up
start: docker compose -f docker-compose.dev.yml up -d
stop: docker compose -f docker-compose.dev.yml down
test:
    all: make smoke
    e2e: cd apps/web && npx playwright test
    unit: cd apps/api && pytest
url: http://localhost:8765
---

# Runbook — Timesheet Terceiros

## Infraestrutura

Este projeto e full-local: o banco SQLite + SQLCipher e embarcado no processo do Backend (sem container) e o banco do Agente e SQLite embarcado no executavel .NET (sem container). A unica dependencia externa rodada via docker-compose em desenvolvimento e o Mailhog (servidor SMTP fake).

### Servicos

| Servico   | Imagem                 | Porta(s)              | Volume                    | Healthcheck                          |
| --------- | ---------------------- | --------------------- | ------------------------- | ------------------------------------ |
| mailhog   | mailhog/mailhog:v1.0.1 | 1025 (SMTP), 8025 (UI) | timesheet-mailhog-data   | wget --spider http://localhost:8025  |

### Comandos

- `make smtp-up` — sobe Mailhog e aguarda healthcheck (max 30s).
- `make smtp-down` — derruba Mailhog e remove volume.
- `make smtp-status` — exibe estado atual.
- `make data-dir` — cria diretorio `data/` local para SQLite e key.kek em dev.

### Healthchecks manuais

- Mailhog UI: `curl -fsS http://localhost:8025` retorna 200.
- Mailhog SMTP: `Test-NetConnection 127.0.0.1 -Port 1025` retorna `TcpTestSucceeded: True`.

### Banco de dados (sem container)

- Backend: SQLite + SQLCipher em `./data/timesheet.sqlite` (dev). Em producao, `C:\ProgramData\TimesheetTerceiros\timesheet.sqlite` provisionado pelo MSI.
- Agente: SQLite em `./data/agent-queue.sqlite` (dev) ou `C:\ProgramData\TimesheetTerceiros\agent-queue.sqlite` (producao).
- KEK: `./data/key.kek` (dev, gerada na primeira execucao se ausente). Em producao, `C:\ProgramData\TimesheetTerceiros\key.kek` protegida por DPAPI e vinculada a conta LocalSystem do Service.

## Aplicacao

Esta secao descreve o ciclo de vida da aplicacao em producao (Windows), instalada via MSI.

> Producao usa `C:\ProgramData\TimesheetTerceiros\` (nao `%APPDATA%`), pois os Windows Services
> rodam como `LocalSystem` e precisam de um caminho estavel e compartilhado entre contas.

### Instalacao

```powershell
# Instalacao silenciosa com porta padrao (8765)
msiexec /i TimesheetTerceiros.msi /qn

# Instalacao silenciosa com porta customizada
msiexec /i TimesheetTerceiros.msi /qn TIMESHEET_PORT=9000

# O MSI:
# 1. Instala binarios em C:\Program Files\TimesheetTerceiros\
# 2. Cria C:\ProgramData\TimesheetTerceiros\pdfs\ (ACL restrita a SYSTEM + Administrators)
# 3. Registra e inicia os 2 Windows Services
# 4. Registra TimesheetAgentUi.exe para autostart na sessao do usuario (pasta Startup)
# 5. Define env vars TIMESHEET_* no ambiente do Service backend
# 6. Aguarda /api/v1/ready responder 200 (timeout 60s)
```

### Windows Services

| Servico          | Tipo       | Conta      | Start | Descricao                                    |
| ---------------- | ---------- | ---------- | ----- | -------------------------------------------- |
| TimesheetBackend | ownProcess | LocalSystem | auto | Servidor HTTP (porta configuravel via MSI)   |
| TimesheetAgent   | ownProcess | LocalSystem | auto | Agente de processamento de tarefas .NET      |

```powershell
# Iniciar servicos manualmente
sc start TimesheetBackend
sc start TimesheetAgent

# Parar servicos
sc stop TimesheetBackend
sc stop TimesheetAgent

# Verificar estado
sc query TimesheetBackend
sc query TimesheetAgent
```

### Autostart da UI

`TimesheetAgentUi.exe` e configurado para iniciar automaticamente na sessao do usuario via atalho na pasta `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.

### Dados de Producao

Todos os dados persistidos em `C:\ProgramData\TimesheetTerceiros\`:

| Arquivo / Pasta  | Descricao                                           |
| ---------------- | --------------------------------------------------- |
| `key.kek`        | Chave mestra de criptografia (DPAPI, LocalSystem)   |
| `timesheet.sqlite` | Banco SQLite + SQLCipher do dominio               |
| `pdfs\`          | PDFs gerados (ACL restrita a SYSTEM + Administrators) |
| `scheduler.sqlite` | Banco SQLite dos jobs do APScheduler             |

### Healthchecks de Producao

```powershell
# Health (servico vivo)
curl http://127.0.0.1:8765/api/v1/health
# Resposta esperada: 200 OK

# Ready (servico pronto — banco ok, migrations ok)
curl http://127.0.0.1:8765/api/v1/ready
# Resposta esperada: 200 OK
```

### Build e Release

```powershell
# Build completo: backend + agente + MSI
make build
# Saida: dist/TimesheetTerceiros.msi

# Validar MSI sem rodar o build dos executaveis (CI)
make installer-validate

# Release assinado (requer SIGN_CERT apontando para .pfx)
$env:SIGN_CERT = "C:\certs\meu-cert.pfx"
make release
# Assina dist/TimesheetTerceiros.msi com signtool + timestamp DigiCert

# Setup do ambiente de dev (sem subir app)
make setup
# Cria data/ local; producao e instalada via MSI
```

### Desinstalacao

```powershell
# Desinstalacao silenciosa
msiexec /x TimesheetTerceiros.msi /qn

# O MSI remove:
# - Servicos TimesheetBackend e TimesheetAgent (para + remove)
# - Binarios em C:\Program Files\TimesheetTerceiros\
# - Atalho de autostart da UI na pasta Startup
# Dados em C:\ProgramData\TimesheetTerceiros\ sao preservados (convencao MSI)
```

## Pre-requisitos (desenvolvimento)

- Docker Desktop (para Mailhog)
- Python 3.12+ com pip
- Node.js 20+
- .NET 8 SDK
- WiX Toolset (para gerar MSI)
- PyInstaller (`pip install pyinstaller`)

## Variaveis de Ambiente

| Variavel                  | Descricao                                        | Exemplo                     | Obrigatorio | Secret |
| ------------------------- | ------------------------------------------------ | --------------------------- | ----------- | ------ |
| TIMESHEET_DEV             | Habilita OpenAPI docs e modo desenvolvimento     | true                        | nao         | nao    |
| TIMESHEET_PORT            | Porta do servidor HTTP                           | 8765                        | nao         | nao    |
| TIMESHEET_DB_CIPHER_KEY   | Chave de cifragem SQLCipher (dev apenas)         | hex-32-bytes                | sim (dev)   | sim    |
| TIMESHEET_SECRET_KEY      | Chave secreta JWT                                | hex-32-bytes                | sim         | sim    |
| TIMESHEET_HOST            | Host de bind do servidor                         | 127.0.0.1                   | nao         | nao    |

## Setup (primeira execucao — dev)

```bash
# 1. Criar diretorio de dados local
make data-dir

# 2. Subir Mailhog
make smtp-up

# 3. Copiar .env.example para .env e preencher as variaveis secret
cp .env.example .env
# Editar .env com os valores reais

# 4. Instalar dependencias backend
cd apps/api && pip install -e ".[dev]"

# 5. Rodar migrations
cd apps/api && alembic upgrade head

# 6. Instalar dependencias frontend
cd apps/web && npm install

# 7. Instalar dependencias do agente .NET
cd apps/agent && dotnet restore

# 8. Validar smoke completo
make smoke
```

## Health Checks

| Servico               | Endpoint                           | Metodo | Resposta esperada |
| --------------------- | ---------------------------------- | ------ | ----------------- |
| Backend (vivo)        | /api/v1/health                     | GET    | 200 OK            |
| Backend (pronto)      | /api/v1/ready                      | GET    | 200 OK {"status":"ready"} |
| Mailhog UI (dev)      | http://localhost:8025              | GET    | 200 OK            |

## Comandos Uteis

```bash
# Rodar backend em modo dev (OpenAPI habilitado)
cd apps/api && TIMESHEET_DEV=true uvicorn app.main:app --reload --port 8765

# Rodar frontend em modo dev
cd apps/web && npm run dev

# Rodar testes backend
cd apps/api && pytest

# Rodar testes agente
cd apps/agent && dotnet test Timesheet.Agent.sln

# Rodar E2E Playwright
cd apps/web && npx playwright test

# Build completo (backend PyInstaller + agente .NET + MSI)
make build

# Smoke (valida api/health + web dev + agent build)
make smoke

# Logs do Mailhog (docker)
docker compose -f docker-compose.dev.yml logs -f mailhog
```

## Integracoes Externas

| Servico | Finalidade                                     | Autenticacao                         |
| ------- | ---------------------------------------------- | ------------------------------------ |
| SMTP    | Envio de relatorio mensal PDF ao destinatario  | Usuario + senha configurados pelo Terceiro via /api/v1/smtp |

## Troubleshooting

| Sintoma                                            | Causa provavel                                               | Solucao                                                                     |
| -------------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------- |
| `curl` para /health falha                          | Backend nao esta rodando                                     | Verificar processo uvicorn ou Windows Service TimesheetBackend              |
| Mailhog nao acessivel em :8025                     | Container nao subiu                                          | `make smtp-up` e verificar Docker Desktop                                   |
| SQLCipher: file is not a database                  | TIMESHEET_DB_CIPHER_KEY incorreta                            | Verificar .env e recriar banco com `make data-dir`                          |
| E2E Playwright falha ao conectar                   | Backend ou frontend nao esta rodando                         | Rodar `make smtp-up` e verificar webServer config no playwright.config.ts   |
| Windows Service nao inicia (trava em START_PENDING) | Handshake SCM ausente ou binario sem hiddenimports pywin32  | Rebuild com `make build` (requer PyInstaller spec atualizado com pywin32 hiddenimports e launcher.py com TimesheetBackendService) |
| Windows Service nao inicia (MSI instala mas servico nao responde) | Argumento `service` ausente no binPath do ServiceInstall | Verificar `Components.wxs`: `ServiceInstall` do TimesheetBackend deve ter `Arguments=" service"` |
| PDF nao gerado: WeasyPrint erro                    | DLLs libpango/libcairo ausentes no bundle                    | Verificar PyInstaller spec para incluir DLLs necessarias                    |
