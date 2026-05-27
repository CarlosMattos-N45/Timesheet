---
created_at: "2026-05-27 12:00:55"
id: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
n45_version: 0.2.0
status: proposed
title: TimeSheet Terceiros — Sistema Full-Local de Marcação de Jornada
type: feat
updated_at: "2026-05-27 12:11:17"
---
## 1. Visão Geral

**Goal (To Be):** Entregar um sistema híbrido full-local (Agente Desktop Windows + Web SPA + Backend Python) que registra automaticamente as 4 marcações diárias da jornada de um Terceiro, permite ajustes manuais auditáveis e gera/envia relatório mensal em PDF por SMTP à Empresa Contratante, sem dependências externas além do servidor SMTP do usuário.

**Forma do trabalho:** `build`

**Background (As Is):** Hoje o Terceiro registra a jornada manualmente em planilhas/ferramentas externas, sem automação, sem evidência das marcações reais e sem padronização do relatório mensal. As dores principais são: (1) marcações esquecidas ou imprecisas; (2) trabalho repetitivo de consolidar horas no fim do mês; (3) ausência de rastreabilidade de ajustes; (4) risco de divergência entre o que o Terceiro lembra e o que entrega à Contratante.

### Requisitos Funcionais

- **RF-001** — O sistema deve exibir uma saudação contextual (Bom dia / Boa tarde / Boa noite) ao login do Terceiro na Web e, via Agente Desktop, ao login do Windows, com toast nativo auto-fechado em 10s.
- **RF-002** — O Agente Desktop deve coletar o cadastro inicial (nome, empresa, CNPJ com validação de dígitos, 4 horários cronológicos, flag fim de semana, e-mail/senha, e-mail destinatário do relatório) e bloquear operação até o cadastro completo.
- **RF-003** — O Agente deve registrar `INICIO_JORNADA` no evento de login do Windows, aplicando regras de tolerância (±30 min), alerta para atraso e diálogo de confirmação para antecipação.
- **RF-004** — O Agente deve detectar `SAIDA_ALMOCO` por inatividade contínua ≥ 10 min dentro da janela `[saida_almoco ± 30min]`, sem confirmação imediata.
- **RF-005** — O Agente deve detectar `RETORNO_ALMOCO` pelo primeiro input pós-almoço, com diálogo de confirmação fora da janela e marcação `PENDENTE` em caso de negativa.
- **RF-006** — O Agente deve gerenciar `FIM_JORNADA` via diálogo modal no horário cadastrado (timeout de 60s com ação padrão "NÃO / Lembrar em 30 min"), re-prompt a cada 30 min, auto-encerramento por inatividade ≥ 60 min e captura obrigatória da atividade do dia (≥ 10 chars).
- **RF-007.1** — A Web deve listar as jornadas do mês com 4 horários, total diário, total mensal e badge de status (`EM_ANDAMENTO`, `FECHADA`, `AJUSTADA_MANUALMENTE`, `PENDENTE`) e flag `tem_marcacao_pendente` por linha.
- **RF-007.2** — A Web deve permitir edição individual de horários de uma jornada `FECHADA` com justificativa obrigatória, alterando o status para `AJUSTADA_MANUALMENTE` e gerando registro de auditoria.
- **RF-007.3** — A Web deve permitir a criação manual de uma jornada para um dia sem eventos (data + 4 horários + atividade + justificativa).
- **RF-007.4** — A Web deve permitir visualizar e editar inline a atividade do dia em qualquer jornada.
- **RF-007.5** — A Web deve permitir editar o cadastro do Terceiro e alterar a senha (endpoint dedicado, requer senha atual); ao trocar a senha, todos os refresh tokens ativos do Terceiro são revogados e `smtp_config.password_enc` é re-criptografado na mesma transação.
- **RF-008** — O Backend deve gerar PDF mensal automaticamente (dia 1 de cada mês 00:00 `America/Sao_Paulo` para o mês anterior) e on-demand via Web, armazenar com retenção de 24 meses e enviar por SMTP ao e-mail destinatário, registrando histórico do envio.
- **RF-009** — A Web deve oferecer autenticação por e-mail + senha (JWT access 15 min + refresh 30 dias) com refresh automático no client.
- **RF-010** — O sistema deve registrar `LogAuditoria` genérica (entidade, entidade_id, autor, antes_json, depois_json, motivo, timestamp, expira_em) em todo ajuste manual e exibir o histórico na Web.
- **RF-011** — O Agente deve sincronizar marcações com o Backend a cada 30s quando `/api/v1/health` estiver up, usando `idempotency_key` para evitar duplicatas e aplicando a regra de conflito `AJUSTE_WEB sempre vence; senão last-write-wins por horario_efetivo; empate → Agente vence`.
- **RF-012** — O sistema deve exibir um aviso de privacidade modal one-time no primeiro acesso à Web, persistindo aceite em flag local.
- **RF-013** — O Backend deve expor `/api/v1/ready` (readiness) que verifica conexão SQLite + SELECT 1 + APScheduler rodando, sem autenticação, retornando apenas `{"status":"ready"}`.

## 2. Stack Tecnológica

| Camada | Componente | Tecnologia | Observação |
| ------ | ---------- | ---------- | ---------- |
| Distribuição | Instalador | WiX Toolset (MSI assinado) | Cria 2 Windows Services (`TimesheetAgent`, `TimesheetBackend`), bind backend `127.0.0.1:8765` configurável |
| Backend | Runtime | Python 3.12 embarcado via PyInstaller `--onefile` | Bundle inclui libpango/libcairo (WeasyPrint) e DLLs SQLCipher |
| Backend | HTTP framework | FastAPI + Uvicorn single-worker | OpenAPI desabilitado em produção (`docs_url=None, redoc_url=None, openapi_url=None`); habilitado em desenvolvimento via flag `TIMESHEET_DEV=true` |
| Backend | ORM / Migrations | SQLAlchemy 2.x + Alembic | Async com `asyncpg`-style driver SQLite (`aiosqlite`) |
| Backend | Banco | SQLite + SQLCipher | Criptografia em repouso; chave via KEK (ver §7) |
| Backend | Scheduler | APScheduler in-process | Persistência em SQLite separado (jobstore); `misfire_grace_time=3600, coalesce=True` |
| Backend | Logger | structlog | JSON estruturado, sink de arquivo rotativo; redact de campos sensíveis obrigatório |
| Backend | PDF | WeasyPrint + Jinja2 | Templates HTML→PDF; chamada envolvida em `asyncio.wait_for(timeout=120)` |
| Backend | E-mail | `smtplib` + Jinja2 | SMTP genérico configurável; `timeout=30`; retry 3× backoff linear 5s |
| Backend | Auth | `python-jose` (JWT) + `passlib[argon2]` | Refresh tokens persistidos em SQLite; rotation obrigatória com revogação em cadeia |
| Backend | Rate Limiting | `slowapi` + `limits` | ≤5 tentativas/min por IP+email em `/auth/login`; ≤10/min em `/auth/refresh` |
| Frontend | Runtime | React 18 + TypeScript | |
| Frontend | Build | Vite | |
| Frontend | UI | Material UI (MUI) v5 | WCAG 2.1 AA out-of-the-box |
| Frontend | Roteamento | React Router v6 | |
| Frontend | Data fetching | TanStack Query v5 | |
| Frontend | Forms | React Hook Form + Zod | |
| Frontend | HTTP | Axios + interceptor de refresh JWT | |
| Frontend | i18n | pt-BR fixo na v1.0 | Estrutura permite extensão futura |
| Agente | Runtime | .NET 8 (LTS) | Windows 10 1809+ / Windows 11 |
| Agente | UI | WPF (+ `NotifyIcon` WinForms para tray) | Service `TimesheetAgent` + processo WPF, IPC named pipes |
| Agente | ORM | EF Core + Microsoft.Data.Sqlite | Banco em `%APPDATA%\TimesheetTerceiros\agent-queue.sqlite` |
| Agente | Inatividade | Win32 `GetLastInputInfo` via P/Invoke | Polling 30s |
| Agente | HTTP client | `HttpClient` + Polly | Circuit breaker (fail_max=5/30s, reset=60s) + retry exponencial (1→2→4→8→16s, max 5); timeout 10s por request |
| Agente | Logger | Serilog JSON rotativo | Redact de campos sensíveis obrigatório; `Log.CloseAndFlush()` no shutdown |
| Testes | Backend | pytest + pytest-asyncio + httpx | |
| Testes | Frontend | Vitest + RTL + Playwright | E2E em browser |
| Testes | Agente | xUnit + FluentAssertions + Moq | |
| CI/CD | Plataforma | GitHub Actions | Lint+testes no PR; build do MSI assinado em tag `vX.Y.Z` |

**Padrões de código:**

- **Arquitetura:** monorepo com aplicações por pasta. Backend em slices verticais por domínio. Frontend em slices verticais por feature/página. Agente em camadas (Service host, Domain, Infra HTTP, Infra SQLite, IPC).
- **Nomenclatura:** identificadores em inglês (`Journey`, `Punch`, `Audit`); textos visíveis em pt-BR; endpoints REST em pt-BR mantidos conforme contrato existente (`/api/v1/marcacoes`, `/api/v1/jornadas`, etc.) para alinhar com terminologia do domínio.
- **Estrutura de pastas:**
  ```
  /apps/api          # Backend Python
    /app
      /core          # config, logging, db, security, exceptions
      /modules
        /auth        # service, schema, router, model
        /terceiros
        /jornadas
        /marcacoes
        /atividades
        /justificativas
        /auditoria
        /relatorios
        /historico_envio
      /scheduler     # APScheduler jobs
      /smtp
      /pdf           # templates Jinja2
      /static        # build do React copiado no install
      main.py        # cria FastAPI app, registra routers
    /alembic         # migrations
    /tests
    pyproject.toml
  /apps/web          # Frontend React
    /src
      /pages         # Login, Dashboard, JornadasMes, JornadaDetalhe, JornadaManual, Cadastro, Senha, Relatorios, SMTPConfig, Privacidade
      /components    # MUI compostos reutilizáveis
      /hooks         # useAuth, useJornadas, useRelatorios
      /api           # axios client + queries
      /lib           # zod schemas, formatters
      /types
      App.tsx
      main.tsx
    vite.config.ts
    package.json
  /apps/agent        # Agente .NET
    /src
      /Timesheet.Agent.Service     # Windows Service host
      /Timesheet.Agent.Domain      # State machine de jornada, regras
      /Timesheet.Agent.Infra.Http  # HttpClient + Polly
      /Timesheet.Agent.Infra.Db    # EF Core SQLite
      /Timesheet.Agent.Ipc         # Named pipes (Service ↔ WPF)
      /Timesheet.Agent.Ui          # WPF + tray
      /Timesheet.Agent.Tests
    Timesheet.Agent.sln
  /apps/installer    # WiX
    Product.wxs
    Components.wxs
  /packages/contracts  # OpenAPI yaml gerado pelo Backend, consumido pelo Web via `openapi-typescript`
  /Makefile           # setup, dev, test, build, release
  /docker-compose.dev.yml  # apenas SMTP fake (mailhog) para dev
  /README.md
  ```

## 3. Modelagem de Dados

### Backend (SQLite + SQLCipher, via Alembic)

```sql
-- migration 0001_initial.sql

CREATE TABLE terceiro (
  id                            TEXT PRIMARY KEY,             -- UUID v4
  nome                          TEXT NOT NULL CHECK (length(nome) BETWEEN 1 AND 120),
  empresa_nome                  TEXT NOT NULL CHECK (length(empresa_nome) BETWEEN 1 AND 150),
  empresa_cnpj                  TEXT NOT NULL CHECK (length(empresa_cnpj) = 14),
  horario_inicio_jornada        TEXT NOT NULL,                -- 'HH:MM:SS'
  horario_saida_almoco          TEXT NOT NULL,
  horario_retorno_almoco        TEXT NOT NULL,
  horario_fim_jornada           TEXT NOT NULL,
  trabalha_fim_de_semana        INTEGER NOT NULL DEFAULT 0,   -- bool
  email_contato                 TEXT NOT NULL UNIQUE CHECK (length(email_contato) <= 254),
  email_destinatario_relatorio  TEXT NULL,
  senha_hash                    TEXT NOT NULL,                -- argon2id
  criado_em                     TEXT NOT NULL,                -- ISO 8601 UTC
  atualizado_em                 TEXT NOT NULL,
  CHECK (horario_inicio_jornada < horario_saida_almoco
         AND horario_saida_almoco < horario_retorno_almoco
         AND horario_retorno_almoco < horario_fim_jornada)
);

CREATE TABLE jornada (
  id                       TEXT PRIMARY KEY,
  terceiro_id              TEXT NOT NULL REFERENCES terceiro(id) ON DELETE CASCADE,
  data                     TEXT NOT NULL,                     -- 'YYYY-MM-DD'
  status                   TEXT NOT NULL CHECK (status IN ('EM_ANDAMENTO','FECHADA','AJUSTADA_MANUALMENTE','PENDENTE')),
  total_horas_apuradas_s   INTEGER NULL,                      -- segundos
  criada_em                TEXT NOT NULL,
  fechada_em               TEXT NULL,
  UNIQUE (terceiro_id, data)
);
-- Índice composto substitui idx_jornada_data; cobre filtro por terceiro+período
CREATE INDEX idx_jornada_terceiro_data ON jornada(terceiro_id, data);

CREATE TABLE marcacao (
  id                       TEXT PRIMARY KEY,
  jornada_id               TEXT NOT NULL REFERENCES jornada(id) ON DELETE CASCADE,
  tipo                     TEXT NOT NULL CHECK (tipo IN ('INICIO_JORNADA','SAIDA_ALMOCO','RETORNO_ALMOCO','FIM_JORNADA')),
  horario_registrado       TEXT NOT NULL,                     -- ISO 8601 UTC
  horario_efetivo          TEXT NULL,                         -- ISO 8601 UTC (após ajuste/confirmação)
  origem                   TEXT NOT NULL CHECK (origem IN ('AGENTE_AUTOMATICO','AGENTE_CONFIRMADO','AJUSTE_WEB')),
  status                   TEXT NOT NULL DEFAULT 'CONFIRMADA' CHECK (status IN ('CONFIRMADA','PENDENTE','AJUSTADA')),
  confirmado_pelo_usuario  INTEGER NOT NULL DEFAULT 0,
  idempotency_key          TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) = 36),
  criada_em                TEXT NOT NULL,
  UNIQUE (jornada_id, tipo)
);
-- Índice para JOIN em carregamento de detalhe e CASCADE verify
CREATE INDEX idx_marcacao_jornada ON marcacao(jornada_id);

CREATE TABLE atividade (
  id              TEXT PRIMARY KEY,
  jornada_id      TEXT NOT NULL UNIQUE REFERENCES jornada(id) ON DELETE CASCADE,
  descricao       TEXT NOT NULL CHECK (length(descricao) >= 10),
  registrada_em   TEXT NOT NULL,
  atualizado_em   TEXT NULL        -- ISO 8601 UTC; NULL = nunca editado após criação
);

CREATE TABLE justificativa (
  id                    TEXT PRIMARY KEY,
  jornada_id            TEXT NOT NULL REFERENCES jornada(id) ON DELETE CASCADE,
  motivo                TEXT NOT NULL CHECK (length(motivo) >= 5),
  usuario_responsavel   TEXT NOT NULL,
  criada_em             TEXT NOT NULL
);
-- Índice para busca de justificativas ao carregar detalhe da jornada
CREATE INDEX idx_justificativa_jornada ON justificativa(jornada_id);

CREATE TABLE log_auditoria (
  id            TEXT PRIMARY KEY,
  entidade      TEXT NOT NULL CHECK (entidade IN ('Jornada','Marcacao','Terceiro','Atividade')),
  entidade_id   TEXT NOT NULL,
  autor         TEXT NOT NULL,
  antes_json    TEXT NULL,
  depois_json   TEXT NOT NULL,
  motivo        TEXT NULL,
  criado_em     TEXT NOT NULL,
  expira_em     TEXT NULL        -- ISO 8601 UTC; NULL = retenção indefinida (v1.0); job futuro purga
);
CREATE INDEX idx_audit_entidade ON log_auditoria(entidade, entidade_id);
CREATE INDEX idx_audit_criado_em ON log_auditoria(criado_em);

CREATE TABLE historico_envio_relatorio (
  id                   TEXT PRIMARY KEY,
  mes_referencia       TEXT NOT NULL CHECK (length(mes_referencia) = 7),  -- 'YYYY-MM'
  email_destinatario   TEXT NOT NULL,
  status               TEXT NOT NULL CHECK (status IN ('SUCESSO','FALHA')),
  erro_mensagem        TEXT NULL,
  enviado_em           TEXT NOT NULL
);
CREATE INDEX idx_hist_envio_mes ON historico_envio_relatorio(mes_referencia);

CREATE TABLE refresh_token (
  id            TEXT PRIMARY KEY,
  terceiro_id   TEXT NOT NULL REFERENCES terceiro(id) ON DELETE CASCADE,
  token_hash    TEXT NOT NULL,
  expira_em     TEXT NOT NULL,
  revogado_em   TEXT NULL,
  criado_em     TEXT NOT NULL
);
CREATE INDEX idx_refresh_token_hash ON refresh_token(token_hash);
CREATE INDEX idx_refresh_token_exp ON refresh_token(expira_em);

CREATE TABLE relatorio_gerado (
  id                TEXT PRIMARY KEY,
  mes_referencia    TEXT NOT NULL UNIQUE CHECK (length(mes_referencia) = 7),
  caminho_arquivo   TEXT NOT NULL,
  gerado_em         TEXT NOT NULL,
  invalidado_em     TEXT NULL
);

CREATE TABLE smtp_config (
  id                INTEGER PRIMARY KEY CHECK (id = 1),       -- singleton
  host              TEXT NOT NULL,
  port              INTEGER NOT NULL,
  username_enc      TEXT NOT NULL,                            -- AES-GCM (nonce||ciphertext||tag) com KEK contexto "smtp"
  password_enc      TEXT NOT NULL,                            -- AES-GCM (nonce||ciphertext||tag) com KEK contexto "smtp"
  use_starttls      INTEGER NOT NULL DEFAULT 1,
  from_address      TEXT NOT NULL,
  atualizado_em     TEXT NOT NULL
);

CREATE TABLE privacy_acceptance (
  id              INTEGER PRIMARY KEY CHECK (id = 1),
  aceito_em       TEXT NOT NULL,
  versao_aviso    TEXT NOT NULL    -- ex: "1.0"; atualizado a cada revisão do texto para re-exibição futura
);
```

**Nota sobre `smtp_config`:** `username_enc` substituiu `username` (texto claro) para proteger a identidade do serviço SMTP. Ambos os campos (`username_enc`, `password_enc`) usam AES-GCM com nonce de 12 bytes armazenado como `nonce || ciphertext || tag`. A chave AES-GCM é derivada via `HKDF-Expand` com contexto `info="smtp"` separado do contexto `info="db"` da chave SQLCipher. Como ambas as chaves derivam da KEK (não da senha do Terceiro), não há re-cifragem na troca de senha — a KEK é imutável. Porém, o fluxo de troca de senha deve revogar todos os refresh tokens ativos (ver RF-007.5 e §7).

### Agente (.NET, EF Core SQLite — `agent-queue.sqlite`)

```sql
CREATE TABLE marcacao_local (
  id                     TEXT PRIMARY KEY,             -- UUID v4 (= idempotency_key no backend)
  tipo                   TEXT NOT NULL,                -- INICIO_JORNADA | SAIDA_ALMOCO | RETORNO_ALMOCO | FIM_JORNADA
  horario_registrado     TEXT NOT NULL,                -- ISO 8601 UTC
  horario_efetivo        TEXT NULL,
  origem                 TEXT NOT NULL,                -- AGENTE_AUTOMATICO | AGENTE_CONFIRMADO
  confirmado_pelo_usuario INTEGER NOT NULL DEFAULT 0,
  data_jornada           TEXT NOT NULL,                -- 'YYYY-MM-DD'
  sincronizada           INTEGER NOT NULL DEFAULT 0,
  tentativas_sync        INTEGER NOT NULL DEFAULT 0,
  ultimo_erro_sync       TEXT NULL,
  proxima_tentativa_em   TEXT NULL,                    -- reflete backoff calculado para evitar polling com circuit aberto
  criado_em              TEXT NOT NULL
);
CREATE INDEX idx_marc_local_sync ON marcacao_local(sincronizada, proxima_tentativa_em);

CREATE TABLE estado_jornada_atual (
  id              INTEGER PRIMARY KEY CHECK (id = 1),
  data_jornada    TEXT NOT NULL,
  status          TEXT NOT NULL,  -- AGUARDANDO_INICIO | EM_JORNADA | EM_ALMOCO | AGUARDANDO_FIM | FECHADA
  ultimo_input    TEXT NULL,      -- ISO 8601 UTC
  atualizado_em   TEXT NOT NULL
);

CREATE TABLE configuracao_local (
  id                          INTEGER PRIMARY KEY CHECK (id = 1),
  backend_base_url            TEXT NOT NULL,                  -- ex: http://127.0.0.1:8765
  ultima_sincronizacao_em     TEXT NULL,
  jwt_access_token            TEXT NULL,                      -- DPAPI protected (ProtectedData.Protect)
  jwt_refresh_token           TEXT NULL,                      -- DPAPI protected
  expira_em                   TEXT NULL
);
```

**Nota:** `jwt_access_token` protegido via DPAPI (`ProtectedData.Protect`) — estendido em relação à Spec inicial que cobria apenas o refresh token.

## 4. Contratos e Arquitetura

### Endpoints REST (FastAPI — `/apps/api/app/modules/*/router.py`)

```python
# Auth
@router.post("/api/v1/auth/login", status_code=200, response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse: ...
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    terceiro_id: UUID
    expires_in: int  # seconds (=900)

@router.post("/api/v1/auth/refresh", status_code=200, response_model=RefreshResponse)
async def refresh(body: RefreshRequest) -> RefreshResponse: ...

@router.post("/api/v1/auth/logout", status_code=204)
async def logout(current: TerceiroAuth = Depends(auth_dep)) -> None: ...

# Terceiro
@router.post("/api/v1/terceiros", status_code=201, response_model=CreateTerceiroResponse)
async def create_terceiro(body: CreateTerceiroRequest) -> CreateTerceiroResponse: ...
# Endpoint desabilitado após criação do primeiro Terceiro (flag singleton no banco ou env var TIMESHEET_SETUP_DONE)
class CreateTerceiroRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    empresa_nome: str = Field(min_length=1, max_length=150)
    empresa_cnpj: str = Field(pattern=r"^\d{14}$")  # validação de dígitos verificadores obrigatória server-side
    horario_inicio_jornada: time
    horario_saida_almoco: time
    horario_retorno_almoco: time
    horario_fim_jornada: time
    trabalha_fim_de_semana: bool = False
    email_contato: EmailStr
    email_destinatario_relatorio: EmailStr | None = None
    senha: str = Field(min_length=8, max_length=128)
    senha_confirmacao: str

@router.get("/api/v1/terceiros/me", response_model=TerceiroResponse)
@router.put("/api/v1/terceiros/me", response_model=TerceiroResponse)
@router.put("/api/v1/terceiros/me/senha", status_code=204)
class ChangePasswordRequest(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=8, max_length=128)
# Ao processar: revogar todos refresh_token ativos do Terceiro na mesma transação.
# KEK é imutável (protegida por DPAPI/instalação) — smtp_config.password_enc não precisa re-cifragem.

# Marcações
@router.post("/api/v1/marcacoes", status_code=201, response_model=MarcacaoResponse)
async def post_marcacao(body: PostMarcacaoRequest, current=Depends(auth_dep)) -> MarcacaoResponse: ...
class PostMarcacaoRequest(BaseModel):
    tipo: Literal["INICIO_JORNADA","SAIDA_ALMOCO","RETORNO_ALMOCO","FIM_JORNADA"]
    horario_registrado: datetime  # UTC ISO 8601
    horario_efetivo: datetime | None = None
    origem: Literal["AGENTE_AUTOMATICO","AGENTE_CONFIRMADO"]  # AJUSTE_WEB nunca vem do Agente
    idempotency_key: UUID

@router.get("/api/v1/marcacoes", response_model=list[MarcacaoResponse])
async def list_marcacoes(status: str | None = None, current=Depends(auth_dep)): ...

@router.put("/api/v1/marcacoes/{marcacao_id}", response_model=MarcacaoResponse)
class AjusteMarcacaoRequest(BaseModel):
    horario_efetivo: datetime
    motivo: str = Field(min_length=5)

# Jornadas
@router.get("/api/v1/jornadas", response_model=JornadasMesResponse)
async def list_jornadas(mes: str = Query(pattern=r"^\d{4}-\d{2}$")): ...
class JornadaResumo(BaseModel):
    id: UUID
    data: date
    status: str
    total_horas_apuradas_s: int | None
    tem_marcacao_pendente: bool  # True se qualquer marcacao.status == 'PENDENTE'
    # + 4 campos de horário para exibição na tabela
class JornadasMesResponse(BaseModel):
    mes_referencia: str
    total_horas_mes_s: int
    jornadas: list[JornadaResumo]

@router.get("/api/v1/jornadas/{jornada_id}", response_model=JornadaDetalheResponse)
@router.put("/api/v1/jornadas/{jornada_id}", response_model=JornadaDetalheResponse)
class AjusteJornadaRequest(BaseModel):
    marcacoes: list[AjusteMarcacaoItem]
    motivo: str = Field(min_length=5)

@router.post("/api/v1/jornadas/manual", status_code=201, response_model=JornadaDetalheResponse)
class JornadaManualRequest(BaseModel):
    data: date
    marcacoes: list[MarcacaoManualItem]   # 4 itens com tipo+horario_efetivo
    atividade: str = Field(min_length=10)
    motivo: str = Field(min_length=5)

@router.post("/api/v1/jornadas/{jornada_id}/atividade", status_code=201)
class AtividadeRequest(BaseModel):
    descricao: str = Field(min_length=10)

# Auditoria
@router.get("/api/v1/auditoria", response_model=list[AuditoriaItem])
async def list_auditoria(entidade: str, entidade_id: UUID, current=Depends(auth_dep)): ...
# auth_dep obrigatório — endpoint protegido por JWT

# Relatórios
class RelatorioMesResponse(BaseModel):
    mes_referencia: str
    caminho_arquivo: str
    gerado_em: str
    invalidado_em: str | None  # não-nulo = PDF desatualizado; frontend exibe badge âmbar

@router.get("/api/v1/relatorios/{mes}", response_class=FileResponse)
async def get_relatorio(mes: str = Path(pattern=r"^\d{4}-\d{2}$")): ...

@router.get("/api/v1/relatorios/{mes}/meta", response_model=RelatorioMesResponse)
async def get_relatorio_meta(mes: str = Path(pattern=r"^\d{4}-\d{2}$")): ...

@router.post("/api/v1/relatorios/{mes}/enviar", status_code=202)
class EnviarRelatorioRequest(BaseModel):
    email: EmailStr | None = None  # default: email_destinatario_relatorio
# Retorna 422 com code="SMTP_NOT_CONFIGURED" se smtp_config ausente (permite distinção no frontend)

@router.get("/api/v1/relatorios/{mes}/historico", response_model=list[HistoricoEnvioItem])

# SMTP config
@router.get("/api/v1/smtp", response_model=SmtpConfigResponse)
@router.put("/api/v1/smtp", response_model=SmtpConfigResponse)
class SmtpConfigRequest(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    username: str          # recebido em texto claro; persistido criptografado como username_enc
    password: SecretStr    # persistido criptografado como password_enc
    use_starttls: bool = True
    from_address: EmailStr

# Privacidade
@router.get("/api/v1/privacidade", response_model=PrivacyStatus)
@router.post("/api/v1/privacidade/aceitar", status_code=204)

# Sistema
@router.get("/api/v1/health")
async def health() -> dict: return {"status": "ok", "version": __version__}
# Sem autenticação; sem acesso ao banco; latência < 50ms

@router.get("/api/v1/ready")
async def ready() -> dict:
    # Verifica: SELECT 1 no banco de domínio + APScheduler.state == STATE_RUNNING
    # Retorna apenas {"status": "ready"} — sem detalhes internos
    return {"status": "ready"}
# Sem autenticação; usado pelo instalador MSI e pelo tray icon

@router.get("/api/v1/config")
async def config_pub() -> dict:
    return {"port": settings.port, "version": __version__, "timezone": "America/Sao_Paulo"}
```

**Formato de erro padronizado** (todos os 4xx/5xx):

```json
{
  "code": "VALIDATION_ERROR" | "UNAUTHORIZED" | "FORBIDDEN" | "NOT_FOUND" | "CONFLICT" | "INTERNAL_ERROR" | "SMTP_NOT_CONFIGURED",
  "message": "texto em pt-BR",
  "details": [{"field": "empresa_cnpj", "issue": "CNPJ inválido"}]
}
```

**Segurança de endpoint `POST /api/v1/terceiros`:** após criação do primeiro (e único) Terceiro, o endpoint retorna `403 FORBIDDEN` com `code="SETUP_ALREADY_DONE"` para evitar criação de múltiplos Terceiros (sistema single-tenant).

**Middleware de segurança HTTP (FastAPI):**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'` (adequado para SPA local)
- Validação do header `Host`: aceitar apenas `127.0.0.1` e `localhost` (proteção DNS rebinding)

### Contrato Agente ↔ Backend (HTTP/JSON local)

- O Agente envia `POST /api/v1/marcacoes` com `idempotency_key` (UUID v4 = id local). Resposta `201` ou `409` (já existente) — ambas são consideradas sucesso pelo Agente (idempotência).
- O Backend cria a `jornada` do dia (se inexistente) ao receber a primeira marcação daquele `data_jornada`.
- O Agente faz `GET /api/v1/health` a cada 30s. Se up → drena fila pendente em ordem cronológica.
- O Agente usa `GET /api/v1/ready` no pré-sync de inicialização para garantir que o banco está acessível antes de drenar a fila.
- Conflito (`409` com `code = CONFLICT`): retorna o estado servidor; Agente aplica regra **RN-012** (AJUSTE_WEB vence; senão last-write-wins; empate exato → Agente vence) e re-PUT se necessário.
- Polly configurado: circuit breaker `fail_max=5` tentativas em 30s, `reset_timeout=60s`; retry exponencial 1→2→4→8→16s (max 5 tentativas); timeout 10s por request; `proxima_tentativa_em` em `marcacao_local` reflete o backoff calculado.

### Contrato IPC Service ↔ WPF (named pipes)

Pipe único `\\.\pipe\TimesheetAgent`. Frames JSON delimitados por newline. ACL do pipe restrita ao SID do `TimesheetAgent` Service + verificação de identidade via `GetNamedPipeClientProcessId` para impedir injeção de processos maliciosos:

```json
{"type": "DIALOG_REQUEST", "id": "uuid", "kind": "CONFIRM_INICIO_ANTECIPADO" | "CONFIRM_RETORNO_FORA_JANELA" | "PROMPT_FIM_JORNADA" | "PROMPT_ATIVIDADE", "payload": {...}}
{"type": "DIALOG_RESPONSE", "id": "uuid", "answer": "SIM" | "NAO" | "TIMEOUT", "payload": {...}}
{"type": "TOAST", "title": "...", "body": "...", "duration_s": 10}
{"type": "STATUS_PUSH", "estado": "EM_JORNADA", "marcacao": {...}}
```

Timeout de 60s nos diálogos: `CONFIRM_INICIO_ANTECIPADO` → `TIMEOUT` (equivale a NÃO); `CONFIRM_RETORNO_FORA_JANELA` → `TIMEOUT` (equivale a PENDENTE); `PROMPT_FIM_JORNADA` → `TIMEOUT` (equivale a NÃO / Lembrar em 30 min).

### Fluxo de Dados

1. **Login Windows** → Service detecta evento `SessionLogon` → publica `TOAST` saudação → cria `MarcacaoLocal(INICIO_JORNADA)` → enfileira sync.
2. **Inatividade** → polling 30s do `GetLastInputInfo` → se ≥ 10 min contínuos dentro de `[saida_almoco ± 30min]` → cria `MarcacaoLocal(SAIDA_ALMOCO)`.
3. **Primeiro input pós-almoço** → cria `MarcacaoLocal(RETORNO_ALMOCO)`; fora da janela → `DIALOG_REQUEST CONFIRM_RETORNO_FORA_JANELA`.
4. **Horário de fim** → `DIALOG_REQUEST PROMPT_FIM_JORNADA` (timeout 60s → NÃO) → re-prompt a cada 30 min; inatividade ≥ 60 min após horário cadastrado → registra último input como `FIM_JORNADA` (PENDENTE) sem prompt.
5. **Sync loop** (a cada 30s): verifica `/health` → drena fila local → POST → atualiza `sincronizada`. Erro de rede → backoff exponencial Polly; `proxima_tentativa_em` atualizado.
6. **Web** → `PUT /jornadas/{id}` → cria `LogAuditoria` + `Justificativa` + atualiza marcações → invalida `relatorio_gerado` do mês (`invalidado_em = now()`).
7. **Scheduler APScheduler** → dia 1, 00:00 BRT → gera PDF do mês anterior (`asyncio.wait_for(timeout=120)`) → tenta envio SMTP (3× backoff 5s, `timeout=30`) → registra `HistoricoEnvioRelatorio`.
8. **Graceful Shutdown Backend**: `scheduler.shutdown(wait=True)` → drenar requests Uvicorn (30s) → fechar pool aiosqlite. **Graceful Shutdown Agente**: `StopAsync` com `CancellationToken(10s)` → `Log.CloseAndFlush()` → fechar named pipe graciosamente.

### Máquina de Estados do Agente

```
                +-------------------+
                | AGUARDANDO_INICIO |
                +---------+---------+
                          | login Windows / janela início
                          v
                +-------------------+
                |    EM_JORNADA     |
                +---------+---------+
                          | inatividade >=10min dentro da janela almoço
                          v
                +-------------------+
                |     EM_ALMOCO     |
                +---------+---------+
                          | primeiro input
                          v
                +-------------------+
                |    EM_JORNADA     |  (segundo período da tarde)
                +---------+---------+
                          | horário fim atingido OU inatividade >=60min
                          v
                +-------------------+
                |   AGUARDANDO_FIM  |
                +---------+---------+
                          | usuário confirma SIM e preenche atividade
                          v
                +-------------------+
                |      FECHADA      |
                +-------------------+
```

### Impacto em Arquivos Existentes

| Arquivo / Módulo | Mudança | Observação |
| ---------------- | ------- | ---------- |
| (greenfield) | Todos novos | Não há arquivos pré-existentes; nada a modificar |

## 5. Telas e Navegação

### `/login` — Login

**Conteúdo:** Logo centralizado, saudação contextual (Bom dia/Boa tarde/Boa noite) acima do form, campos e-mail + senha, botão "Entrar", link "Esqueci minha senha" (desabilitado/cinza com tooltip "Recuperação de senha disponível em breve").
**Ações disponíveis:** Entrar; nenhuma outra ação (sem cadastro — o Terceiro é criado via Agente Desktop no onboarding).
**Navegação:** Sucesso → `/privacidade` (one-time) ou `/jornadas` (demais acessos).
**Estados:**
- Loading: spinner no botão "Entrar", campos desabilitados.
- Vazio: form em branco, botão "Entrar" desabilitado até ambos os campos preenchidos.
- Erro: alert MUI inline abaixo do form — "E-mail ou senha inválidos. Verifique e tente novamente." Campo senha limpo; foco retorna ao campo senha.

---

### `/privacidade` — Aviso de Privacidade (one-time)

**Conteúdo:** Cabeçalho "Aviso de Privacidade", bloco de texto scrollável (dados coletados — incluindo `email_destinatario_relatorio` como dado de terceiro e período de retenção do log de auditoria e que credenciais SMTP são armazenadas criptografadas localmente —, finalidade, retenção, base legal, contato DPO), checkbox "Li e aceito os termos de privacidade", botão "Continuar" (desabilitado até check). Sem opção de recusar — LGPD art. 7, VI.
**Ações disponíveis:** Aceitar e continuar.
**Navegação:** Aceite → `/jornadas`.
**Estados:**
- Loading (pós-clique): botão "Continuar" com spinner, checkbox desabilitado.
- Erro: toast MUI snackbar vermelho — "Não foi possível registrar o aceite. Tente novamente."

**Guard de rota:** `/privacidade` redireciona para `/jornadas` se `privacy_acceptance` já existir. Demais rotas autenticadas redirecionam para `/privacidade` se aceite pendente.

---

### `/jornadas` — Lista Mensal (default após login)

**Conteúdo:** Seletor de mês (MUI DatePicker, default = mês atual, máximo = mês atual), tabela MUI DataGrid com colunas: Data | Dia da Semana | Início | Saída Almoço | Retorno Almoço | Fim | Total | Status. Rodapé com total mensal em horas. Barra de ações: botão "Nova jornada manual", botão "Baixar PDF", botão "Enviar por e-mail".
**Ações disponíveis:** Trocar mês; clicar linha → detalhe; criar jornada manual; baixar PDF (desabilitado com tooltip quando vazio); enviar PDF por e-mail (desabilitado com tooltip quando vazio) → modal de confirmação com campo e-mail preenchido com `email_destinatario_relatorio` (editável).
**Navegação:** Clique em linha → `/jornadas/:id`; "Nova jornada manual" → `/jornadas/manual`; "Baixar PDF" → download direto; "Enviar por e-mail" → modal de confirmação.
**Estados:**
- Loading: skeleton MUI (5 linhas) na tabela, total exibindo "—".
- Vazio: ilustração neutra + "Nenhuma jornada registrada para este mês." + CTA "Criar jornada manual".
- Erro: alert MUI inline "Não foi possível carregar as jornadas." + botão "Tentar novamente".
- Badge de status: `EM_ANDAMENTO` = chip cinza, `FECHADA` = chip verde, `AJUSTADA_MANUALMENTE` = chip âmbar, `PENDENTE` = chip vermelho com ícone de alerta. Linhas com `tem_marcacao_pendente=true` exibem badge PENDENTE independentemente do status da jornada.

---

### `/jornadas/:id` — Detalhe da Jornada

**Conteúdo:** Breadcrumb "Jornadas > DD/MM/YYYY", badge de status no cabeçalho, 4 campos de horário (MUI TimePicker, editáveis somente para jornadas `FECHADA` e `AJUSTADA_MANUALMENTE` — `PENDENTE` e `EM_ANDAMENTO` bloqueados), total diário recalculado em tempo real, textarea "Atividade do dia" (editável em qualquer status exceto `EM_ANDAMENTO`), seção colapsada "Histórico de auditoria" (accordion MUI, `aria-expanded`), seção "Justificativas anteriores". Botão "Salvar alterações" visível somente se algo foi editado.
**Ações disponíveis:** Editar horários; editar atividade; salvar (abre modal de justificativa); voltar via breadcrumb.
**Navegação:** Salvar com sucesso → permanece na tela (TanStack Query invalidation); breadcrumb → `/jornadas`.
**Estados:**
- Loading: skeleton nos campos de horário e textarea.
- Erro ao carregar: alert + botão "Tentar novamente".
- Modal de justificativa: input obrigatório ≥ 5 chars com contador, botões "Cancelar" / "Confirmar alterações" (desabilitado até mínimo atingido).
- Sucesso ao salvar: toast "Jornada atualizada com sucesso." Badge atualiza.
- Erro ao salvar: toast vermelho com mensagem do campo `message` do erro.
- Jornada `PENDENTE`: banner âmbar informativo no topo — "Esta jornada possui marcações pendentes. Ajuste os horários sinalizados." — com campos PENDENTE destacados em âmbar.

**Acessibilidade:** TimePickers com `aria-label` descritivo; accordion com `aria-expanded`; badge de status com `role="status"`.

---

### `/jornadas/manual` — Criar Jornada Manual

**Conteúdo:** Cabeçalho "Nova Jornada Manual", MUI DatePicker (dias futuros desabilitados; dias com jornada existente indicados visualmente com dot no calendario), 4 TimePickers de horário com validação cronológica em tempo real, textarea "Atividade" (≥10 chars, contador), textarea "Justificativa" (≥5 chars, contador), botões "Cancelar" / "Salvar".
**Ações disponíveis:** Selecionar data, preencher horários, preencher atividade e justificativa, salvar, cancelar.
**Navegação:** Sucesso → `/jornadas/:id` da jornada criada (via `Location` do `201`); Cancelar → `/jornadas`.
**Estados:**
- Loading: botão "Salvar" com spinner.
- Vazio: form inicial. Botão "Salvar" desabilitado até todos os campos válidos.
- Erro de validação: campos inválidos com helper text inline ("Os horários devem ser em ordem cronológica.").
- Erro 409: alert "Já existe uma jornada para este dia. Abra-a para editar." + link para `/jornadas/:id_existente`.

---

### `/cadastro` — Editar Cadastro

**Conteúdo:** Form com todos os campos do `terceiro` (nome, empresa, CNPJ, 4 horários, flag fim de semana, e-mail contato, e-mail destinatário relatório). Seção separada com botão "Alterar senha" → `/cadastro/senha`. Botão "Salvar".
**Ações disponíveis:** Editar campos, salvar, alterar senha.
**Navegação:** Salvar → permanece com toast de sucesso; "Alterar senha" → `/cadastro/senha`.
**Estados:**
- Loading: skeleton nos campos.
- Erro de validação: CNPJ inválido com helper text "CNPJ inválido (dígito verificador incorreto)."
- Erro 4xx: alert com mensagem.
- Sucesso: toast "Cadastro atualizado com sucesso."

---

### `/cadastro/senha` — Alterar Senha

**Conteúdo:** Campo "Senha atual", campo "Nova senha" (com indicador de força), campo "Confirmar nova senha", botão "Salvar", link "Cancelar".
**Ações disponíveis:** Salvar, cancelar.
**Navegação:** Sucesso → `/cadastro`; Cancelar → `/cadastro`.
**Estados:**
- Erro 401: alert "Senha atual incorreta." Campo "Senha atual" limpo, foco retorna a ele.
- Erro validação: senhas não coincidem — helper text inline antes do submit.
- Sucesso: toast "Senha alterada com sucesso." + redirect para `/cadastro`.

---

### `/relatorios` — Relatórios

**Conteúdo:** Seletor de mês (máximo = mês anterior), iframe com prévia do PDF (ou placeholder "PDF indisponível"), badge âmbar "PDF desatualizado — clique em 'Atualizar relatório' para regenerar" quando `invalidado_em` não-nulo, histórico de envios em tabela (data, destinatário, status, erro), botão "Baixar PDF", botão "Enviar agora", botão "Configurar SMTP".
**Ações disponíveis:** Selecionar mês, baixar PDF, enviar, configurar SMTP.
**Navegação:** "Configurar SMTP" → `/configuracoes/smtp`.
**Estados:**
- Loading: skeleton no iframe.
- Vazio (mês sem dados): "Nenhuma jornada registrada para este mês. Não é possível gerar o relatório."
- PDF invalidado: badge âmbar + botão extra "Atualizar relatório".
- Erro envio SMTP (SMTP não configurado): modal de alerta "Servidor SMTP não configurado." com CTA "Configurar agora" → `/configuracoes/smtp`.
- Erro envio SMTP (falha de envio): alerta vermelho "Último envio falhou: [erro_mensagem]. Verifique as configurações SMTP." + link para `/configuracoes/smtp`.
- Sucesso envio: toast "Relatório enviado para [email]."

---

### `/configuracoes/smtp` — Configuração SMTP

**Conteúdo:** Campos host, porta (default 587), usuário, senha (masked), toggle STARTTLS, from_address, botão "Testar conexão", botão "Salvar".
**Ações disponíveis:** Preencher/editar configuração, testar conexão, salvar.
**Navegação:** Salvar → permanece com toast; Cancelar → `/relatorios`.
**Estados:**
- Loading (teste/salvar): botão com spinner.
- Sucesso teste: toast "Conexão SMTP testada com sucesso."
- Erro teste: alert inline com mensagem do servidor ("Conexão recusada", "Autenticação falhou").
- Sucesso salvar: toast "Configuração SMTP salva."

---

### Tela do Agente Desktop (WPF — não rota web)

**`Cadastro Inicial`** (one-time, modal full-screen do WPF host):
**Conteúdo:** Wizard 3 passos com barra de progresso visual:
- Passo 1: Nome completo, nome da empresa, CNPJ (com máscara e validação de dígitos verificadores em tempo real).
- Passo 2: 4 TimePickers de horários (validação cronológica em tempo real), toggle "Trabalha nos fins de semana".
- Passo 3: E-mail de contato, senha (≥8 chars, indicador de força visual), confirmar senha, e-mail destinatário do relatório (opcional).
**Ações:** Avançar (desabilitado até passo válido), Voltar, Finalizar (passo 3, desabilitado até válido).
**Navegação:** Finalizar → fecha modal wizard → tray icon ativo → abre browser em `http://127.0.0.1:8765`.
**Estados:** Validação inline por campo (não apenas no submit). Erro 409 (e-mail já cadastrado) → alert no passo 3 "Este e-mail já está em uso."

**Diálogos modais do WPF** (todos com timeout de 60s e progress bar visual):
- Confirmação de antecipação > 30 min: "Você iniciou às [T]. Seu horário cadastrado é [H_INI]. Deseja registrar [T]?" Botões "Sim, registrar [T]" / "Não, usar [H_INI]". Timeout → NÃO.
- Confirmação de retorno fora de janela: "Detectamos retorno às [T], fora da janela. Confirmar [T]?" Botões "Confirmar [T]" / "Marcar como pendente". Timeout → PENDENTE.
- Fim de jornada: "São [H_FIM]. Encerrar jornada agora?" Botões "Sim, encerrar" / "Lembrar em 30 min". Timeout → "Lembrar em 30 min". Ao clicar "Sim" → form de atividade como passo 2 do mesmo diálogo.
- Form de atividade: textarea com contador (mínimo 10 chars), botões "Salvar e encerrar" (desabilitado < 10 chars) / "Cancelar" (volta ao diálogo de fim).

**Toast saudação:** Notificação nativa Windows (balloon tip ou toast moderno se Win 10 1903+), auto-fechamento 10s, sem interação necessária.

---

### Fluxos de Usuário

**Onboarding:** Instalar MSI → reboot opcional → login Windows → Cadastro Inicial (WPF wizard 3 passos, validação inline) → Finalizar → tray ativo → browser em `http://127.0.0.1:8765/login` → login com credenciais cadastradas → aceite de privacidade → `/jornadas` (vazio + CTA "Criar jornada manual").
Desvio: CNPJ inválido no passo 1 → campo em vermelho, botão "Avançar" bloqueado → usuário corrige.

**Dia normal:** Login Windows 09:02 (dentro de [08:30, 09:30]) → toast "Bom dia, Maria. Início registrado às 09:02." → trabalho → inatividade 12:05–12:18 (≥10min, dentro de [11:30, 12:30]) → SAIDA_ALMOCO 12:05 (silencioso) → input 13:10 (dentro de [12:30, 13:30]) → RETORNO_ALMOCO 13:10 (silencioso) → trabalho → 18:00 chega → diálogo "Encerrar?" (progress bar 60s) → SIM → form atividade ≥10 chars → encerrada → relatório mostra status FECHADA.

**Antecipação:** Login 06:45, fora de [08:30, 09:30] → diálogo "Registrar 06:45 ou 09:00?" (progress bar 60s) → SIM (06:45) → INICIO_JORNADA = 06:45; timeout ou NÃO → INICIO_JORNADA = 09:00.

**Atraso > tolerância:** Login 09:45, fora de [08:30, 09:30] (atraso) → toast informativo "Início registrado às 09:45 (atraso de 45 min)" + INICIO_JORNADA = 09:45 (sem diálogo, pois é atraso, não antecipação).

**Auto-encerramento:** 18:00 chega → diálogo "Encerrar?" → timeout 60s → "Lembrar em 30 min" → 18:30 re-prompt → 19:00 inatividade contínua ≥ 60 min → FIM_JORNADA = último input (ex 18:02), status jornada = PENDENTE.

**Ajuste manual:** Usuário acessa `/jornadas` → 25/05 mostra badge PENDENTE (chip vermelho) → abre detalhe → banner âmbar "Esta jornada possui marcações pendentes" → edita fim de 18:02 para 18:00 → botão "Salvar alterações" aparece → clique → modal justificativa → digita ≥5 chars → "Confirmar alterações" → toast sucesso → badge vira AJUSTADA_MANUALMENTE → accordion auditoria mostra 1 entrada.
Desvio: justificativa < 5 chars → botão "Confirmar alterações" permanece desabilitado.

**Geração mensal:** Dia 1 do mês, 00:00 BRT → APScheduler dispara job → gera PDF mês anterior → busca `email_destinatario_relatorio` → tenta SMTP (3×) → `HistoricoEnvioRelatorio(SUCESSO)`. Se SMTP não configurado → `FALHA(SMTP_NOT_CONFIGURED)`; usuário no próximo acesso vê alerta para configurar.

**Offline:** Backend crashou → Agente continua registrando localmente → tray icon mostra badge "X marcações pendentes" → Backend volta → próxima passada sync (≤30s) drena fila → badge zera → toast discreta "X marcações sincronizadas."

## 6. Boundaries

**In scope (v1.0):**

- Cadastro inicial completo via Agente Desktop + login Web.
- Registro automático das 4 marcações no Windows com regras de tolerância, inatividade, diálogos (timeout 60s), progress bar e auto-encerramento.
- Sincronização offline-first Agente → Backend com idempotency, resolução de conflitos e circuit breaker Polly.
- Web SPA para listagem mensal, edição de jornadas/marcações/atividade, criação manual e edição de cadastro/senha.
- Auditoria genérica de toda mutação manual com campo `expira_em` (purge em fase 2).
- Relatório PDF mensal automático (cron) + on-demand + envio SMTP configurável + histórico.
- Banco SQLCipher (criptografia em repouso via KEK/DPAPI) e aviso de privacidade.
- Instalador MSI WiX que provisiona 2 Windows Services, banco e arquivos estáticos do Web.
- Logs locais rotativos com redact de campos sensíveis no Backend e no Agente.
- Segurança HTTP: headers `X-Content-Type-Options`, `X-Frame-Options`, `CSP`, validação header `Host`.
- Rate limiting em `/auth/login` e `/auth/refresh`.
- Endpoint `/api/v1/ready` para readiness probe do instalador e tray icon.
- DPAPI protection para tokens JWT no banco local do Agente.
- Segurança do named pipe IPC (ACL + verificação de identidade de processo).

**Out of scope (fases futuras):**

- Integração com RH/ERP, folha de pagamento, biometria, geolocalização, ponto físico.
- Aplicativo mobile.
- Suporte macOS/Linux.
- Multi-Terceiro no mesmo Backend; papel administrador/RH centralizado.
- Auto-update de Agente/Backend.
- Endpoints LGPD formais de exportação/exclusão (apenas aviso de privacidade na v1.0); deleção/anonimização do Terceiro.
- Cadastro de feriados.
- Múltiplas atividades por jornada.
- Suporte a horário de verão.
- Observabilidade externa (Prometheus/Grafana).
- Backup/restore automatizado do SQLite.
- "Esqueci minha senha" / reset por e-mail.
- i18n com framework.
- Job de purge de `log_auditoria` via `expira_em` (infra preparada, job na fase 2).
- Anonimização de PII em `log_auditoria` na deleção do Terceiro.

## 7. Constraints

- **Plataforma do Agente:** Windows 10 build 1809+ ou Windows 11; .NET 8 runtime embarcado.
- **Bind do Backend:** `127.0.0.1` apenas — nunca exposto na rede; porta default `8765` configurável **na instalação**, exposta também via env var `TIMESHEET_PORT`.
- **Distribuição:** MSI assinado por certificado de code signing válido. Sem auto-update na v1.0.
- **Criptografia em repouso (KEK):** SQLite via SQLCipher com chave derivada de uma KEK (Key Encryption Key) gerada na instalação (32 bytes, CSPRNG), protegida via DPAPI antes de persistir em `%APPDATA%\TimesheetTerceiros\key.kek` (separada do banco). A KEK é imutável — não deriva da senha do Terceiro, eliminando re-cifragem na troca de senha. A chave SQLCipher (contexto `info="db"`) e a chave AES-GCM do SMTP (contexto `info="smtp"`) são derivadas via `HKDF-Expand` a partir da KEK com contextos distintos. `smtp_config.username_enc` e `smtp_config.password_enc` usam nonce de 12 bytes armazenado como `nonce || ciphertext || tag`.
- **Internacionalização:** textos visíveis em pt-BR; identificadores de código em inglês.
- **Fuso horário fixo:** `America/Sao_Paulo` para scheduler, exibição e PDF.
- **Dependência externa única:** servidor SMTP do usuário; demais funcionalidades operam offline.
- **WeasyPrint quirk:** requer libpango/libcairo Windows-native no bundle PyInstaller; validados no smoke test do CI; chamada via `asyncio.wait_for(timeout=120)`.
- **SQLite + asyncio quirk:** `aiosqlite` com `PRAGMA journal_mode=WAL`; APScheduler em jobstore SQLite separado do domínio.
- **JWT:** access token 15 min, refresh token 30 dias, refresh rotation obrigatória (cada uso invalida o anterior e revoga toda a cadeia em caso de reuso de token revogado); troca de senha revoga todos os refresh tokens ativos.
- **Idempotency obrigatória:** toda mutação vinda do Agente carrega `idempotency_key` (UUID v4) com índice único.
- **Validação CNPJ:** dígitos verificadores validados via algoritmo módulo 11 server-side (Backend) e client-side (Web + Agente).
- **Senha:** mínimo 8 chars, hashing Argon2id (`time_cost=3, memory_cost=65536, parallelism=4`).
- **Tray do Agente:** `NotifyIcon` é o único uso de WinForms; demais UIs em WPF puro.
- **Setup automatizado:** `make setup` / `scripts/setup.ps1` provisiona Python, deps e SQLite local sem passos manuais.
- **Quality gate de cobertura:** Backend ≥ 80%, Web ≥ 80%, Agente ≥ 70% (camadas Domain e Infra, excluindo UI WPF).
- **OpenAPI UI:** desabilitado em produção (`docs_url=None, redoc_url=None, openapi_url=None`); habilitado apenas em dev via `TIMESHEET_DEV=true`.
- **`POST /api/v1/terceiros`:** retorna `403` após criação do primeiro Terceiro (sistema single-tenant).
- **Logs:** redact obrigatório de `senha`, `senha_hash`, `password_enc`, `username_enc`, `jwt_access_token`, `jwt_refresh_token`, `token_hash`, chave KEK em todos os sinks.
- **Named pipe IPC:** ACL restrita ao SID do Service + `GetNamedPipeClientProcessId` para verificação de identidade.
- **DPAPI:** tokens JWT (access e refresh) no `configuracao_local` do Agente protegidos por `ProtectedData.Protect`.
- **ACLs de arquivo:** pasta de PDFs gerados com permissões restritas ao usuário do Service `TimesheetBackend` (definidas no MSI WiX).
- **Retenção de logs:** Backend: 10 MB/arquivo, max 30 arquivos (~300 MB); Agente: 5 MB/arquivo, max 20 arquivos (~100 MB).

## 8. Acceptance Criteria

### RF-001
- [ ] Ao login na Web, o cabeçalho exibe "Bom dia / Boa tarde / Boa noite" conforme hora local do navegador (faixas 0–12, 12–18, 18–24).
- [ ] Ao login do Windows, o Service emite toast com a saudação e o nome do Terceiro, fechando automaticamente em 10s.
- [ ] Se o nome do Terceiro contiver acentos, eles são preservados na saudação.

### RF-002
- [ ] Antes do cadastro completo, o tray icon mostra badge vermelha e qualquer tentativa de uso abre o wizard.
- [ ] CNPJ é validado pelos dígitos verificadores (módulo 11) server-side e client-side; CNPJ inválido bloqueia avanço com mensagem inline.
- [ ] Os 4 horários devem ser cronológicos; tentativa de salvar fora de ordem bloqueia com mensagem inline.
- [ ] Senha e confirmação devem coincidir; senha < 8 chars bloqueia.
- [ ] `email_contato` é único; tentativa de cadastrar um segundo Terceiro retorna `403 FORBIDDEN` com `code="SETUP_ALREADY_DONE"`.
- [ ] Finalizado o wizard, `POST /api/v1/terceiros` retorna `201` e o Agente abre o browser em `http://127.0.0.1:8765/login`.

### RF-003
- [ ] Login do Windows às `T` dentro de `[h_ini - 30min, h_ini + 30min]` → `INICIO_JORNADA = T`, origem `AGENTE_AUTOMATICO`, sem prompt.
- [ ] Login às `T` em `[h_ini + 30min, ...]` (atraso) → `INICIO_JORNADA = T` + toast informativo "Atraso de N min".
- [ ] Login às `T` em `[..., h_ini - 30min)` (antecipação) → diálogo modal com progress bar 60s; SIM → `INICIO_JORNADA = T, origem=AGENTE_CONFIRMADO`; NÃO ou timeout → `INICIO_JORNADA = h_ini, origem=AGENTE_CONFIRMADO`.
- [ ] Em sábado/domingo, se `trabalha_fim_de_semana=false`, nenhum INICIO_JORNADA é registrado.

### RF-004
- [ ] Inatividade ≥ 10 min contínuos cuja janela intersecta `[h_alm_saida - 30min, h_alm_saida + 30min]` → `SAIDA_ALMOCO = t_inicio_inatividade`, origem `AGENTE_AUTOMATICO`, sem prompt.
- [ ] Inatividade ≥ 10 min fora da janela não cria SAIDA_ALMOCO.
- [ ] Não há almoço → jornada continua sem SAIDA_ALMOCO/RETORNO_ALMOCO; total diário = `FIM - INICIO`.

### RF-005
- [ ] Primeiro input após SAIDA_ALMOCO dentro de `[h_alm_retorno - 30min, h_alm_retorno + 30min]` → `RETORNO_ALMOCO = T`, sem prompt.
- [ ] Primeiro input fora da janela → diálogo com progress bar 60s; SIM → `RETORNO_ALMOCO = T, origem=AGENTE_CONFIRMADO`; NÃO ou timeout → marcação com `status=PENDENTE` e jornada `PENDENTE`.
- [ ] Marcação PENDENTE listada na Web em destaque (badge vermelho) e bloqueia fechamento da jornada até ajuste.

### RF-006
- [ ] Ao atingir `h_fim`, diálogo modal aparece com progress bar 60s; SIM → form de atividade obrigatório (≥10 chars) → ao salvar, `FIM_JORNADA = T_confirmacao_dialogo`, status `FECHADA`.
- [ ] Timeout 60s → "Lembrar em 30 min" (equivalente a NÃO) → re-prompt após 30 min.
- [ ] Inatividade ≥ 60 min após `h_fim` sem confirmação → `FIM_JORNADA = último_input`, status jornada `PENDENTE`, sem atividade gravada.
- [ ] Atividade < 10 chars bloqueia salvar com mensagem inline.

### RF-007.1
- [ ] `GET /api/v1/jornadas?mes=2026-05` retorna 1 entrada por dia com `tem_marcacao_pendente`, 4 horários, total e status.
- [ ] Web exibe badge colorido para cada status; linhas com `tem_marcacao_pendente=true` exibem badge PENDENTE.
- [ ] Tabela ordenada por data crescente.

### RF-007.2
- [ ] Edição de jornada `FECHADA` exige justificativa ≥ 5 chars.
- [ ] Após salvar, status passa a `AJUSTADA_MANUALMENTE` e total é recalculado.
- [ ] Um `log_auditoria` é criado com `antes_json`, `depois_json`, `motivo`, `autor`=email do Terceiro.

### RF-007.3
- [ ] POST `/api/v1/jornadas/manual` em dia sem jornada existente cria jornada com `status=AJUSTADA_MANUALMENTE`, 4 marcações `origem=AJUSTE_WEB`, 1 atividade e 1 justificativa.
- [ ] Em dia com jornada existente, endpoint retorna `409 CONFLICT`.

### RF-007.4
- [ ] Editar atividade existente gera log de auditoria sobre entidade `Atividade`; `atividade.atualizado_em` é atualizado.
- [ ] Tentar gravar atividade < 10 chars retorna `422 VALIDATION_ERROR`.

### RF-007.5
- [ ] `PUT /api/v1/terceiros/me` atualiza todos os campos exceto senha; gera log de auditoria sobre entidade `Terceiro`.
- [ ] `PUT /api/v1/terceiros/me/senha` exige `senha_atual` válida; falha retorna `401 UNAUTHORIZED`.
- [ ] Troca de senha bem-sucedida revoga **todos** os refresh tokens ativos do Terceiro na mesma transação.
- [ ] KEK é imutável — `smtp_config` não requer re-cifragem na troca de senha.

### RF-008
- [ ] Job APScheduler em 00:00 BRT do dia 1 gera PDF do mês anterior; se o serviço estava offline, executa assim que voltar (misfire_grace_time=3600s, coalesce=true).
- [ ] PDF contém: cabeçalho (nome, empresa, CNPJ, mês/ano), tabela de dias (data, dia da semana, 4 horários, total, indicador de ajuste), total mensal, seção "Atividades" agrupada por dia.
- [ ] `POST /api/v1/relatorios/{mes}/enviar` envia o PDF cached por SMTP (timeout=30s, 3× retry); sucesso → `HistoricoEnvioRelatorio(SUCESSO)`; falha → `HistoricoEnvioRelatorio(FALHA, erro_mensagem)`.
- [ ] `POST /api/v1/relatorios/{mes}/enviar` retorna `422` com `code="SMTP_NOT_CONFIGURED"` se `smtp_config` ausente.
- [ ] Quando jornada do mês muda, `relatorio_gerado.invalidado_em` é setado; `GET /relatorios/{mes}/meta` retorna `invalidado_em` não-nulo; frontend exibe badge âmbar.
- [ ] Retenção: PDFs com `gerado_em` > 24 meses são purgados por job semanal (arquivo físico + registro em `relatorio_gerado`); operação registrada em log estruturado.
- [ ] Geração de PDF envolvida em `asyncio.wait_for(timeout=120)`.

### RF-009
- [ ] `POST /api/v1/auth/login` válido retorna `access_token` (exp 15 min) + `refresh_token` (exp 30 dias) + `terceiro_id`.
- [ ] Acesso com token expirado retorna `401`; Axios intercepta, faz `POST /auth/refresh` e refaz a requisição original transparentemente.
- [ ] Refresh rotation: cada uso gera novo refresh e invalida o anterior; reuso de token revogado retorna `401` e revoga toda a cadeia daquele Terceiro.
- [ ] `logout` revoga o refresh atual.
- [ ] `POST /auth/login` limitado a ≤5 tentativas/min por IP+email; `POST /auth/refresh` a ≤10/min.

### RF-010
- [ ] Toda mutação via Web gera 1 linha em `log_auditoria` com `antes_json`/`depois_json`/`motivo`/`autor`/`criado_em`; `expira_em` populado conforme config (NULL na v1.0).
- [ ] `GET /api/v1/auditoria?entidade=Jornada&entidade_id=<id>` exige autenticação JWT; retorna histórico ordenado decrescente por `criado_em`.
- [ ] A Web `/jornadas/:id` exibe histórico colapsado em ordem cronológica reversa.

### RF-011
- [ ] Agente envia `POST /marcacoes` com `idempotency_key` único; repetir a mesma chave retorna `201` com o registro existente.
- [ ] Conflito com `Marcacao` já ajustada via `AJUSTE_WEB` → Backend responde `409 CONFLICT`; Agente descarta tentativa local.
- [ ] Sem AJUSTE_WEB, vence `horario_efetivo` mais recente; empate exato → mantém origem AGENTE.
- [ ] Sync drena fila pendente em ordem cronológica (`criado_em` asc) a cada 30s; `proxima_tentativa_em` reflete backoff do circuit breaker.

### RF-012
- [ ] No primeiro acesso Web (sem `privacy_acceptance`), `/privacidade` é a única rota acessível; outras rotas redirecionam para `/privacidade`.
- [ ] Após `POST /api/v1/privacidade/aceitar`, usuário pode navegar livremente.
- [ ] Aviso não reaparece em logins subsequentes; rota `/privacidade` redireciona para `/jornadas` se aceite existir.
- [ ] `versao_aviso` é um identificador versionado (ex: `"1.0"`) que permite re-exibição em futuras versões do texto.

### RF-013
- [ ] `GET /api/v1/ready` sem autenticação retorna `{"status":"ready"}` quando SQLite acessível (SELECT 1 OK) e APScheduler em `STATE_RUNNING`.
- [ ] Retorna `503` se banco indisponível ou APScheduler parado.
- [ ] Instalador MSI usa `/ready` para aguardar Backend pronto após start do Service.
- [ ] Tray icon usa `/ready` para exibir estado de conectividade (distinto de `/health`).

## 9. Quality Gates

- Cobertura: ≥ 80% no Backend e Web; ≥ 70% no Agente (camadas Domain + Infra, excluindo UI WPF).
- Lint: ruff (Python), eslint + prettier (TS), `dotnet format` + analyzers (C#).
- Tipagem: mypy strict no Backend; `tsc --noEmit` no Web; nullable reference types no Agente.
- E2E Playwright: fluxos "Onboarding completo", "Dia normal", "Ajuste manual", "Envio de relatório".
- Smoke test do MSI no CI: instalação silenciosa, sobe os 2 services, `GET /api/v1/health` retorna `200`, `GET /api/v1/ready` retorna `200`, desinstalação limpa.

## 10. Decisões e Trade-offs

| Decisão | Alternativa descartada | Justificativa |
| ------- | ---------------------- | ------------- |
| Backend em FastAPI + SQLite + SQLCipher | Backend em .NET único processo unificado com o Agente | Manter separação clara entre coleta (Windows-native em .NET) e domínio/regras/relatório (Python com WeasyPrint + ecossistema de auth/orm maduro). Facilita futura portabilidade do Backend para macOS/Linux sem mexer no Agente. |
| Agente em .NET 8 WPF + Service | Agente em Electron ou Python `pywin32` | WPF/.NET é nativo Windows com integração profunda em `GetLastInputInfo`, event log de sessão, named pipes e Windows Service; Electron pesaria 300+ MB e violaria RNF-001; `pywin32` tem APIs frágeis para Service+UI. |
| SQLite serial em vez de Postgres | Postgres local empacotado | 1 Terceiro por instalação; volume baixíssimo; eliminar 1 binário pesado simplifica MSI e RAM. Trade-off de contenção é aceitável. |
| KEK gerada na instalação (DPAPI) para SQLCipher e SMTP — sem derivação da senha do Terceiro | Derivar chave SQLCipher da senha do Terceiro via Argon2id | Chave derivada da senha cria dependência entre autenticação e criptografia em repouso: troca de senha forçaria re-cifragem do banco inteiro (operação lenta, risco de corrupção) e de `smtp_config.password_enc`. KEK imutável + DPAPI elimina esse problema, é mais robusta e evita vetores de ataque por força bruta via salt. Alternativa descartada: dois contextos HKDF derivados da senha — mantém o problema de re-cifragem na troca. |
| `smtp_config.username_enc` criptografado (AES-GCM) | `username` em texto claro | Consistência com `password_enc`; username SMTP revela identidade do serviço de e-mail do Terceiro; custo de implementação zero (mesma lógica). |
| Nonce AES-GCM armazenado como `nonce‖ciphertext‖tag` | Nonce em coluna separada | Formato compacto, auto-contido, sem risco de dessincronia entre colunas. Nonce de 12 bytes CSPRNG único por cifragem. |
| Dois contextos HKDF distintos (`info="db"` e `info="smtp"`) | Mesma chave para DB e SMTP | Isolamento de segurança: comprometimento de um contexto não expõe o outro. |
| JWT com refresh rotation + revogação em cadeia | Sessão de servidor stateful | Refresh rotation persistido dá revogação real (logout/troca de senha invalida tudo) sem Redis local; reuso detectado revoga toda a cadeia (proteção contra token theft). |
| OpenAPI UI desabilitado em produção | UI sempre habilitada em `127.0.0.1` | Reduz superfície de ataque; processo local malicioso não pode explorar a interface para enumerar endpoints. Habilitado em dev via flag. |
| `POST /api/v1/terceiros` retorna `403` após setup | Endpoint removido no MSI | Mais simples de implementar e manter; evita panic em código que tenta chamar o endpoint. |
| Rate limiting com `slowapi` em `/auth/login` e `/auth/refresh` | Sem rate limiting (bind `127.0.0.1` como proteção) | Processo local malicioso pode fazer brute force; `127.0.0.1` não é proteção suficiente. |
| `/api/v1/ready` separado de `/api/v1/health` | Único endpoint de health | `/health` = liveness (processo vivo, sem banco); `/ready` = readiness (banco + scheduler). Evita falso "down" durante migration ou geração de PDF; usado pelo instalador antes do primeiro login. |
| Timeout de 60s com progress bar nos diálogos WPF | Sem timeout (bloqueante) | Usuário ausente não deve bloquear a máquina indefinidamente; progress bar visual sinaliza urgência sem surpresa. Ação padrão = NÃO/PENDENTE para evitar registros indesejados por timeout. |
| `tem_marcacao_pendente` no `JornadaResumo` | Carregar detalhe de cada jornada para detectar PENDENTE | Evita N requests na listagem mensal; campo derivado calculado em query com JOIN; custo de transmissão mínimo (1 bool por linha). |
| `smtp_config.password_enc` e `username_enc` no Backend (não no Agente) | Agente gerencia SMTP | Backend é o responsável por envio; manter credenciais no lado que as usa; Agente não precisa de acesso a SMTP. |
| `idempotency_key` UUID v4 obrigatório no POST /marcacoes | Dedup por timestamp+tipo | Garante retries seguros no Polly e simplifica resolução de conflitos. |
| Conflito: AJUSTE_WEB sempre vence + last-write-wins + empate → Agente vence | CRDT ou versão por incremento | Modelo simples, determinístico; reflete intenção do usuário (ajuste manual é "verdade declarada"). |
| `email_contato` é também o login | Login separado (username) | Reduz campos no cadastro; coincide com Discovery. |
| Fuso horário fixo `America/Sao_Paulo` | Detectar timezone do SO | Brasil sem DST desde 2019; elimina ambiguidades em relatórios mensais. |
| MSI assinado, sem auto-update | Squirrel / Wix Burn bootstrap | Reduz superfície de risco; release manual aceitável no escopo. |
| WeasyPrint para PDF | ReportLab / PDFkit | Templates HTML+CSS alinhados com stack Web; mais rápido de escrever e manter. |
| Tray em `NotifyIcon` (WinForms) | WPF puro com Win32 manual | `NotifyIcon` é a API consagrada; risco sem benefício de reimplementar. |
| Aviso de privacidade one-time persistido localmente | Modal a cada login + endpoints LGPD completos | v1.0 atende informação ao titular; export/exclusão em fase 2. |
| Endpoints em pt-BR (`/jornadas`, `/marcacoes`) | Endpoints em inglês | Discovery e domínio do usuário falam pt-BR; código interno em inglês permanece. |
| Índice composto `(terceiro_id, data)` substituindo `idx_jornada_data` | Índice simples por `data` | Composto cobre o mesmo caso e é mais seletivo para queries com filtro de terceiro+período. |
| Coluna `log_auditoria.expira_em` adicionada (NULL na v1.0) | Sem TTL (purge por migration destrutiva futura) | Prepara infra para purge futuro sem migration destrutiva; sem custo na v1.0. |
| Coluna `atividade.atualizado_em` adicionada | Sem timestamp de atualização | Necessário para snapshot temporal do `antes_json` no log de auditoria de edição inline (RF-007.4). |

## 11. Ambiguity Report

| Dimensão            | Score | Mín   | Status | Notas |
| ------------------- | ----- | ----- | ------ | ----- |
| Goal Clarity        | 0.93  | 0.75  | OK     | Goal e público bem definidos no Discovery; enriquecimento não alterou o escopo. |
| Boundary Clarity    | 0.92  | 0.70  | OK     | In/Out of scope amplo e explícito; novos itens de segurança e resiliência clarificados. |
| Constraint Clarity  | 0.92  | 0.65  | OK     | KEK/DPAPI, rate limiting, timeouts, logs, permissões de arquivo — todos documentados. |
| Acceptance Criteria | 0.92  | 0.70  | OK     | Todo RF tem ≥1 critério verificável; novos RFs (RF-013) cobertos; nenhum critério órfão. |
| **Ambiguity**       | 0.08  | ≤0.20 | OK     | Todos os conflitos entre consultores resolvidos; nenhuma decisão pendente. |
