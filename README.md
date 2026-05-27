# Timesheet Terceiros

## Visão Geral

Sistema full-local de marcação de jornada para terceiros da C&M Tecnologia. Composto por um backend Python (FastAPI), uma SPA web (React) e um agente desktop (.NET 8) que registra os pontos diretamente na máquina do colaborador, sem depender de conectividade externa.

## Estrutura

```
.
├── apps/
│   ├── agent/        # Agente desktop .NET 8
│   ├── api/          # Backend FastAPI (Python 3.12)
│   ├── installer/    # Instalador Windows
│   └── web/          # SPA React (Node 20.x)
├── packages/
│   └── contracts/    # Tipos e contratos compartilhados entre apps
├── .gitignore
├── Makefile
└── README.md
```

## Pré-requisitos

- Python 3.12
- Node 20.x LTS
- .NET 8 SDK
- Windows 10 1809+ ou Windows 11

## Como rodar

```bash
make help
```

Lista todos os comandos disponíveis no projeto.

## Smoke test

`make smoke` valida o pipeline completo da Phase 1 — Scaffold Mínimo — executando, em sequência, os três verifiers:

1. **`make api-smoke`** — sobe o backend FastAPI em background, aguarda até 10s pelo endpoint `/api/v1/health` retornar `{"status":"ok","version":"0.1.0"}` e encerra o processo.
2. **`make web-smoke`** — executa `npm run build` em `apps/web` (inclui `tsc --noEmit` + Vite build), validando que o frontend compila sem erros de tipo.
3. **`make agent-smoke`** — executa `dotnet build` e `dotnet test` na solution `Timesheet.Agent.sln`, garantindo que o agente .NET compila e seus testes passam.

Qualquer falha interrompe o processo com exit ≠ 0. Sucesso completo imprime `[SMOKE OK]`.

```bash
make smoke      # pipeline completo
make api-smoke  # apenas backend
make web-smoke  # apenas frontend
make agent-smoke # apenas agente .NET
```
