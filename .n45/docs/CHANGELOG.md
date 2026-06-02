---
entries:
    - date: "2026-06-02"
      feature: hot-fix/backend-boot-204-email-validator
      summary: |
        ### Corrigido

        - Backend não subia em instalação limpa: declarada a dependência `email-validator` (via `pydantic[email]`), antes ausente apesar do uso de `EmailStr`.
        - Corrigidas 4 rotas `204 No Content` que quebravam o registro de rotas na FastAPI 0.115.x. Com `from __future__ import annotations` (PEP 563), o retorno `-> None`/`-> FileResponse` era inferido como `response_model`, disparando o assert de "status 204 não pode ter corpo". Adicionado `response_model=None` explícito em `/auth/logout`, `/privacidade/aceitar`, `/terceiros/me/senha` e no catch-all SPA. Incluído teste de regressão de import/startup.
      version: Unreleased
    - date: "2026-06-01"
      feature: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
      summary: |
        ### Adicionado

        - Monorepo com estrutura de pastas, Makefile, .gitignore e README em pt-BR (TASK-001)
        - Backend FastAPI com GET /api/v1/health, ruff + mypy strict, pytest ≥ 80% cobertura (TASK-002)
        - Frontend React 18 + Vite + TypeScript + MUI scaffold em apps/web (TASK-003)
        - Agente .NET 8 solution scaffold com 7 projetos e xUnit em apps/agent (TASK-004)
        - Smoke verifier: make smoke validando api/health + web dev + agent build (TASK-005)
        - Infra de desenvolvimento: docker-compose.dev.yml com Mailhog + Makefile smtp-* + .env.example (TASK-006)
        - Alembic setup + migration 0001_initial com 11 tabelas (terceiro, jornada, marcacao, atividade, justificativa, log_auditoria, historico_envio_relatorio, smtp_config, refresh_token, privacidade, agente_estado) (TASK-007)
        - SQLAlchemy 2.x async engine + sessionmaker + DI get_session + PRAGMAs WAL/FK + suporte SQLCipher (TASK-008)
        - Módulo de criptografia: KEK ensure (DPAPI/fallback) + HKDF-Expand + helpers AES-GCM (TASK-009)
        - ORM SQLAlchemy 2.x: Base + 11 modelos em slices verticais por domínio (TASK-010)
        - EF Core Agente: 3 POCOs + AgentDbContext + migration Initial + testes xUnit (TASK-011)
        - Fundação backend: errors padronizados, security helpers, middleware de logging/rate-limit, audit helpers, DI de dependências (TASK-012)
        - Autenticação JWT (access 15 min + refresh 30 dias com rotation) + Terceiros com single-tenant guard e validação de CNPJ (TASK-013)
        - Endpoint de privacidade: GET /api/v1/privacidade + POST /aceitar singleton idempotente (TASK-014)
        - SMTP Config: GET/PUT /api/v1/smtp + POST /smtp/test, cifragem AES-GCM, crypto_state (TASK-015)
        - Marcações: POST/GET/PUT com idempotency_key, auto-criação de jornada, RN-012 (regra de conflito Agente vs Web), verificação de fim de semana e audit log (TASK-016)
        - Jornadas + Atividades + Justificativas + Auditoria — slice vertical completo com endpoints REST (TASK-017)
        - Relatórios: geração de PDF via WeasyPrint + Jinja2, APScheduler in-process (dia 1 de cada mês), envio SMTP, histórico de envio e endpoints /relatorios (TASK-018)
        - Wiring final: registra todos os routers, /api/v1/ready e /api/v1/config (TASK-019)
        - Fundação frontend: Axios + interceptor JWT refresh automático, AuthContext, QueryClient, React Router, PrivacyGuard, AppLayout, types e helpers (TASK-020)
        - Página /login com saudação contextual (Bom dia/tarde/noite), form React Hook Form + Zod, tratamento de erros 401/429/rede (TASK-021)
        - Página /privacidade one-time modal (RF-012) com aceite persistido localmente (TASK-022)
        - Página /jornadas com DataGrid mensal, DatePicker, chips de status, download e envio de PDF (TASK-023)
        - Página /jornadas/:id (Detalhe) com edição de horários, atividade inline e accordion de auditoria (TASK-024)
        - Página /jornadas/manual para criação manual de jornada sem eventos (TASK-025)
        - Páginas /cadastro e /senha com PUT /terceiros e troca de senha (revogação de refresh tokens ativos) (TASK-026)
        - Páginas /relatorios e /configuracoes/smtp (RF-008) (TASK-027)
        - Fundação do Agente .NET: IClock, constantes de domínio, 3 repositórios SQLite, contrato IPC e AddAgentInfra (TASK-028)
        - Infra HTTP do Agente: BackendClient + Polly (circuit breaker + retry exponencial) para todos os endpoints do backend (TASK-029)
        - Domain: máquina de estados de jornada pura implementando RF-003/004/005/006 (TASK-030)
        - Detecção de input: InactivityTracker + Win32LastInputProvider + SessionMonitor (TASK-031)
        - IPC named pipe: DialogCorrelator, IpcServer, IpcClient, NamedPipeChannel, IdentityGuard (TASK-032)
        - Service host: SyncProcessor (drena fila RN-012 + backoff), DecisionApplier, hosted services e Program.cs wiring (TASK-033)
        - WPF UI: wizard de cadastro (RF-002), diálogos modais de confirmação, tray icon, validadores CNPJ/horários/senha (TASK-034)
        - Token persistence: DpapiTokenStore (ProtectedData DPAPI) + TokenManager com refresh automático (TASK-035)
        - Backend launcher de produção + serve SPA estática embutida + bundle PyInstaller onefile (TASK-036)
        - Publish .NET self-contained single-file win-x64 para TimesheetAgent.Service e TimesheetAgent.Ui (TASK-037)
        - Instalador WiX MSI: 2 Windows Services, ACLs ProgramData, Makefile build/release, RUNBOOK Aplicacao (TASK-038)
        - Setup E2E: Playwright + config webServer, seed idempotente, fixtures e spec de infraestrutura (TASK-039)
        - Smoke test E2E cobrindo caminho crítico: login → privacidade → jornada manual → lista (TASK-040)
        - Specs E2E completos: Onboarding, Dia normal (agente), Ajuste manual e Envio de relatório (TASK-041)
        - Workflow GitHub Actions CI de PR: 3 jobs windows-latest (lint, test, build) (TASK-042)
        - Workflow GitHub Actions E2E no CI: windows-latest + Playwright + Mailhog (TASK-043)
        - Workflow GitHub Actions Release em tag vX.Y.Z: build MSI, smoke, assinatura condicional e publicação de Release com artefatos (TASK-044)
      version: 0.1.0
n45_version: 0.2.0
---
