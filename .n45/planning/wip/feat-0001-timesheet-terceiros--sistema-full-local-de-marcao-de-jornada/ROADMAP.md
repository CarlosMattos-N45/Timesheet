---
branch: feat/0001
created_at: "2026-05-27 14:07:30"
id: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
n45_version: 0.2.0
phases:
    - name: Phase 1 — Scaffold Mínimo
      status: done
      tasks:
        - complexity: P
          deps: []
          id: TASK-001
          persona: backend
          status: done
          title: 'Monorepo: .gitignore, Makefile mínimo, README e estrutura de pastas'
        - complexity: M
          deps:
            - TASK-001
          id: TASK-002
          persona: backend
          status: done
          title: Backend FastAPI scaffold em /apps/api com GET /api/v1/health
        - complexity: M
          deps:
            - TASK-001
          id: TASK-003
          persona: frontend
          status: done
          title: Frontend React+Vite+TS+MUI scaffold em /apps/web com página inicial
        - complexity: M
          deps:
            - TASK-001
          id: TASK-004
          persona: backend
          status: done
          title: Agente .NET 8 solution scaffold em /apps/agent com 6 projetos + xUnit
        - complexity: M
          deps:
            - TASK-002
            - TASK-003
            - TASK-004
          id: TASK-005
          persona: backend
          status: done
          title: 'Smoke verifier: Makefile com make smoke validando api/health + web dev + agent build'
    - name: Phase 2 — Dados
      status: pending
      tasks: []
    - name: Phase 3 — Backend por Domínio
      status: pending
      tasks: []
    - name: Phase 4 — Frontend por Feature
      status: pending
      tasks: []
    - name: Phase 5 — Agente Desktop
      status: pending
      tasks: []
    - name: Phase 6 — Empacotamento Windows (PyInstaller + WiX MSI)
      status: pending
      tasks: []
    - name: Phase 7 — E2E
      status: pending
      tasks: []
    - name: Phase 8 — CI/CD
      status: pending
      tasks: []
status: in-progress
updated_at: "2026-05-27 15:31:30"
---

