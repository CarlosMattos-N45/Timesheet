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
