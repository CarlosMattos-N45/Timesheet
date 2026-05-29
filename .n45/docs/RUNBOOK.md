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
    e2e: null
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
