---
n45_version: 0.2.0
patterns:
    - description: Router → Service → Repository → DB (slices verticais por domínio)
      name: Camadas Backend
      scope: architecture
    - description: Service Host → Domain (state machine) → Infra HTTP / Infra SQLite → IPC → WPF UI
      name: Camadas Agente
      scope: architecture
    - description: 'Monorepo: apps/api (Python), apps/web (React), apps/agent (.NET), apps/installer (WiX), packages/contracts'
      name: Estrutura de Pastas
      scope: architecture
    - description: ruff format + ruff check + mypy --strict
      name: Formatação Backend
      scope: code_conventions
    - description: ESLint + Prettier (via npm run lint)
      name: Formatação Frontend
      scope: code_conventions
    - description: dotnet format (warnings as errors no build)
      name: Formatação Agente
      scope: code_conventions
    - description: snake_case para variáveis e funções Python; PascalCase para classes; snake_case no banco
      name: Nomenclatura Backend
      scope: code_conventions
    - description: PascalCase para componentes React e tipos; camelCase para hooks, funções e variáveis
      name: Nomenclatura Frontend
      scope: code_conventions
    - description: PascalCase para classes e interfaces; camelCase para variáveis e métodos; prefixo I para interfaces
      name: Nomenclatura Agente
      scope: code_conventions
    - description: Identificadores em inglês (Journey, Punch, Audit); textos visíveis e endpoints em pt-BR (/api/v1/jornadas, /api/v1/marcacoes)
      name: Identificadores de Domínio
      scope: code_conventions
    - description: 'Conventional Commits: feat, fix, docs, refactor, test, chore — sufixo [TASK-NNN] no título'
      name: Commits
      scope: code_conventions
    - description: feat/NNNN para features; fix/NNNN para correções
      name: Branches
      scope: code_conventions
    - description: 'Sucesso: payload direto (sem wrapper). Erro: {"detail": "mensagem legível"} padrão FastAPI com código HTTP semântico'
      name: Response Envelope API
      scope: response
    - description: 200 OK · 201 Created · 400 Bad Request · 401 Unauthorized · 403 Forbidden · 404 Not Found · 409 Conflict · 422 Unprocessable Entity · 429 Too Many Requests · 500 Internal Server Error
      name: HTTP Status Codes
      scope: response
    - description: 'Repository: lança exceção raw → Service: converte para domínio tipado → Router: captura e retorna HTTPException com status semântico'
      name: Erros por Camada Backend
      scope: errors
    - description: Polly gerencia retries/circuit breaker; exceções de domínio tipadas; falhas de IPC logadas e operação continua
      name: Erros Agente
      scope: errors
    - description: structlog JSON estruturado com campos level, event, timestamp; redact obrigatório de campos sensíveis (senha, token, key); sink arquivo rotativo
      name: Logging Backend
      scope: observability
    - description: Serilog JSON rotativo; Log.CloseAndFlush() no shutdown; redact obrigatório de campos sensíveis
      name: Logging Agente
      scope: observability
    - description: test_<função>_quando_<condição>_deve_<resultado> — pytest com pytest-asyncio + httpx
      name: Nomenclatura de Testes Backend
      scope: testing
    - description: describe > it('should <resultado> when <condição>') — Vitest + RTL
      name: Nomenclatura de Testes Frontend
      scope: testing
    - description: FooTests.MetodoQuandoCondicaoDeveFazerResultado — xUnit + FluentAssertions + Moq
      name: Nomenclatura de Testes Agente
      scope: testing
    - description: describe('<Feature>') > test('<ação> deve <resultado>') — Playwright
      name: Nomenclatura de Testes E2E
      scope: testing
    - description: Toda marcação carrega idempotency_key (UUID v4); backend retorna 200 em duplicata sem criar novo registro
      name: Idempotência de Marcações
      scope: architecture
    - description: AJUSTE_WEB sempre vence; senão last-write-wins por horario_efetivo; empate → Agente vence (RN-012)
      name: Regra de Conflito Agente vs Web
      scope: architecture
    - description: SQLite + SQLCipher com chave derivada via HKDF-Expand da KEK. KEK protegida por DPAPI (LocalSystem em produção) ou fallback de arquivo em dev. Configuração SMTP cifrada com AES-GCM separado
      name: Criptografia em Repouso
      scope: architecture
updated_at: YYYY-MM-DD hh:mm:ss
---

## Arquitetura

**Responsabilidade de cada camada (Backend):**

- Router: valida entrada (Pydantic), delega ao Service, serializa resposta ou lança HTTPException
- Service: orquestra lógica de negócio, não conhece HTTP nem detalhes de banco
- Repository: abstrai persistência, retorna modelos de domínio

**Responsabilidade de cada camada (Agente .NET):**

- Service Host: Windows Service, hosted services, DI root
- Domain: máquina de estados de jornada pura (sem dependências externas)
- Infra HTTP: BackendClient + Polly — comunicação com backend
- Infra SQLite: repositórios EF Core — fila local e estado do agente
- IPC: named pipes — comunicação bidirecional entre Service e WPF UI
- WPF UI: wizard de cadastro, diálogos modais, tray icon

**Estrutura de pastas:**

```
/apps/api                    # Backend Python
  /app
    /core                    # config, logging, db, security, exceptions, audit
    /modules
      /auth                  # router, service, schema, model
      /terceiros
      /jornadas
      /marcacoes
      /atividades
      /justificativas
      /auditoria
      /relatorios
      /historico_envio
      /smtp
      /privacidade
    /scheduler               # APScheduler jobs (PDF mensal)
    /pdf                     # templates Jinja2 HTML→PDF
    /static                  # build React copiado no install
    main.py                  # cria FastAPI app, registra routers
  /alembic                   # migrations Alembic
  /tests
  pyproject.toml
/apps/web                    # Frontend React
  /src
    /pages                   # Login, JornadasMes, JornadaDetalhe, JornadaManual,
                             # Cadastro, Senha, Relatorios, SMTPConfig, Privacidade
    /components              # MUI compostos reutilizáveis
    /hooks                   # useAuth, useJornadas, useRelatorios
    /api                     # axios client + React Query queries/mutations
    /lib                     # zod schemas, formatters
    /types
    App.tsx
    main.tsx
  vite.config.ts
  package.json
/apps/agent                  # Agente .NET 8
  /src
    /Timesheet.Agent.Service     # Windows Service host + SyncProcessor + DecisionApplier
    /Timesheet.Agent.Domain      # State machine de jornada, regras RF-003/004/005/006
    /Timesheet.Agent.Infra.Http  # BackendClient + Polly + DpapiTokenStore
    /Timesheet.Agent.Infra.Db    # EF Core SQLite — 3 repositórios
    /Timesheet.Agent.Ipc         # Named pipes — DialogCorrelator, IpcServer, IpcClient
    /Timesheet.Agent.Ui          # WPF wizard + tray + diálogos modais
    /Timesheet.Agent.Tests       # xUnit + FluentAssertions + Moq
  Timesheet.Agent.sln
/apps/installer              # WiX Toolset
  Product.wxs
  Components.wxs
/packages/contracts          # OpenAPI YAML gerado pelo backend
/Makefile                    # setup, dev, test, build, release, smoke
/docker-compose.dev.yml      # apenas Mailhog para dev
/README.md
```

## Convenções de Código

| Item                    | Padrão                                                                             |
| ----------------------- | ---------------------------------------------------------------------------------- |
| Arquivos backend        | snake_case.py (ex: jwt_service.py, jornada_router.py)                             |
| Arquivos frontend       | PascalCase.tsx para componentes; camelCase.ts para hooks e utilitários             |
| Arquivos agente         | PascalCase.cs (ex: SyncProcessor.cs, BackendClient.cs)                            |
| Variáveis de ambiente   | TIMESHEET_* (ex: TIMESHEET_PORT, TIMESHEET_DEV, TIMESHEET_DB_CIPHER_KEY)          |

## Padrões de Response

**API REST:**

```json
// Sucesso — payload direto (sem envelope wrapper)
{"id": "uuid", "status": "FECHADA", ...}

// Erro — padrão FastAPI HTTPException
{"detail": "mensagem legível para o usuário"}

// Ready check
{"status": "ready"}
```

**HTTP status codes usados:** 200 OK · 201 Created · 400 Bad Request · 401 Unauthorized · 403 Forbidden · 404 Not Found · 409 Conflict · 422 Unprocessable Entity · 429 Too Many Requests · 500 Internal Server Error

## Padrões de Erro

**Backend — propagação:** exceção raw no Repository → exceção de domínio tipada no Service → HTTPException no Router (nunca propagar stack trace para o cliente)

**Logging:** logar stack trace apenas na borda (router/middleware) em 5xx; nunca logar dados sensíveis (senha, token, KEK, CNPJ)

## Autenticação

**JWT:** `Authorization: Bearer <access_token>` — extraído no middleware, injetado no contexto da request

**Refresh:** interceptor Axios no frontend renova automaticamente ao receber 401; rotation obrigatória (novo refresh token a cada uso, revoga o anterior)

**Troca de senha:** revoga todos os refresh tokens ativos do Terceiro + re-cifra smtp_config.password_enc na mesma transação

**Agente:** DpapiTokenStore — access e refresh tokens cifrados via DPAPI (conta LocalSystem) em SQLite local

## Observabilidade

**Backend — formato:** JSON estruturado via structlog com campos `level`, `event`, `timestamp`; sink de arquivo rotativo

**Agente — formato:** JSON estruturado via Serilog com rotação; `Log.CloseAndFlush()` garantido no shutdown

**Níveis:** `error` = falha que afeta o usuário · `warn` = degradação sem falha · `info` = eventos de negócio relevantes · `debug` = desabilitado em produção

**O que NÃO logar:** senhas, tokens JWT, chave KEK, CNPJ — qualquer dado sensível ou PII

## Convenções de Teste

| Item              | Padrão                                                                                                              |
| ----------------- | ------------------------------------------------------------------------------------------------------------------- |
| Backend           | `tests/` separado de `app/`; fixtures pytest para DB async e httpx.AsyncClient                                     |
| Frontend          | `.spec.ts` ao lado do componente ou em `__tests__/`; `vi.mock()` para módulos externos                             |
| Agente            | `Timesheet.Agent.Tests/` projeto separado; interfaces mockadas com Moq; FluentAssertions para asserções            |
| E2E               | `apps/web/e2e/` ou `apps/web/tests/`; Playwright com `webServer` aponta para backend real + seed idempotente       |
| Cobertura backend | ≥ 80% (branch/line via pytest-cov)                                                                                  |
| Cobertura frontend| ≥ 80% (via Vitest + c8)                                                                                             |
