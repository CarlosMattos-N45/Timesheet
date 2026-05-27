---
checkpoint: null
complexity: P
created_at: "2026-05-27 14:08:27"
criteria:
    - done: false
      test: make help
      text: make help imprime a lista de comandos disponiveis
    - done: false
      text: Pastas apps/api apps/web apps/agent apps/installer packages/contracts existem versionadas via .gitkeep
    - done: false
      test: git check-ignore -q .env
      text: Arquivos .env são ignorados pelo git
    - done: false
      test: git check-ignore -q apps/api/__pycache__/foo.pyc
      text: Diretorios __pycache__ sao ignorados pelo git
    - done: false
      test: git check-ignore -q apps/web/node_modules/x
      text: Diretorios node_modules sao ignorados pelo git
    - done: false
      test: git check-ignore -q apps/agent/bin/Debug/foo.dll
      text: Diretorios bin obj sao ignorados pelo git
    - done: false
      text: README.md em pt-BR contem secoes Visao Geral Estrutura Pre-requisitos Como rodar
deps: []
id: TASK-001
n45_version: 0.2.0
persona: backend
phase: Phase 1 — Scaffold Mínimo
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
title: 'Monorepo: .gitignore, Makefile mínimo, README e estrutura de pastas'
updated_at: "2026-05-27 14:08:27"
---
## Contexto

Projeto greenfield: monorepo Windows-native que abriga Backend Python (FastAPI), Web SPA (React) e Agente Desktop (.NET 8). Não há arquivos pré-existentes — esta task é a primeira escrita.

Esta task cria a fundação do repositório: `.gitignore` unificado (cobrindo Python, Node, .NET, segredos), `Makefile` mínimo com targets de help, esqueleto de pastas das três aplicações + installer + contracts compartilhados, e `README.md` inicial com instruções de bootstrap. Sem código de aplicação ainda — cada app é scaffoldada em tasks dependentes (TASK-002 Backend, TASK-003 Web, TASK-004 Agente).

Todas as outras tasks da Phase 1 dependem desta porque importam decisões dela: localização das pastas (`/apps/api`, `/apps/web`, `/apps/agent`), entrada do Makefile, padrão de ignore.

## Comportamento Esperado

O repositório recém-clonado pode ser explorado e ler `README.md` orienta o desenvolvedor. `git status` em uma instalação Python/Node/.NET local não suja com diretórios `__pycache__`, `node_modules`, `bin/`, `obj/`, `.env`. `make help` lista os comandos disponíveis (mesmo que ainda sejam só `help`).

**Exemplos (entrada / ação → saída / efeito esperado)** — valores reais:

| Entrada / Ação                                              | Saída / Efeito esperado                                                                          |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `make help`                                                 | Imprime `Comandos disponíveis:` seguido das linhas `help` e `smoke` (mesmo que `smoke` ainda não exista — virá em TASK-005, aqui só `help`) |
| `ls apps/`                                                  | Linhas: `agent`, `api`, `installer`, `web` (ordem alfabética; pastas existem mesmo se vazias com `.gitkeep`) |
| `ls packages/`                                              | Linha única: `contracts`                                                                         |
| Criar arquivo `apps/api/__pycache__/foo.pyc` e rodar `git status` | `__pycache__/` ignorado — `git status` não lista o arquivo                                       |
| Criar arquivo `.env` na raiz e rodar `git status`           | `.env` ignorado — `git status` não lista o arquivo                                               |
| Criar arquivo `apps/web/node_modules/x` e rodar `git status`| `node_modules/` ignorado                                                                         |
| Criar arquivo `apps/agent/bin/Debug/foo.dll` e rodar `git status` | `bin/` ignorado em todos os níveis                                                          |

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                              | Ação  | Descrição                                                                                                                                                                  |
| ------------------------------------ | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.gitignore`                         | Criar | Ignora artefatos Python (`__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `build/`, `*.egg-info/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `coverage.xml`, `.coverage`), Node (`node_modules/`, `dist/`, `build/`, `.vite/`, `coverage/`), .NET (`bin/`, `obj/`, `*.user`, `*.suo`, `.vs/`, `TestResults/`), IDE (`.idea/`, `.vscode/`), segredos (`.env`, `.env.local`, `*.kek`, `*.sqlite`, `*.sqlite-journal`, `*.sqlite-wal`, `*.sqlite-shm`), OS (`Thumbs.db`, `.DS_Store`)  |
| `Makefile`                           | Criar | Target `help` (default) com `@echo` listando comandos. Convenção `.PHONY`. Sem outros targets nesta task — TASK-002/003/004 adicionam o seu, TASK-005 adiciona `smoke`     |
| `README.md`                          | Criar | Visão geral em pt-BR: o que é o projeto (1 parágrafo), estrutura de pastas, pré-requisitos (Python 3.12, Node 20, .NET 8 SDK), como rodar `make help`. Sem detalhes de execução das apps ainda (esses ficam no RUNBOOK em fases posteriores)                                                                              |
| `apps/api/.gitkeep`                  | Criar | Manter pasta vazia versionada                                                                                                                                              |
| `apps/web/.gitkeep`                  | Criar | Manter pasta vazia versionada                                                                                                                                              |
| `apps/agent/.gitkeep`                | Criar | Manter pasta vazia versionada                                                                                                                                              |
| `apps/installer/.gitkeep`            | Criar | Manter pasta vazia versionada                                                                                                                                              |
| `packages/contracts/.gitkeep`        | Criar | Manter pasta vazia versionada                                                                                                                                              |

### Detalhamento Técnico

1. Criar todas as pastas listadas com `.gitkeep` vazio em cada uma (git não versiona diretório vazio).
2. `Makefile` usa **tabs** para indentar receitas (regra do GNU Make). Target `help` deve ser o **primeiro** (default ao digitar `make`). Não usar `@echo` em uma única linha gigante — uma linha por comando para legibilidade.
3. `.gitignore` é a **única lista de exclusões** do repositório por ora. Sem `.gitignore` por subpasta — centralizar facilita revisão. Cada categoria com comentário (`# Python`, `# Node`, `# .NET`, etc).
4. `README.md` em pt-BR, com headings `## Visão Geral`, `## Estrutura`, `## Pré-requisitos`, `## Como rodar`. Pré-requisitos cita versões exatas: Python 3.12, Node 20.x LTS, .NET 8 SDK, Windows 10 1809+/11.

**Exemplo de Makefile:**

```makefile
.PHONY: help

help:
	@echo "Comandos disponíveis:"
	@echo "  help    - mostra esta mensagem"
```

**Exemplo de .gitignore (trecho):**

```
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
coverage.xml
.coverage

# Node
node_modules/
.vite/

# .NET
bin/
obj/
*.user
*.suo
.vs/
TestResults/

# Segredos / banco local
.env
.env.local
*.kek
*.sqlite
*.sqlite-journal
*.sqlite-wal
*.sqlite-shm

# Build / dist
dist/
build/

# IDE
.idea/
.vscode/

# OS
Thumbs.db
.DS_Store
```

**Refatoração:** Nenhuma — task inicial sem código prévio.
