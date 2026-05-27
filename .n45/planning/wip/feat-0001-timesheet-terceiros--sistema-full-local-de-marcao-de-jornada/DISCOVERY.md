---
created_at: "2026-05-27 11:44:10"
id: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
n45_version: 0.2.0
title: TimeSheet Terceiros — Sistema Full-Local de Marcação de Jornada
type: feat
---
## As Is (hoje)

Não existe sistema. O Terceiro registra a jornada manualmente em planilhas ou ferramentas externas, sem automação, sem evidência de marcações reais, e sem padronização para o relatório mensal entregue à Empresa Contratante.

Dores:
- Marcações esquecidas ou imprecisas (Terceiro depende de memória)
- Trabalho repetitivo de consolidar horas no fim do mês
- Falta de rastreabilidade de ajustes (quem alterou o quê, quando, por quê)
- Ausência de comprovação automática de jornada
- Risco de divergências entre o que o Terceiro lembra e o que entrega à Contratante

## To Be (depois)

Sistema híbrido **Agente Desktop + Web SPA + Backend local** que:
- Registra automaticamente as 4 marcações da jornada (início, saída/retorno de almoço, fim) na máquina do Terceiro
- Aplica janelas de tolerância de ±30 min em torno dos horários cadastrados
- Permite ajustes manuais via Web com justificativa obrigatória e auditoria imutável
- Gera relatório mensal em PDF e envia automaticamente por SMTP à Empresa Contratante
- Roda 100% local na máquina do Terceiro — única dependência externa é SMTP

**Público-alvo**: Profissionais terceirizados (autônomos PF ou PJ) que prestam serviço a Empresas Contratantes e precisam de comprovação mensal de jornada.

## Plataforma

- **Desktop**: Windows 10 build 1809+ / Windows 11 (Agente .NET nativo)
- **Web SPA local**: navegador moderno do Terceiro (Chromium/Firefox/Edge) acessando `http://localhost:8765` (porta default, configurável na instalação)

A arquitetura é desacoplada para permitir portabilidade futura a macOS/Linux, mas a entrega da v1.0 é Windows-only.

## Stack

### Distribuição
- **Instalador**: WiX Toolset (MSI assinado)
- Instala em uma única operação:
  - Agente .NET 8 (Windows Service `TimesheetAgent` + processo WPF para diálogos, autostart)
  - Backend Python (PyInstaller `--onefile`, Windows Service `TimesheetBackend`, bind `127.0.0.1:8765`)
  - Arquivos estáticos do Web React (servidos pelo Backend em `/`)
  - Banco SQLite criptografado em `%APPDATA%\TimesheetTerceiros\db.sqlite`
- **Sem auto-update na v1.0** — release manual via MSI assinado

### Backend (Python)
- **Runtime**: Python 3.12 (embarcado via PyInstaller)
- **Framework web**: FastAPI (async, OpenAPI auto-gerado)
- **ORM + migrations**: SQLAlchemy 2.x + Alembic
- **Banco**: SQLite com SQLCipher (criptografia em repouso — RNF-004)
- **Scheduler**: APScheduler in-process (persistência em SQLite)
- **Logger**: structlog (JSON estruturado, rotação local)
- **PDF**: WeasyPrint (templates Jinja2 → HTML → PDF)
- **E-mail**: SMTP genérico via `smtplib` + Jinja2 (host/port/user/pass via configuração local)
- **Auth**: `python-jose` (JWT) + `passlib[argon2]` (hash de senha) + refresh tokens persistidos em SQLite
- **HTTP server**: Uvicorn (em modo single-worker, suficiente para localhost)

### Frontend Web (React)
- **Runtime**: React 18 + TypeScript
- **Build**: Vite
- **UI lib**: Material UI (MUI) v5 (WCAG 2.1 AA out-of-the-box — RNF-006)
- **Roteamento**: React Router v6
- **Data fetching**: TanStack Query (React Query) v5
- **Forms + validação**: React Hook Form + Zod
- **HTTP client**: Axios (com interceptor para refresh automático do JWT)
- **i18n**: textos em pt-BR fixos na v1.0 (sem framework de i18n; estrutura permite extensão futura — RNF-007)

### Agente Desktop (.NET)
- **Runtime**: .NET 8 (LTS até 2026)
- **UI**: WPF
- **Estrutura**: Windows Service (`TimesheetAgent`) + processo WPF independente para diálogos (IPC via named pipes)
- **ORM local**: Entity Framework Core + Microsoft.Data.Sqlite
- **Banco local**: SQLite em `%APPDATA%\TimesheetTerceiros\agent-queue.sqlite` (fila de sync offline-first)
- **Detecção de inatividade**: Win32 `GetLastInputInfo` via P/Invoke (polling 30s)
- **HTTP client**: `HttpClient` + Polly (retry com backoff exponencial, circuit breaker)
- **Tray icon**: `NotifyIcon` (WinForms interop, único componente fora de WPF puro)
- **Logger**: Serilog (JSON estruturado, sink de arquivo com rotação)
- **DI**: Microsoft.Extensions.DependencyInjection (HostBuilder genérico)

### Testes
- **Backend**: pytest + pytest-asyncio + httpx (paridade async com FastAPI)
- **Frontend**: Vitest + React Testing Library + Playwright (E2E em browser)
- **Agente**: xUnit + FluentAssertions + Moq

### CI/CD
- **Plataforma**: GitHub Actions
- **Pipeline**:
  - PR: lint + testes (Python, TS, .NET) em paralelo
  - Tag git `vX.Y.Z`: build do MSI assinado + upload como release artifact
- **Sem deploy automático** — distribuição manual do MSI

### Organização
- **Monorepo** com pastas por aplicação:
  - `/apps/api` — Backend Python
  - `/apps/web` — Frontend React
  - `/apps/agent` — Agente .NET
  - `/apps/installer` — projeto WiX que empacota os três anteriores
  - `/packages/contracts` — schemas OpenAPI compartilhados (gerados pelo Backend, consumidos pelo Web)

## Funcionalidades / Escopo

### Onboarding e Identidade
- Cadastro inicial via Agente Desktop (RF-002) com: nome, empresa, CNPJ (validação de dígitos), 4 horários cronológicos, flag trabalha_fim_de_semana, e-mail (login), senha + confirmação, e-mail destinatário do relatório
- Bloqueio operacional até cadastro completo
- Autenticação Web: e-mail + senha → JWT access (15 min) + refresh token (30 dias)
- Edição de cadastro via Web (RF-007.5)
- Alteração de senha via endpoint dedicado (requer senha atual)

### Registro Automático de Jornada
- **RF-001**: Saudação contextual ao login (Bom dia 00-12h / Boa tarde 12-18h / Boa noite 18-24h), toast nativo Windows com auto-close em 10s
- **RF-003**: Início de jornada disparado pelo evento de **login do Windows** (não boot do SO)
  - Dentro da tolerância (±30 min): registra automaticamente
  - Atraso > 30 min: registra + alerta informativo
  - Antecipação > 30 min: diálogo de confirmação (SIM = `T` / NÃO = horário cadastrado)
- **RF-004**: Detecção de SAIDA_ALMOCO por inatividade contínua ≥ 10 min dentro da janela `[saida_almoco ± 30min]`. Sem confirmação no momento.
- **RF-005**: RETORNO_ALMOCO pelo primeiro input pós-almoço. Fora da janela → diálogo de confirmação; resposta NÃO marca como `PENDENTE` (ajuste obrigatório via Web)
- **RF-006**: FIM_JORNADA com fluxo
  1. Diálogo modal ao atingir `fim_jornada` cadastrado
  2. Se NÃO: re-prompt a cada 30 min
  3. **Auto-encerramento** se inatividade ≥ 60 min após horário cadastrado → registra último input como FIM_JORNADA, marca Jornada como `PENDENTE` (atividade pendente)
  4. Se SIM: form de atividade obrigatório (≥ 10 chars) antes de gravar FIM_JORNADA
- **RN-001**: Janela de tolerância simétrica ±30 min em todas as marcações
- **RN-007**: Se `trabalha_fim_de_semana = false`, agente não cria Jornada automática aos sábados/domingos
- **RN-005**: Total diário = `(SAIDA_ALMOCO - INICIO_JORNADA) + (FIM_JORNADA - RETORNO_ALMOCO)`. Quando não há almoço: total = `FIM_JORNADA - INICIO_JORNADA`

### Sincronização Offline-First
- Agente persiste todas as marcações localmente (EF Core SQLite) com flag `sincronizada`
- Job de sync HTTP localhost a cada 30s quando Backend está up
- Idempotency key por marcação (UUID v4) previne duplicatas
- **Resolução de conflitos (RN-012)**:
  - Se `origem = AJUSTE_WEB`: **sempre vence**
  - Demais conflitos: last-write-wins por `horario_efetivo`
  - Em empate exato: Agente vence (origem automática)
- Health check `/api/v1/health` permite o Agente detectar Backend up/down

### Acompanhamento e Ajustes (Web)
- **RF-007.1**: Listagem mensal com todas as colunas + total mensal + badges de status (EM_ANDAMENTO / FECHADA / AJUSTADA_MANUALMENTE / PENDENTE)
- **RF-007.2**: Edição individual de horários em jornada `FECHADA` com justificativa obrigatória → status vira `AJUSTADA_MANUALMENTE` e gera `LogAuditoria`
- **RF-007.3**: Criação manual de jornada para dia sem eventos (data + 4 horários + atividade + justificativa)
- **RF-007.4**: Visualização da atividade do dia em qualquer jornada (com edição inline)
- Visualização do histórico de auditoria por jornada

### Relatório Mensal (RF-008)
- **Geração automática** via APScheduler: dia 1 de cada mês às 00:00 `America/Sao_Paulo`, para o mês anterior
- **Geração on-demand** via botão no Web (mês selecionado)
- **Conteúdo do PDF**:
  - Cabeçalho: nome do Terceiro, empresa, CNPJ, mês/ano
  - Tabela diária: data, dia da semana, 4 horários, total, indicador "Ajustada manualmente"
  - Total mensal de horas
  - Seção de atividades por dia
- **Armazenamento**: PDF gerado é persistido em `%APPDATA%\TimesheetTerceiros\relatorios\` com retenção de 24 meses; `GET /relatorios/{mes}` retorna o arquivo cached (regenera se ajuste posterior invalidou)
- **Envio por SMTP**:
  - Validação RFC 5322 do e-mail destinatário antes do envio
  - SMTP configurável (host/port/user/pass) — primeira config solicitada na primeira tentativa de envio
  - Histórico de envios persistido (data, e-mail, status)

### Auditoria e Compliance
- `LogAuditoria` genérica registrando todo ajuste manual (entidade, entidade_id, autor, antes_json, depois_json, motivo, timestamp) — RNF-008
- SQLite criptografado em repouso (SQLCipher) — RNF-004 + LGPD
- Aviso de privacidade exibido no primeiro acesso (modal one-time, persistido em flag local) — Seção 13

### Constraint de Concorrência
- ⚠️ SQLite serializa escritas. Em uma instalação por Terceiro (full-local), o volume de escrita é baixo (~dezenas de eventos/dia) e não há contenção. **Decisão**: aceitável para v1.0.

## Mudanças de Schema / Banco

Projeto greenfield — todo o schema é novo. Entidades (Backend SQLite via SQLAlchemy + Alembic):

### Terceiro (singleton — 1 registro por instalação)
```
id UUID PK
nome VARCHAR(120) NOT NULL
empresa_nome VARCHAR(150) NOT NULL
empresa_cnpj VARCHAR(14) NOT NULL  -- só dígitos
horario_inicio_jornada TIME NOT NULL
horario_saida_almoco TIME NOT NULL
horario_retorno_almoco TIME NOT NULL
horario_fim_jornada TIME NOT NULL
trabalha_fim_de_semana BOOLEAN NOT NULL DEFAULT 0
email_contato VARCHAR(254) NOT NULL UNIQUE
email_destinatario_relatorio VARCHAR(254) NULL
senha_hash VARCHAR(255) NOT NULL  -- argon2
criado_em TIMESTAMP NOT NULL
atualizado_em TIMESTAMP NOT NULL
CHECK (horario_inicio_jornada < horario_saida_almoco
       AND horario_saida_almoco < horario_retorno_almoco
       AND horario_retorno_almoco < horario_fim_jornada)
```

### Jornada
```
id UUID PK
terceiro_id UUID FK → Terceiro
data DATE NOT NULL
status ENUM('EM_ANDAMENTO','FECHADA','AJUSTADA_MANUALMENTE','PENDENTE') NOT NULL
total_horas_apuradas INTERVAL NULL  -- calculado
criada_em TIMESTAMP NOT NULL
fechada_em TIMESTAMP NULL
UNIQUE (terceiro_id, data)
INDEX (data)
```

### Marcacao
```
id UUID PK
jornada_id UUID FK → Jornada
tipo ENUM('INICIO_JORNADA','SAIDA_ALMOCO','RETORNO_ALMOCO','FIM_JORNADA') NOT NULL
horario_registrado TIMESTAMP NOT NULL
horario_efetivo TIMESTAMP NULL
origem ENUM('AGENTE_AUTOMATICO','AGENTE_CONFIRMADO','AJUSTE_WEB') NOT NULL
status ENUM('CONFIRMADA','PENDENTE','AJUSTADA') NOT NULL DEFAULT 'CONFIRMADA'
confirmado_pelo_usuario BOOLEAN NOT NULL DEFAULT 0
idempotency_key VARCHAR(36) UNIQUE NOT NULL
criada_em TIMESTAMP NOT NULL
UNIQUE (jornada_id, tipo)
```

### Atividade (1:1 com Jornada)
```
id UUID PK
jornada_id UUID FK UNIQUE → Jornada
descricao TEXT NOT NULL  -- min 10 chars (validado na app)
registrada_em TIMESTAMP NOT NULL
```

### Justificativa (N:1 com Jornada)
```
id UUID PK
jornada_id UUID FK → Jornada
motivo TEXT NOT NULL
usuario_responsavel VARCHAR(120) NOT NULL
criada_em TIMESTAMP NOT NULL
```

### LogAuditoria
```
id UUID PK
entidade VARCHAR(50) NOT NULL  -- 'Jornada' | 'Marcacao' | 'Terceiro'
entidade_id UUID NOT NULL
autor VARCHAR(120) NOT NULL
antes_json JSON NULL
depois_json JSON NOT NULL
motivo TEXT NULL
criado_em TIMESTAMP NOT NULL
INDEX (entidade, entidade_id)
INDEX (criado_em)
```

### HistoricoEnvioRelatorio
```
id UUID PK
mes_referencia VARCHAR(7) NOT NULL  -- 'YYYY-MM'
email_destinatario VARCHAR(254) NOT NULL
status ENUM('SUCESSO','FALHA') NOT NULL
erro_mensagem TEXT NULL
enviado_em TIMESTAMP NOT NULL
INDEX (mes_referencia)
```

### RefreshToken
```
id UUID PK
terceiro_id UUID FK → Terceiro
token_hash VARCHAR(255) NOT NULL
expira_em TIMESTAMP NOT NULL
revogado_em TIMESTAMP NULL
criado_em TIMESTAMP NOT NULL
INDEX (token_hash)
INDEX (expira_em)
```

### RelatorioGerado (cache de PDFs)
```
id UUID PK
mes_referencia VARCHAR(7) NOT NULL UNIQUE
caminho_arquivo VARCHAR(500) NOT NULL
gerado_em TIMESTAMP NOT NULL
invalidado_em TIMESTAMP NULL  -- nullable; quando jornada do mês muda, marca para regerar
```

### Banco local do Agente (EF Core SQLite)
- `MarcacaoLocal` — espelho de `Marcacao` + colunas extras `sincronizada (bool)`, `tentativas_sync (int)`, `ultimo_erro_sync (text)`, `proxima_tentativa_em (timestamp)`
- `EstadoJornadaAtual` — cache do estado em memória persistido (status: AGUARDANDO_INICIO / EM_JORNADA / EM_ALMOCO / AGUARDANDO_FIM / FECHADA)
- `ConfiguracaoLocal` — porta do Backend, último horário de sincronização

## Dependências e Impacto

### Externas (saída para internet)
- **SMTP**: única integração externa. Host/port/user/pass configurados pelo Terceiro (UI no Web ou primeira tentativa de envio). Suporta Gmail, Outlook, AWS SES via SMTP, Mailgun, etc.

### Dependências de runtime (Windows)
- **WeasyPrint** requer libpango/libcairo nativos — incluídos no bundle PyInstaller
- **SQLCipher** requer DLLs — incluídas no bundle

### Impacto operacional
- 2 Windows Services criados pelo instalador: `TimesheetAgent` (LocalSystem, autostart) e `TimesheetBackend` (LocalSystem, autostart)
- Porta TCP local: default 8765 (configurável na instalação para evitar conflito)
- Bind do Backend: 127.0.0.1 apenas (nunca exposto na rede)
- Tray icon do Agente sempre visível na barra de tarefas após login
- Footprint de memória: Backend ~80 MB idle, Agente ~30 MB idle (atende RNF-001 de 100 MB no Agente)

### Contratos REST (FastAPI auto-documentado em `/docs`)

```
Auth
  POST   /api/v1/auth/login          body: {email, senha}
                                      → 200 {access_token, refresh_token, terceiro_id} | 401
  POST   /api/v1/auth/refresh        body: {refresh_token}
                                      → 200 {access_token, refresh_token} | 401
  POST   /api/v1/auth/logout         (Bearer) invalida o refresh_token atual

Terceiro
  POST   /api/v1/terceiros           (público; só permite se nenhum Terceiro existe)
                                      body com todos os campos do cadastro inicial + senha
                                      → 201 {terceiro_id}
  GET    /api/v1/terceiros/me        (Bearer)
  PUT    /api/v1/terceiros/me        (Bearer)
  PUT    /api/v1/terceiros/me/senha  (Bearer) body: {senha_atual, nova_senha}

Marcações (Agente → Backend)
  POST   /api/v1/marcacoes           (Bearer) body: {tipo, horario_registrado, horario_efetivo, origem, idempotency_key}
                                      → 201 (cria/upserts Jornada do dia se necessário)
  GET    /api/v1/marcacoes?status=PENDENTE (Bearer)
  PUT    /api/v1/marcacoes/{id}      (Bearer) body: {horario_efetivo, motivo}  -- ajuste via Web

Jornadas
  GET    /api/v1/jornadas?mes=YYYY-MM        (Bearer)
  GET    /api/v1/jornadas/{id}               (Bearer) detalhe com marcações + atividade
  PUT    /api/v1/jornadas/{id}               (Bearer) body: {marcacoes: [{tipo, horario_efetivo}], motivo}
  POST   /api/v1/jornadas/manual             (Bearer) body: {data, marcacoes, atividade, motivo}
  POST   /api/v1/jornadas/{id}/atividade     (Bearer) body: {descricao} -- chamado pelo Agente no fim ou via Web

Auditoria
  GET    /api/v1/auditoria?entidade=Jornada&entidade_id={id}  (Bearer)

Relatórios
  GET    /api/v1/relatorios/{mes}              (Bearer) → application/pdf (gera+armazena se inexistente)
  POST   /api/v1/relatorios/{mes}/enviar       (Bearer) body: {email} → envia SMTP
  GET    /api/v1/relatorios/{mes}/historico    (Bearer)

Sistema
  GET    /api/v1/health                        público — usado pelo Agente para detectar Backend up/down
  GET    /api/v1/config                        público — porta, versão, fuso horário
```

## Fora do Escopo

- Integração com sistemas de RH/ERP externos
- Folha de pagamento
- Controle biométrico ou facial
- Geolocalização ou validação de presença física
- Integração com ponto eletrônico físico
- Aplicativo mobile (iOS/Android)
- Suporte multi-plataforma na v1.0 (macOS, Linux) — arquitetura permite mas não é entregue
- Multi-Terceiro no mesmo Backend (cada máquina = uma instalação isolada e independente)
- Papel administrador / RH com visão centralizada de múltiplos Terceiros
- Auto-update do Agente / Backend (v1.0 distribui MSI manualmente)
- Mecanismo formal LGPD de exportação/exclusão de dados (apenas aviso de privacidade na v1.0; endpoints dedicados ficam para fase 2)
- Cadastro/tratamento de feriados (todos os dias úteis tratados igualmente; apenas a flag `trabalha_fim_de_semana` filtra)
- Múltiplas atividades por jornada (relação 1:1 com Jornada)
- Suporte a horário de verão / DST (Brasil sem DST desde 2019)
- Métricas/observabilidade externa (Prometheus, Grafana) — apenas logs locais rotativos na v1.0
- Backup/restore automatizado do banco SQLite (responsabilidade do Terceiro via cópia de `%APPDATA%`)
