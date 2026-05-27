---
health_checks:
    - command: curl -fsS http://localhost:8025
      service: mailhog
      type: infra
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

- Backend: SQLite + SQLCipher em `./data/timesheet.sqlite` (dev). Em producao, `%APPDATA%\TimesheetTerceiros\timesheet.sqlite` provisionado pelo MSI.
- Agente: SQLite em `./data/agent-queue.sqlite` (dev) ou `%APPDATA%\TimesheetTerceiros\agent-queue.sqlite` (producao).
- KEK: `./data/key.kek` (dev, gerada na primeira execucao se ausente). Em producao, protegida por DPAPI.

> Secao "Aplicacao" sera adicionada pela Phase 5 (Containerizacao / Empacotamento).
