---
branch: feat/0002
created_at: "2026-06-02 16:42:28"
id: fix-0002-backend-nao-roda-como-windows-service-handshake-scm-ausente
n45_version: 0.2.0
phases:
    - name: Phase 1 — Handshake SCM do Backend
      status: done
      tasks:
        - complexity: M
          deps: []
          id: TASK-001
          persona: backend
          status: done
          title: Modo Windows Service no launcher.py (handshake SCM) + seleção de modo console/serviço + testes
        - complexity: P
          deps: []
          id: TASK-002
          persona: backend
          status: done
          title: Hidden imports do pywin32 service no timesheet-backend.spec
        - complexity: P
          deps: []
          id: TASK-003
          persona: devops
          status: done
          title: Argumento 'service' no binPath do ServiceInstall do TimesheetBackend (Components.wxs)
status: validating
updated_at: "2026-06-02 17:13:56"
---
