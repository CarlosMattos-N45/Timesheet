---
checkpoint: null
complexity: P
created_at: "2026-06-01 09:06:47"
criteria:
    - done: false
      test: actionlint .github/workflows/e2e.yml
      text: actionlint valida e2e.yml sem erros de schema
    - done: false
      test: grep -F windows-latest .github/workflows/e2e.yml
      text: Job e2e roda em windows-latest
    - done: false
      test: grep -F docker compose .github/workflows/e2e.yml
      text: Workflow sobe o Mailhog via docker compose antes da suite
    - done: false
      test: grep -F run e2e .github/workflows/e2e.yml
      text: Workflow roda a suite Playwright via npm run e2e com CI=true
    - done: false
      test: grep -F playwright-report .github/workflows/e2e.yml
      text: Em falha anexa o playwright-report como artefato
    - done: false
      test: grep -F playwright install .github/workflows/e2e.yml
      text: Workflow instala o browser chromium do Playwright
deps:
    - TASK-039
    - TASK-041
id: TASK-043
linter: actionlint .github/workflows/e2e.yml
n45_version: 0.2.0
persona: devops
phase: Phase 8 — CI/CD
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: actionlint .github/workflows/e2e.yml
title: 'E2E no CI: workflow GitHub Actions (windows-latest) rodando a suite Playwright (4 jornadas) com Mailhog via docker compose'
updated_at: "2026-06-01 09:06:47"
---
## Contexto

Segunda task da Phase 8 — CI/CD. A suíte E2E Playwright já existe e está verde localmente (Phase 7): `apps/web/e2e/specs` cobre os fluxos da Spec §9 — "Onboarding completo", "Dia normal", "Ajuste manual" e "Envio de relatório". A config `apps/web/playwright.config.ts` já sobe os servidores via `webServer`: (1) backend `alembic upgrade head && uvicorn app.main:app --host 127.0.0.1 --port 8765` num banco e2e isolado (`sqlite+aiosqlite:///./data/e2e.sqlite`, `TIMESHEET_DEV=true`, rate limit elevado), com `url: http://127.0.0.1:8765/api/v1/ready`; (2) frontend `node node_modules/vite/bin/vite.js` em `http://127.0.0.1:5173`. A config já trata `process.env.CI` (reporter `github`, `retries: 1`, `forbidOnly`, `reuseExistingServer: false`). O alvo de Makefile `web-e2e` remove o banco e2e antigo, sobe o Mailhog (`docker compose -f docker-compose.dev.yml up -d mailhog`) e roda `npm run e2e`. O fluxo "Envio de relatório" usa o **Mailhog real** (SMTP fake em `localhost:1025`, UI `localhost:8025`) para inspecionar o e-mail enviado.

Esta task cria **somente** o workflow de E2E (`.github/workflows/e2e.yml`) — arquivo separado do `ci.yml` (TASK-042) e do `release.yml` (TASK-044) para permitir paralelismo sem conflito de merge. O job roda em `windows-latest` (mesmo motivo do CI: `pywin32`, WeasyPrint Windows-native, e o backend só roda em Windows).

**Decisão sobre o Mailhog no runner (trade-off):** o `windows-latest` da GitHub-hosted vem com Docker. O Mailhog é imagem Linux; `windows-latest` suporta containers Linux via Docker Desktop pré-instalado. O job replica `make web-e2e`: sobe o Mailhog via `docker compose -f docker-compose.dev.yml up -d mailhog` antes de rodar a suíte. Alternativa descartada: rodar Mailhog como service container do GitHub Actions — service containers Linux **não** são suportados em runners Windows, então a abordagem via `docker compose` (já validada localmente no `make web-e2e`) é a única viável.

## Comportamento Esperado

O workflow dispara em `pull_request` (branches `main`), em `push` para `main`, e permite disparo manual (`workflow_dispatch`). Único job `e2e` em `windows-latest` que: instala Python+Node, instala deps do backend e do frontend, instala o browser do Playwright (chromium), sobe o Mailhog via docker compose, roda a suíte Playwright com `CI=true`, e em caso de falha publica o relatório HTML do Playwright como artefato.

**Exemplos (entrada → efeito esperado):**

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| PR cuja suíte E2E passa (4 jornadas verdes) | Job `e2e` conclui com sucesso; checkrun verde |
| PR que quebra a jornada "Ajuste manual" (spec falha) | `playwright test` retorna exit ≠ 0; job `e2e` falha; relatório HTML é anexado como artefato `playwright-report` |
| Mailhog não sobe (docker indisponível) | Passo `docker compose up -d mailhog` falha → job falha antes de rodar specs (fail-fast), sem mascarar como sucesso |
| `actionlint .github/workflows/e2e.yml` | exit 0 — YAML válido |

## O que Implementar

Criar `.github/workflows/e2e.yml`. Persona devops — sem TDD. Verificação: `actionlint` valida o YAML; a suíte real (já verde na Phase 7) roda no job. O executor **deve** rodar `actionlint` antes de retornar; rodar a suíte completa no runner não é exigido localmente, mas os comandos devem ser idênticos aos do `make web-e2e` já validado.

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `.github/workflows/e2e.yml` | Criar | Workflow E2E em `windows-latest`: setup Python+Node, install deps, `playwright install chromium`, sobe Mailhog via docker compose, roda `npm run e2e` com `CI=true`, anexa relatório em falha |

### Detalhamento Técnico

1. **Triggers:** `on: { pull_request: { branches: [main] }, push: { branches: [main] }, workflow_dispatch: {} }`. `permissions: { contents: read }`. `concurrency: { group: "e2e-${{ github.ref }}", cancel-in-progress: true }`.

2. **Job `e2e`** (`runs-on: windows-latest`):
   - `actions/checkout@v4`
   - `actions/setup-python@v5` (`python-version: "3.12"`, `cache: pip`)
   - `actions/setup-node@v4` (`node-version: "20"`, `cache: npm`, `cache-dependency-path: apps/web/package-lock.json`)
   - **Install backend deps:** `pip install -e ".[dev]"` no `apps/api` (precisa de `alembic`, `uvicorn`, app completo — o `webServer` do Playwright roda `alembic upgrade head && uvicorn ...`). Rodar com `working-directory: apps/api` ou `cd apps/api && pip install -e ".[dev]"`.
   - **Install frontend deps:** `npm ci` em `apps/web`.
   - **Install Playwright browser:** `npx playwright install --with-deps chromium` em `apps/web` (o script `e2e:install` faz isso; chamar direto).
   - **Sobe Mailhog:** `docker compose -f docker-compose.dev.yml up -d mailhog` na raiz. Aguardar healthy — o alvo `make smtp-up` faz polling de `docker inspect -f '{{.State.Health.Status}}' timesheet-mailhog` (30× 1s). Replicar esse wait inline (step `shell: pwsh` com loop contador/timeout), pois a config Playwright **não** espera o Mailhog (só espera backend `/ready` e Vite).
   - **Roda E2E:** `npm run e2e` em `apps/web` com `env: { CI: "true" }`. A config Playwright já cuida de `forbidOnly`, `retries: 1`, reporter `github`+`html`, e `reuseExistingServer: false` quando `CI`. O `webServer` do backend já limpa/migra o banco e2e isolado; o `make web-e2e` remove `apps/api/data/e2e.sqlite` antes — replicar esse cleanup num step `shell: pwsh` antes de rodar a suíte (`if (Test-Path apps/api/data/e2e.sqlite) { Remove-Item apps/api/data/e2e.sqlite -Force }`).
   - **Relatório em falha:** step final com `if: failure()` usando `actions/upload-artifact@v4` (`name: playwright-report`, `path: apps/web/playwright-report`, `retention-days: 7`).

3. **Teardown Mailhog:** step final `if: always()` com `docker compose -f docker-compose.dev.yml down -v` (idempotente; não falha o job).

**Exemplo de implementação (trecho):**

```yaml
name: E2E

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  workflow_dispatch: {}

permissions:
  contents: read

concurrency:
  group: "e2e-${{ github.ref }}"
  cancel-in-progress: true

jobs:
  e2e:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: apps/web/package-lock.json
      - name: Install backend deps
        run: pip install -e ".[dev]"
        working-directory: apps/api
      - name: Install frontend deps
        run: npm ci
        working-directory: apps/web
      - name: Install Playwright browser
        run: npx playwright install --with-deps chromium
        working-directory: apps/web
      - name: Start Mailhog
        shell: pwsh
        run: |
          docker compose -f docker-compose.dev.yml up -d mailhog
          $max = 30
          for ($i = 1; $i -le $max; $i++) {
            $state = (docker inspect -f '{{.State.Health.Status}}' timesheet-mailhog 2>$null)
            if ($state -eq 'healthy') { Write-Host '[mailhog] healthy'; exit 0 }
            Start-Sleep -Seconds 1
          }
          Write-Error '[mailhog] nao ficou healthy em 30s'; exit 1
      - name: Clean e2e db
        shell: pwsh
        run: if (Test-Path apps/api/data/e2e.sqlite) { Remove-Item apps/api/data/e2e.sqlite -Force }
      - name: Run Playwright E2E
        run: npm run e2e
        working-directory: apps/web
        env:
          CI: "true"
      - name: Upload Playwright report
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: apps/web/playwright-report
          retention-days: 7
      - name: Stop Mailhog
        if: always()
        run: docker compose -f docker-compose.dev.yml down -v
```

## Refatoração

Nenhuma — task cria um arquivo novo de workflow; a suíte E2E e a config Playwright já existem e não são alteradas.
