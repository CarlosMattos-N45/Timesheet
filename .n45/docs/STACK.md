---
layers:
    - items:
        architecture: Slices verticais por domínio (auth, terceiros, jornadas, marcacoes, atividades, justificativas, auditoria, relatorios, historico_envio)
        auth: python-jose (JWT) + passlib[argon2]
        crypto: DPAPI/fallback KEK + HKDF-Expand + AES-GCM
        email: smtplib + Jinja2
        framework: FastAPI + Uvicorn single-worker
        linter: ruff check apps/api && mypy --strict apps/api/app
        logging: structlog JSON rotativo
        migrations: Alembic
        orm: SQLAlchemy 2.x async (aiosqlite)
        pdf: WeasyPrint + Jinja2
        rate_limiting: slowapi + limits
        scheduler: APScheduler in-process (SQLite jobstore)
        service_mode: Windows Service via pywin32 (servicemanager + win32serviceutil) — handshake SCM START_PENDING→RUNNING→STOPPED
      name: backend
      technology: Python 3.12 (PyInstaller onefile)
    - items:
        architecture: Slices verticais por feature/página
        build: Vite
        forms: React Hook Form + Zod
        http: Axios + interceptor JWT refresh automático
        i18n: pt-BR fixo na v1.0
        linter: npm run lint
        routing: React Router v6
        state: TanStack Query v5
        ui: Material UI (MUI) v5 — WCAG 2.1 AA
      name: frontend
      technology: React 18 + TypeScript
    - items:
        http: HttpClient + Polly (circuit breaker + retry exponencial)
        inactivity: Win32 GetLastInputInfo via P/Invoke (polling 30s)
        ipc: Named pipes (Service <-> WPF UI)
        linter: dotnet build (warnings as errors)
        logging: Serilog JSON rotativo
        orm: EF Core + Microsoft.Data.Sqlite
        platform: Windows 10 1809+ / Windows 11
        ui: WPF + NotifyIcon (tray)
      name: agent
      technology: .NET 8 LTS (self-contained single-file win-x64)
    - items:
        agent_db: C:\\ProgramData\\TimesheetTerceiros\\agent-queue.sqlite (produção)
        backend_db: C:\\ProgramData\\TimesheetTerceiros\\timesheet.sqlite (produção)
        conventions: snake_case, UUID TEXT como PK, ISO 8601 UTC para timestamps
        dev_path: ./data/ (desenvolvimento local)
        kek: C:\\ProgramData\\TimesheetTerceiros\\key.kek (DPAPI LocalSystem em produção)
        pragmas: WAL mode + foreign_keys ON
        scheduler_db: C:\\ProgramData\\TimesheetTerceiros\\scheduler.sqlite (APScheduler)
      name: database
      technology: SQLite + SQLCipher
    - items:
        ci_e2e: GitHub Actions windows-latest — Playwright E2E + Mailhog
        ci_pr: GitHub Actions windows-latest — lint + test + build em cada PR
        ci_release: GitHub Actions em tag vX.Y.Z — build MSI + smoke + assinatura condicional + GitHub Release
        dev_infra: docker-compose.dev.yml (Mailhog SMTP fake)
        installer: WiX MSI — 2 Windows Services (TimesheetBackend, TimesheetAgent) + ProgramData ACLs
      name: infra
      technology: WiX Toolset (MSI) + GitHub Actions
    - items:
        agent_cmd: dotnet test apps/agent/Timesheet.Agent.sln
        backend_cmd: cd apps/api && pytest
        backend_coverage: "80"
        backend_linter: ruff check apps/api && mypy --strict apps/api/app
        e2e_cmd: cd apps/web && npx playwright test
        frontend_cmd: npm test
        frontend_coverage: "80"
        smoke_cmd: make smoke
      name: tests
      technology: pytest + Vitest + xUnit + Playwright
    - items:
        alembic: latest — backend — migrations
        apscheduler: latest — backend — scheduler
        axios: latest — frontend — HTTP client
        ef_core: latest — agente — ORM SQLite
        fastapi: latest — backend — HTTP framework
        mui: v5 — frontend — componentes de UI
        passlib_argon2: latest — backend — password hashing
        playwright: latest — e2e — testes de ponta a ponta
        polly: latest — agente — resiliência HTTP
        pyinstaller: latest — backend — empacotamento Python
        python_jose: latest — backend — JWT
        pywin32: latest — backend — handshake SCM Windows Service (win32serviceutil, win32service, win32event, servicemanager, win32api)
        react: 18 — frontend — UI framework
        react_hook_form: latest — frontend — formulários
        serilog: latest — agente — logging
        slowapi: latest — backend — rate limiting
        sqlalchemy: 2.x — backend — ORM async
        structlog: latest — backend — logging estruturado
        tanstack_query: v5 — frontend — data fetching e cache
        weasyprint: latest — backend — geração de PDF
        wix_toolset: latest — installer — empacotamento MSI
        zod: latest — frontend — validação de schema
      name: deps
      technology: null
    - items:
        bind: 127.0.0.1:8765 (configurável via MSI TIMESHEET_PORT)
        docs: OpenAPI habilitado apenas com TIMESHEET_DEV=true
        versioning: /api/v1/
      name: api
      technology: REST
    - items:
        agent_token: DpapiTokenStore — tokens do Agente protegidos via DPAPI (LocalSystem)
        password_hashing: argon2id via passlib
        rate_limiting: ≤5 tentativas/min por IP+email em /auth/login; ≤10/min em /auth/refresh
        revocation: Revogação em cadeia na troca de senha; revoga todos os refresh tokens ativos
        strategy: JWT access token (15 min) + refresh token (30 dias com rotation obrigatória)
        token_storage: Refresh tokens persistidos em SQLite (tabela refresh_token)
      name: auth
      technology: JWT + Argon2id
n45_version: 0.2.0
updated_at: YYYY-MM-DD hh:mm:ss
---

<!-- Notas adicionais -->
<!-- Sistema full-local: sem dependências de cloud ou banco externo em produção. -->
<!-- Backend Python embarcado via PyInstaller; Agente .NET publicado como single-file self-contained. -->
<!-- Em desenvolvimento, apenas Mailhog (Docker) é necessário como dependência externa. -->
<!-- fix-0002: pywin32 explicitado em deps após implementação do handshake SCM do Windows Service. -->
