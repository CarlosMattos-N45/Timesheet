---
checkpoint: null
complexity: M
created_at: "2026-05-27 15:52:02"
criteria:
    - done: false
      test: docker compose -f docker-compose.dev.yml config
      text: docker compose -f docker-compose.dev.yml config retorna 0 com servico mailhog
    - done: false
      test: make smtp-up
      text: make smtp-up sobe mailhog e fica healthy em <=30s
    - done: false
      test: make smtp-down
      text: make smtp-down derruba mailhog e remove volume
    - done: false
      test: make help
      text: make help lista smtp-up smtp-down smtp-status data-dir
    - done: false
      test: grep -E TIMESHEET_DB_URL apps/api/.env.example
      text: TIMESHEET_DB_URL presente no .env.example com driver aiosqlite
    - done: false
      test: grep -E TIMESHEET_KEK_PATH apps/api/.env.example
      text: TIMESHEET_KEK_PATH presente no .env.example apontando para data/key.kek
    - done: false
      test: grep -E TIMESHEET_SMTP apps/api/.env.example
      text: TIMESHEET_SMTP_HOST e TIMESHEET_SMTP_PORT presentes no .env.example
    - done: false
      test: git check-ignore -q data/x
      text: data/ ignorada pelo git
    - done: false
      test: grep -E mailhog/mailhog:v1.0.1 docker-compose.dev.yml
      text: Imagem mailhog pinada por tag v1.0.1 sem latest
    - done: false
      test: grep -E timesheet-mailhog-data docker-compose.dev.yml
      text: Volume nomeado timesheet-mailhog-data declarado no compose
    - done: false
      test: grep -E healthcheck docker-compose.dev.yml
      text: Healthcheck do mailhog declarado com interval/retries
    - done: false
      test: grep -E max.*30 Makefile
      text: Loop de espera no smtp-up tem limite maximo de tentativas
    - done: false
      test: n45 49aefa26 --bee531 --b79b13 --a6a0ee claude
      text: RUNBOOK Infraestrutura existe com frontmatter start/stop programaticos e secao Servicos
    - done: false
      test: make smoke
      text: Phase 1 smoke continua passando sem regressao
deps: []
id: TASK-006
linter: docker compose -f docker-compose.dev.yml config
n45_version: 0.2.0
persona: devops
phase: Phase 2 — Dados
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: make smtp-up && make smtp-down
title: 'Infra Phase 2: docker-compose.dev.yml (Mailhog) + Makefile smtp-* + .env.example DB/KEK + RUNBOOK Infraestrutura'
updated_at: "2026-05-27 15:52:02"
---
## Contexto

Phase 2 — Dados inaugura a camada de persistência do projeto. Este projeto é full-local: o banco principal é SQLite + SQLCipher embarcado no processo Python do Backend, e o banco do Agente é SQLite via EF Core no executável .NET. **Não há serviços de banco externos** (sem Postgres/Redis/MinIO). A única dependência externa do sistema é o servidor SMTP — para desenvolvimento, usamos um servidor SMTP fake (Mailhog) executado via docker-compose.

Esta task é o **lote-fundação** da Phase 2: cria os artefatos compartilhados de infraestrutura que serão consumidos por todas as demais tasks da fase (Alembic, ORM, KEK, EF Core do Agente). Todas as outras tasks de Phase 2 (TASK-007 a TASK-011) dependem desta. Os artefatos criados aqui também são reutilizados pelas fases seguintes (Phase 3 backend, Phase 4 frontend, Phase 5 containerização).

Estado atual da Phase 1:

- `apps/api/app/main.py` cria `FastAPI()` com `docs_url`/`redoc_url`/`openapi_url` condicionados a `TIMESHEET_DEV`.
- `apps/api/app/core/config.py` lê env vars `TIMESHEET_DEV`, `TIMESHEET_PORT`, `TIMESHEET_HOST` via pydantic-settings.
- `apps/api/.env.example` lista apenas as 3 vars acima.
- Raiz tem `Makefile` com targets `api-dev`, `api-test`, `web-dev`, `agent-build`, `smoke`, etc.
- Não existe `docker-compose.yml` nem `docker-compose.dev.yml`. Não existe pasta `.n45/docs/RUNBOOK.md` (RUNBOOK ainda não criado).

Esta task cria os arquivos que destravam o resto da fase: configuração de banco no `.env.example`, comandos Makefile para subir/descer o Mailhog (SMTP de dev), `docker-compose.dev.yml` com o serviço, e o RUNBOOK inicial com a seção `Infraestrutura`.

## Comportamento Esperado

| Entrada / Ação                                                                    | Saída / Efeito esperado                                                                                                          |
| --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `docker compose -f docker-compose.dev.yml config`                                 | Imprime YAML válido sem erro, contém serviço `mailhog`                                                                           |
| `make smtp-up`                                                                    | Sobe `mailhog`, aguarda healthcheck (máx 30 tentativas × 1s), sai 0; container em estado `healthy`                               |
| `make smtp-down`                                                                  | Derruba o `mailhog` e remove o volume; sai 0                                                                                     |
| `make smtp-status`                                                                | Imprime estado do `mailhog` (running/stopped); sai 0                                                                             |
| `make help`                                                                       | Lista `smtp-up`, `smtp-down`, `smtp-status` entre os comandos disponíveis                                                        |
| `grep -E 'TIMESHEET_DB_URL' apps/api/.env.example`                                | Encontra linha de exemplo `TIMESHEET_DB_URL=sqlite+aiosqlite:///./data/timesheet.sqlite` comentada                                |
| `grep -E 'TIMESHEET_KEK_PATH' apps/api/.env.example`                              | Encontra linha comentada apontando para `./data/key.kek`                                                                         |
| Subir Mailhog e abrir `http://localhost:8025`                                     | UI web do Mailhog responde (200) — interface administrativa para inspecionar e-mails enviados em dev                             |
| Conectar SMTP cliente em `localhost:1025`                                         | Servidor SMTP aceita SMTP sem TLS (modo dev) — Mailhog é o sink                                                                  |
| `make smtp-up` quando porta `1025` já está ocupada                                | Falha com mensagem clara do docker compose; saída ≠ 0; não congela                                                               |
| Diretório `data/`                                                                 | Criado pelo Makefile (target `data-dir`) se não existir; serve para o SQLite local e o `key.kek` em dev                          |
| `docker-compose.dev.yml` linhas com `image: mailhog/mailhog:v1.0.1`               | Imagem pinada por tag de versão; sem `latest`                                                                                    |

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                                | Ação      | Descrição                                                                                                |
| -------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------- |
| `docker-compose.dev.yml`               | Criar     | Compose com serviço `mailhog` (SMTP fake) — única dependência externa de dev                             |
| `Makefile`                             | Modificar | Adicionar targets `smtp-up`, `smtp-down`, `smtp-status`, `data-dir` + entradas em `help` e `.PHONY`      |
| `apps/api/.env.example`                | Modificar | Adicionar vars de banco (`TIMESHEET_DB_URL`, `TIMESHEET_KEK_PATH`) e SMTP dev (`TIMESHEET_SMTP_HOST`, `TIMESHEET_SMTP_PORT`) — todas comentadas com valor default explícito |
| `.gitignore`                           | Modificar | Adicionar `data/` (pasta de dados locais com SQLite e `key.kek` em dev)                                  |
| `.n45/docs/RUNBOOK.md`                 | Criar via `n45 ... 69443222 --bee531 --1a0cb6` | Frontmatter YAML programático + seção `Infraestrutura`                                                   |

### Detalhamento Técnico

**1. `docker-compose.dev.yml`** — raiz do repositório:

```yaml
# docker-compose.dev.yml
# Serviços de dependência externa para desenvolvimento.
# Único serviço: Mailhog (servidor SMTP fake) — sink de e-mails durante dev/teste.
# O banco SQLite + SQLCipher é embarcado no processo Python, sem container.

services:
  mailhog:
    image: mailhog/mailhog:v1.0.1
    container_name: timesheet-mailhog
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web UI
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8025"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 2s
    restart: unless-stopped
    volumes:
      - mailhog-data:/maildir

volumes:
  mailhog-data:
    name: timesheet-mailhog-data
```

Observações:
- Sem `networks:` customizada — usa a rede default do compose (`default`).
- Volume nomeado `timesheet-mailhog-data` para manter e-mails entre restarts (RN: "Volume nomeado obrigatório").
- Tag de versão `v1.0.1` (não `latest`).
- Healthcheck via `wget --spider` apontando para a UI HTTP, que sobe junto com o SMTP.

**2. `Makefile`** — adicionar targets ao final do arquivo existente (sem remover targets atuais). Atualizar `.PHONY` e o bloco `help`:

```makefile
.PHONY: help smoke api-smoke web-smoke agent-smoke api-dev api-test api-lint web-dev web-build web-test web-lint agent-build agent-test agent-format smtp-up smtp-down smtp-status data-dir

# Substituir o bloco help atual por uma versão que inclua os novos comandos
help:
	@echo Comandos disponiveis:
	@echo   help          - mostra esta mensagem
	@echo   smoke         - executa os 3 smoke verifiers em sequencia
	@echo   api-smoke     - valida que o backend sobe e /api/v1/health responde 200
	@echo   web-smoke     - valida que o build de producao do frontend passa
	@echo   agent-smoke   - valida que a solution .NET compila e testes passam
	@echo   api-dev       - inicia servidor de desenvolvimento da API
	@echo   api-test      - executa testes da API
	@echo   api-lint      - executa ruff e mypy na API
	@echo   web-dev       - inicia servidor de desenvolvimento do frontend
	@echo   web-build     - build de producao do frontend
	@echo   web-test      - executa testes do frontend
	@echo   web-lint      - executa eslint e typecheck no frontend
	@echo   agent-build   - compila a solution do agente .NET
	@echo   agent-test    - executa testes do agente .NET
	@echo   agent-format  - verifica formatacao do agente .NET
	@echo   smtp-up       - sobe Mailhog (SMTP fake) via docker compose
	@echo   smtp-down     - derruba Mailhog
	@echo   smtp-status   - estado do servico Mailhog
	@echo   data-dir      - cria diretorio data/ local (SQLite + key.kek dev)

# Novos targets — colocar após o bloco existente
data-dir:
	@powershell -NoProfile -Command "if (-not (Test-Path data)) { New-Item -ItemType Directory data | Out-Null }"

smtp-up:
	docker compose -f docker-compose.dev.yml up -d mailhog
	@powershell -NoProfile -Command "$$max = 30; for ($$i = 1; $$i -le $$max; $$i++) { $$state = (docker inspect -f '{{.State.Health.Status}}' timesheet-mailhog 2>$$null); if ($$state -eq 'healthy') { Write-Host '[mailhog] healthy'; exit 0 }; Start-Sleep -Seconds 1 }; Write-Error '[mailhog] nao ficou healthy em 30s'; exit 1"

smtp-down:
	docker compose -f docker-compose.dev.yml down -v

smtp-status:
	docker compose -f docker-compose.dev.yml ps mailhog
```

Notas:
- `data-dir` é tab-indentado conforme convenção de Makefile (igual aos targets existentes).
- Loop de espera de healthcheck tem limite máximo (30 tentativas × 1s), conforme regra "Loop de espera com limite" — `until` sem limite seria tech debt.
- `smtp-down` usa `-v` para também remover o volume nomeado (estado de e-mails de dev é descartável).
- Não adicionar target `infra-up`/`infra-down` redundante: o **único serviço de infra** deste projeto é o SMTP, então `smtp-*` é semanticamente mais claro que `infra-*`.

**3. `apps/api/.env.example`** — adicionar novas vars (mantendo as 3 existentes), todas comentadas com defaults explícitos:

```dotenv
# Habilita documentacao OpenAPI (Swagger UI) em /docs
# TIMESHEET_DEV=false

# Porta do servidor local
# TIMESHEET_PORT=8765

# Host do servidor local
# TIMESHEET_HOST=127.0.0.1

# URL de conexao do banco de dominio (SQLAlchemy async + aiosqlite)
# Em producao: SQLite + SQLCipher; em dev: SQLite simples se TIMESHEET_KEK_PATH ausente.
# TIMESHEET_DB_URL=sqlite+aiosqlite:///./data/timesheet.sqlite

# Caminho do arquivo KEK (Key Encryption Key) protegido por DPAPI.
# Em producao: gerado pelo instalador MSI em %APPDATA%\TimesheetTerceiros\key.kek.
# Em dev: arquivo opcional em ./data/key.kek — se ausente, banco roda sem SQLCipher.
# TIMESHEET_KEK_PATH=./data/key.kek

# Servidor SMTP de desenvolvimento (Mailhog).
# Em producao: configuracao real do usuario via tabela smtp_config.
# TIMESHEET_SMTP_HOST=127.0.0.1
# TIMESHEET_SMTP_PORT=1025
```

Regras:
- Todas as linhas comentadas (`# VAR=valor`) — o app deve operar com defaults dos `Field()` em `config.py`; nunca exigir `.env` para subir em dev.
- Valor real, nunca placeholder (`change-me` / `<value>` / `admin`).
- Comentário acima de cada bloco explica papel da var.

**4. `.gitignore`** — adicionar `data/` em uma seção apropriada. Adicionar **antes** da seção `# Segredos / banco local` para ficar agrupado:

```gitignore
# (...) seções existentes mantidas (...)

# Segredos / banco local
.env
.env.local
*.kek
*.sqlite
*.sqlite-journal
*.sqlite-wal
*.sqlite-shm

# Dados locais de desenvolvimento (SQLite, key.kek, PDFs gerados)
data/

# (...) demais seções mantidas (...)
```

Observação: as entradas `*.sqlite`, `*.kek` já cobriam os arquivos individuais; `data/` cobre a pasta inteira (mais limpo para listar com `ls`).

**5. RUNBOOK** — criar via binary `n45 ... 69443222 --bee531 --a6a0ee claude --1a0cb6 .n45/tmp/runbook-draft.md` após escrever o draft. Estrutura do draft:

```markdown
---
start: docker compose -f docker-compose.dev.yml up -d
stop: docker compose -f docker-compose.dev.yml down
services:
  - mailhog
---

# Runbook — Timesheet Terceiros

## Infraestrutura

Este projeto é full-local: o banco SQLite + SQLCipher é embarcado no processo do Backend (sem container) e o banco do Agente é SQLite embarcado no executável .NET (sem container). A única dependência externa rodada via docker-compose em desenvolvimento é o Mailhog (servidor SMTP fake).

### Serviços

| Servico   | Imagem                 | Porta(s)        | Volume                     | Healthcheck                           |
| --------- | ---------------------- | --------------- | -------------------------- | ------------------------------------- |
| mailhog   | mailhog/mailhog:v1.0.1 | 1025 (SMTP), 8025 (UI) | timesheet-mailhog-data | wget --spider http://localhost:8025  |

### Comandos

- `make smtp-up` — sobe Mailhog e aguarda healthcheck (max 30s).
- `make smtp-down` — derruba Mailhog e remove volume.
- `make smtp-status` — exibe estado atual.

### Healthchecks manuais

- Mailhog UI: `curl -fsS http://localhost:8025` → 200.
- Mailhog SMTP: `Test-NetConnection 127.0.0.1 -Port 1025` → `TcpTestSucceeded: True`.

### Banco de dados (sem container)

- Backend: SQLite + SQLCipher em `./data/timesheet.sqlite` (dev). Em producao, `%APPDATA%\TimesheetTerceiros\timesheet.sqlite` provisionado pelo MSI.
- Agente: SQLite em `./data/agent-queue.sqlite` (dev) ou `%APPDATA%\TimesheetTerceiros\agent-queue.sqlite` (producao).
- KEK: `./data/key.kek` (dev, gerada na primeira execucao se ausente). Em producao, protegida por DPAPI.

> Secao "Aplicacao" sera adicionada pela Phase 5 (Containerizacao / Empacotamento).
```

O frontmatter `start` e `stop` devem ser **programáticos** (docker compose); nunca instruções interativas. A lista `services` espelha os serviços do compose.

## Contratos com camadas adjacentes

Esta task **produz** artefatos consumidos pelas demais tasks da Phase 2:

```
Produz para:
  - TASK-007 (Alembic): TIMESHEET_DB_URL em .env.example (driver aiosqlite, caminho data/timesheet.sqlite); make data-dir para garantir pasta antes de criar SQLite.
  - TASK-008 (SQLAlchemy session): mesmo TIMESHEET_DB_URL; conexão a SQLite local.
  - TASK-009 (KEK): TIMESHEET_KEK_PATH default ./data/key.kek; pasta data/ via make data-dir.
  - TASK-010 (ORM models): nenhum acoplamento direto.
  - TASK-011 (EF Core agent): caminho ./data/agent-queue.sqlite documentado no RUNBOOK; .env.example não cobre Agente (.NET usa appsettings.json).

Consome de: nada (lote-fundação).
```

Nenhum endpoint HTTP é alterado nesta task (sem contrato HTTP).

**Validação obrigatória pelo executor antes de marcar done:**

1. `docker compose -f docker-compose.dev.yml config` retorna 0 e imprime YAML com `mailhog`.
2. `make smtp-up` → sai 0 e o container fica `healthy`.
3. `curl -fsS http://localhost:8025` → 200.
4. `make smtp-down` → sai 0 e o container some de `docker ps`.
5. `make help` → contém as 4 novas linhas (`smtp-up`, `smtp-down`, `smtp-status`, `data-dir`).
6. `grep -E 'TIMESHEET_DB_URL' apps/api/.env.example` → match.
7. `grep -E 'TIMESHEET_KEK_PATH' apps/api/.env.example` → match.
8. `grep -E '^data/$' .gitignore` → match.
9. Após criar RUNBOOK via binary, `n45 49aefa26 --bee531 --b79b13 --a6a0ee claude` retorna `status: ok` com seção `Infraestrutura`.
10. `make smoke` (Phase 1) continua passando sem regressão.

> Executor DEVE rodar todas as validações acima e garantir saída 0 antes de retornar. Falha em qualquer passo = task não concluída.

**Refatoração:** Nenhuma — todos os arquivos modificados são pequenos e idiomáticos; o `Makefile` recebe apenas extensão por concatenação.
