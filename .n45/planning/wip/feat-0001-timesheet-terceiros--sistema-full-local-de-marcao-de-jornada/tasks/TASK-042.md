---
checkpoint: null
complexity: M
created_at: "2026-06-01 09:05:39"
criteria:
    - done: false
      test: actionlint .github/workflows/ci.yml
      text: actionlint valida ci.yml sem erros de schema
    - done: false
      test: grep -F windows-latest .github/workflows/ci.yml
      text: Workflow tem 3 jobs api web agent todos em windows-latest
    - done: false
      test: grep -F cov-fail-under=80 .github/workflows/ci.yml
      text: Job api roda pytest com gate de cobertura 80 da Spec 9
    - done: false
      test: grep -F typecheck .github/workflows/ci.yml
      text: Job web roda npm run typecheck e vitest --coverage
    - done: false
      test: grep -F verify-no-changes .github/workflows/ci.yml
      text: Job agent roda dotnet format --verify-no-changes e dotnet test
    - done: false
      test: grep -F pull_request .github/workflows/ci.yml
      text: Workflow dispara em pull_request e push para main
deps:
    - TASK-019
    - TASK-027
    - TASK-035
id: TASK-042
linter: actionlint .github/workflows/ci.yml
n45_version: 0.2.0
persona: devops
phase: Phase 8 — CI/CD
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: actionlint .github/workflows/ci.yml
title: 'CI de PR: workflow GitHub Actions (windows-latest) com lint+tipagem+testes das 3 apps (api/web/agent)'
updated_at: "2026-06-01 09:05:39"
---
## Contexto

Esta é a primeira task da Phase 8 — CI/CD. O monorepo já está completo: backend FastAPI em `apps/api` (Python 3.12, lint via `ruff` + `mypy --strict`, testes via `pytest`), frontend React+Vite+TS em `apps/web` (lint via `eslint` + `tsc --noEmit`, testes via `vitest`), e agente .NET 8 em `apps/agent` (lint via `dotnet format --verify-no-changes`, testes via `dotnet test` com `coverlet.collector`). Não existe nenhum workflow de CI ainda (`.github/` não existe no repositório).

A Spec define no Quadro de Stack: **"CI/CD · GitHub Actions · Lint+testes no PR"** e em §9 Quality Gates: cobertura ≥ 80% no Backend e Web, ≥ 70% no Agente (Domain + Infra, excluindo UI WPF); lint ruff (Python) + eslint/prettier (TS) + `dotnet format` + analyzers (C#); tipagem mypy strict (Backend), `tsc --noEmit` (Web), nullable reference types (Agente).

Esta task cria **somente** o workflow de Pull Request (`.github/workflows/ci.yml`) com lint + tipagem + testes unitários das 3 aplicações. **Não** cobre E2E (TASK-043) nem build de MSI/release (TASK-044) — cada uma é um arquivo de workflow separado para permitir paralelismo sem conflito de merge.

**Por que `windows-latest` é obrigatório:** o backend depende de `pywin32` (marcado `sys_platform == 'win32'` no `pyproject.toml`) e do bundle WeasyPrint com libpango/libcairo Windows-native (Spec §7 "WeasyPrint quirk"); o agente é `net8.0-windows` com WPF. Nenhuma das 3 aplicações compila/testa em Linux. Todos os jobs rodam em `runs-on: windows-latest`.

## Comportamento Esperado

O workflow dispara em `pull_request` e em `push` para `main`. Roda 3 jobs independentes em paralelo (cada stack tem toolchain distinto). Cada job: faz checkout, instala o toolchain, instala dependências, roda lint+tipagem, roda testes com cobertura, e falha o job se lint/tipagem/teste falharem.

**Comandos canônicos já existentes no `Makefile` da raiz** (os jobs chamam os comandos diretos abaixo, não `make`):

| Aplicação | Lint + tipagem | Testes |
| --------- | -------------- | ------ |
| `apps/api` (Python 3.12) | `ruff check . && mypy --strict app` | `pytest` |
| `apps/web` (Node 20) | `npm run lint && npm run typecheck` | `npm test -- --run` |
| `apps/agent` (.NET 8) | `dotnet format Timesheet.Agent.sln --verify-no-changes` | `dotnet test Timesheet.Agent.sln -c Debug` |

**Exemplos (entrada → efeito esperado):**

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| PR aberto com `ruff check` limpo, `pytest` verde, `npm run lint`/`vitest` verdes, `dotnet test` verde | Os 3 jobs (`api`, `web`, `agent`) concluem com sucesso; checkrun do PR fica verde |
| PR com erro de lint Python (ex.: import não usado em `apps/api/app/`) | Job `api` falha no passo de lint (`ruff check` retorna exit ≠ 0); PR bloqueado |
| PR com teste de frontend quebrado (`vitest` retorna exit ≠ 0) | Job `web` falha no passo de testes; jobs `api` e `agent` continuam (jobs independentes) |
| PR com violação de formatação C# (`dotnet format --verify-no-changes` detecta diff) | Job `agent` falha no passo de lint/format; PR bloqueado |
| `actionlint .github/workflows/ci.yml` | exit 0 — YAML do workflow é sintaticamente válido e sem erros de schema |

## O que Implementar

Criar o diretório `.github/workflows/` e o arquivo `ci.yml`. Persona devops — sem TDD. A verificação é a validação do YAML (`actionlint`) e a execução real dos comandos de cada job (os mesmos que rodam localmente via `Makefile`, já validados nas fases anteriores).

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `.github/workflows/ci.yml` | Criar | Workflow de PR/push com 3 jobs (`api`, `web`, `agent`) em `windows-latest`: setup do toolchain, install de deps, lint+tipagem, testes com cobertura |

### Detalhamento Técnico

1. **Triggers:** `on: { pull_request: { branches: [main] }, push: { branches: [main] } }`. `concurrency: { group: "ci-${{ github.ref }}", cancel-in-progress: true }`. Topo: `permissions: { contents: read }`.

2. **Job `api`** (`runs-on: windows-latest`, `defaults.run.working-directory: apps/api`):
   - `actions/checkout@v4`
   - `actions/setup-python@v5` com `python-version: "3.12"` e `cache: pip`
   - Install: `pip install -e ".[dev]"` (pacote + grupo `dev`: `pytest`, `pytest-asyncio`, `httpx`, `ruff==0.7.*`, `mypy==1.13.*`). **Não instalar o grupo `build` (PyInstaller).**
   - Lint: `ruff check .`
   - Tipagem: `mypy --strict app`
   - Testes + cobertura: `pytest --cov=app --cov-report=term-missing --cov-fail-under=80` (Spec §9). `pytest-cov` não está em `dev` → `pip install pytest-cov` no job. Comentar que o threshold ≥ 80% vem da Spec §9.

3. **Job `web`** (`runs-on: windows-latest`, `defaults.run.working-directory: apps/web`):
   - `actions/checkout@v4`
   - `actions/setup-node@v4` com `node-version: "20"`, `cache: npm`, `cache-dependency-path: apps/web/package-lock.json`
   - Install: `npm ci`
   - Lint: `npm run lint`
   - Tipagem: `npm run typecheck`
   - Format check: `npm run format:check` (script já existe)
   - Testes + cobertura: `npm test -- --run --coverage` (`@vitest/coverage-v8` já é devDependency). Não alterar `vitest.config` nesta task.

4. **Job `agent`** (`runs-on: windows-latest`, `defaults.run.working-directory: apps/agent`):
   - `actions/checkout@v4`
   - `actions/setup-dotnet@v4` com `dotnet-version: "8.0.x"`
   - Restore: `dotnet restore Timesheet.Agent.sln`
   - Format check: `dotnet format Timesheet.Agent.sln --verify-no-changes --no-restore`
   - Build: `dotnet build Timesheet.Agent.sln -c Debug --no-restore`
   - Testes + cobertura: `dotnet test Timesheet.Agent.sln -c Debug --no-build --collect:"XPlat Code Coverage"` (`coverlet.collector` já referenciado). Spec §9 exclui UI WPF do gate; `Timesheet.Agent.Tests` cobre Domain+Infra.

5. **Robustez:** comandos diretos (não `make`) para erro claro. Steps PowerShell-específicos usam `shell: pwsh`. O executor deve rodar `actionlint` para validar o YAML antes de retornar.

**Exemplo de implementação (trecho):**

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: "ci-${{ github.ref }}"
  cancel-in-progress: true

jobs:
  api:
    runs-on: windows-latest
    defaults:
      run:
        working-directory: apps/api
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Install deps
        run: |
          pip install -e ".[dev]"
          pip install pytest-cov
      - run: ruff check .
      - run: mypy --strict app
      - name: Tests + coverage (>= 80% per Spec §9)
        run: pytest --cov=app --cov-report=term-missing --cov-fail-under=80

  web:
    runs-on: windows-latest
    defaults:
      run:
        working-directory: apps/web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: apps/web/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run format:check
      - run: npm test -- --run --coverage

  agent:
    runs-on: windows-latest
    defaults:
      run:
        working-directory: apps/agent
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "8.0.x"
      - run: dotnet restore Timesheet.Agent.sln
      - run: dotnet format Timesheet.Agent.sln --verify-no-changes --no-restore
      - run: dotnet build Timesheet.Agent.sln -c Debug --no-restore
      - run: dotnet test Timesheet.Agent.sln -c Debug --no-build --collect:"XPlat Code Coverage"
```

## Refatoração

Nenhuma — task cria um arquivo novo de CI; não há código de produção a refatorar.
