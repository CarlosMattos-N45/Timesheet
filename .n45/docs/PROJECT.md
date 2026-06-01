---
created_at: "2026-06-01 10:20:05"
description: Sistema hibrido full-local de marcacao de jornada de trabalho para Terceiros (prestadores de servico)
n45_version: 0.2.0
type: desktop-app-windows
---
## Visao Geral

Timesheet Terceiros e um sistema hibrido full-local (sem dependencias de cloud) composto por: (1) um Agente Desktop Windows que monitora o login/logout e inatividade para registrar automaticamente as 4 marcacoes diarias da jornada de trabalho de um Terceiro (prestador de servico); (2) uma Web SPA React servida pelo proprio backend para visualizacao, ajustes manuais auditaveis e configuracao; (3) um Backend Python (FastAPI + SQLite+SQLCipher) que persiste tudo localmente e gera/envia o relatorio mensal em PDF via SMTP ao e-mail da Empresa Contratante. A distribuicao e feita via MSI Windows que instala dois Windows Services (backend e agente) e configura autostart da UI do agente.

## Modulos / Dominios

| Modulo              | Responsabilidade                                                                              |
| ------------------- | --------------------------------------------------------------------------------------------- |
| Auth                | Autenticacao JWT (access 15 min + refresh 30 dias com rotation), rate limiting no login      |
| Terceiros           | Cadastro unico do Terceiro (single-tenant), troca de senha com revogacao de tokens           |
| Jornadas            | Registro diario de jornada, status (EM_ANDAMENTO, FECHADA, AJUSTADA_MANUALMENTE, PENDENTE)   |
| Marcacoes           | 4 marcacoes diarias (INICIO_JORNADA, SAIDA_ALMOCO, RETORNO_ALMOCO, FIM_JORNADA) com idempotencia e regra de conflito Agente vs Web |
| Atividades          | Descricao da atividade do dia associada a cada jornada (min 10 chars)                        |
| Justificativas      | Justificativas obrigatorias em ajustes manuais de horarios                                   |
| Auditoria           | Log de auditoria generico (antes/depois em JSON) para rastreabilidade de toda alteracao manual |
| Relatorios          | Geracao de PDF mensal via WeasyPrint, agendamento APScheduler (dia 1 mensal), envio SMTP     |
| Historico Envio     | Registro de cada envio de relatorio (destinatario, data, status)                             |
| SMTP Config         | Configuracao do servidor SMTP do Terceiro, senha cifrada AES-GCM                             |
| Privacidade         | Aceite one-time do aviso de privacidade, persistido em banco                                  |
| Agente Desktop      | Monitoramento de login/logout Windows, deteccao de inatividade, diálogos de confirmacao, sincronizacao com backend |
| Instalador          | MSI WiX com 2 Windows Services, ACLs ProgramData, autostart UI                              |

## Modelo de Dados

| Entidade                  | Campos-chave                                               | Relacoes                              |
| ------------------------- | ---------------------------------------------------------- | ------------------------------------- |
| terceiro                  | id (UUID), email_contato (UNIQUE), senha_hash, 4 horarios, empresa_cnpj | 1:N com jornada, refresh_token, smtp_config |
| jornada                   | id, terceiro_id, data (YYYY-MM-DD), status, total_horas_apuradas_s | 1:N com marcacao, justificativa; 1:1 com atividade |
| marcacao                  | id, jornada_id, tipo, horario_registrado, horario_efetivo, origem, status, idempotency_key (UNIQUE) | N:1 com jornada |
| atividade                 | id, jornada_id (UNIQUE), descricao (min 10 chars)          | 1:1 com jornada                       |
| justificativa             | id, jornada_id, motivo, usuario_responsavel                | N:1 com jornada                       |
| log_auditoria             | id, entidade, entidade_id, autor, antes_json, depois_json, motivo | independente (referencia soft) |
| historico_envio_relatorio | id, mes_referencia (YYYY-MM), email_destinatario, status   | independente                          |
| smtp_config               | id, terceiro_id (UNIQUE), host, port, username, password_enc (AES-GCM) | 1:1 com terceiro |
| refresh_token             | id, terceiro_id, token_hash, revogado                      | N:1 com terceiro                      |
| privacidade               | id, aceito_em                                              | singleton (max 1 registro)            |
| agente_estado             | id, tipo_marcacao_pendente, sincronizado_em                | estado interno do agente              |

## Usuarios e Perfis

| Perfil   | Descricao                                       | Permissoes principais                                              |
| -------- | ----------------------------------------------- | ------------------------------------------------------------------ |
| Terceiro | Prestador de servico — unico usuario do sistema | CRUD jornadas/marcacoes, ajuste manual, config SMTP, troca de senha |

## Funcionalidades

- **Registro automatico de jornada:** Agente Desktop captura INICIO_JORNADA (login Windows), SAIDA_ALMOCO (inatividade >= 10 min na janela configurada), RETORNO_ALMOCO (primeiro input pos-almoco) e FIM_JORNADA (dialogo no horario cadastrado)
- **Diálogos de confirmacao:** toasts nativos auto-fechados em 10s para saudacao; dialogo modal com timeout 60s para FIM_JORNADA (re-prompt a cada 30 min); marcacao PENDENTE em caso de negativa
- **Sincronizacao Agente-Backend:** a cada 30s quando backend acessivel, via idempotency_key; regra de conflito RN-012 (AJUSTE_WEB vence, last-write-wins, empate Agente vence)
- **Listagem e detalhe de jornadas:** DataGrid mensal com 4 horarios, total diario/mensal, badges de status, flag tem_marcacao_pendente
- **Ajuste manual auditavel:** edicao de horarios de jornada FECHADA com justificativa obrigatoria e geracao de log_auditoria
- **Criacao manual de jornada:** para dias sem eventos automaticos (4 horarios + atividade + justificativa)
- **Relatorio mensal em PDF:** gerado automaticamente no dia 1 de cada mes e on-demand; enviado por SMTP ao email_destinatario_relatorio; retencao de 24 meses
- **Aviso de privacidade:** modal one-time no primeiro acesso Web, persistido em banco
- **Configuracao SMTP:** interface Web para configurar servidor SMTP do Terceiro; senha cifrada AES-GCM
- **Instalador MSI:** setup silencioso com 2 Windows Services + autostart da UI do agente + ACLs

## Fluxos Principais

### Registro automatico de marcacao (fluxo nominal)

1. Terceiro faz login no Windows
2. Agente detecta evento de login → registra INICIO_JORNADA com horario_registrado = agora
3. Backend aplica regra de tolerancia (±30 min); retorna marcacao com status CONFIRMADA ou PENDENTE
4. Ao detectar inatividade >= 10 min na janela de saida para almoco → registra SAIDA_ALMOCO automaticamente
5. Ao detectar primeiro input pos-inatividade → exibe dialogo de RETORNO_ALMOCO; confirma ou marca PENDENTE
6. No horario cadastrado de fim de jornada → exibe dialogo modal (timeout 60s, padrao "NAO / Lembrar em 30 min")
7. Terceiro confirma → Agente registra FIM_JORNADA + captura atividade do dia (min 10 chars) → jornada FECHADA
8. Agente sincroniza marcacoes com backend via idempotency_key

### Ajuste manual de jornada

1. Terceiro acessa /jornadas no browser
2. Seleciona jornada FECHADA → clica em editar horario
3. Informa novo horario + justificativa obrigatoria → POST /jornadas/:id/ajuste
4. Backend altera status para AJUSTADA_MANUALMENTE + gera log_auditoria (antes/depois JSON)
5. Accordion de auditoria exibe historico na pagina de detalhe

### Envio de relatorio mensal

1. APScheduler dispara job no dia 1 de cada mes as 00:00 America/Sao_Paulo
2. Backend gera PDF do mes anterior via WeasyPrint + Jinja2
3. Envia por SMTP ao email_destinatario_relatorio do Terceiro
4. Registra resultado em historico_envio_relatorio
5. Terceiro pode tambem gerar/enviar on-demand pela pagina /relatorios

## Regras de Negocio

- Single-tenant: somente um Terceiro pode estar cadastrado no sistema (endpoint POST /terceiros retorna 409 se ja existe)
- Marcacoes sao idempotentes: idempotency_key UUID unico por marcacao; duplicata retorna 200 sem criar novo registro
- Regra de conflito RN-012: AJUSTE_WEB sempre vence; senao last-write-wins por horario_efetivo; empate → Agente vence
- Horarios devem ser cronologicos: inicio_jornada < saida_almoco < retorno_almoco < fim_jornada (validado em CREATE de terceiro)
- Jornada so pode ser criada manualmente para dia sem jornada existente (UNIQUE terceiro_id + data)
- Jornada FECHADA pode ser ajustada (AJUSTADA_MANUALMENTE) mas nao revertida para EM_ANDAMENTO
- Ajuste manual exige justificativa com minimo 5 chars
- Atividade do dia exige minimo 10 chars
- Troca de senha revoga todos os refresh tokens ativos + re-cifra smtp_config.password_enc na mesma transacao
- Relatorio PDF retido por 24 meses; job de purga futuro
- Inatividade de FIM_JORNADA: se sem input por >= 60 min apos horario cadastrado, auto-encerra a jornada
- Trabalha_fim_de_semana: se false, backend rejeita marcacoes em sabado/domingo (HTTP 422)

## Endpoints

```
GET  /api/v1/health
     Response 200: {"status": "ok", "version": "0.1.0"}

GET  /api/v1/ready
     Response 200: {"status": "ready"}

POST /api/v1/auth/login
     Request: {"email": "...", "senha": "..."}
     Response 200: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
     Response 401: {"detail": "credenciais invalidas"}
     Response 429: {"detail": "muitas tentativas — aguarde"}

POST /api/v1/auth/refresh
     Request: {"refresh_token": "..."}
     Response 200: {"access_token": "...", "refresh_token": "..."}
     Response 401: {"detail": "token invalido ou revogado"}

POST /api/v1/terceiros
     Request: {"nome": "...", "empresa_nome": "...", "empresa_cnpj": "14 digitos", "horario_inicio_jornada": "HH:MM:SS", ...}
     Response 201: {terceiro object}
     Response 409: {"detail": "terceiro ja cadastrado"}

GET  /api/v1/terceiros/me
     Response 200: {terceiro object sem senha_hash}

PUT  /api/v1/terceiros/me
     Request: {campos editaveis}
     Response 200: {terceiro atualizado}

POST /api/v1/terceiros/me/senha
     Request: {"senha_atual": "...", "nova_senha": "..."}
     Response 200: {"message": "senha alterada"}
     Response 401: {"detail": "senha atual incorreta"}

GET  /api/v1/privacidade
     Response 200: {"aceito": true|false, "aceito_em": "ISO8601"|null}

POST /api/v1/privacidade/aceitar
     Response 200: {"aceito": true, "aceito_em": "ISO8601"}

GET  /api/v1/smtp
     Response 200: {smtp_config sem password_enc}

PUT  /api/v1/smtp
     Request: {"host": "...", "port": 587, "username": "...", "password": "..."}
     Response 200: {smtp_config}

POST /api/v1/smtp/test
     Response 200: {"message": "email de teste enviado"}
     Response 422: {"detail": "falha no envio: <motivo>"}

POST /api/v1/marcacoes
     Request: {"tipo": "INICIO_JORNADA", "horario_registrado": "ISO8601", "idempotency_key": "UUID"}
     Response 201: {marcacao object}
     Response 200: {marcacao existente — idempotencia}
     Response 422: {"detail": "fim de semana nao permitido"}

GET  /api/v1/marcacoes?data=YYYY-MM-DD
     Response 200: [lista de marcacoes do dia]

PUT  /api/v1/marcacoes/:id
     Request: {"horario_efetivo": "ISO8601", "origem": "AJUSTE_WEB"}
     Response 200: {marcacao atualizada}

GET  /api/v1/jornadas?mes=YYYY-MM
     Response 200: [lista de jornadas do mes com marcacoes]

GET  /api/v1/jornadas/:id
     Response 200: {jornada com marcacoes, atividade, justificativas, auditoria}

POST /api/v1/jornadas/manual
     Request: {"data": "YYYY-MM-DD", "marcacoes": [...], "atividade": "...", "justificativa": "..."}
     Response 201: {jornada criada}

PUT  /api/v1/jornadas/:id/horarios
     Request: {"marcacoes": [...], "justificativa": "..."}
     Response 200: {jornada atualizada com status AJUSTADA_MANUALMENTE}

PUT  /api/v1/jornadas/:id/atividade
     Request: {"descricao": "..."}
     Response 200: {atividade atualizada}

GET  /api/v1/relatorios?mes=YYYY-MM
     Response 200: {meta do relatorio ou 404 se nao gerado}

POST /api/v1/relatorios/gerar
     Request: {"mes": "YYYY-MM"}
     Response 202: {"message": "geracao em andamento"}

POST /api/v1/relatorios/enviar
     Request: {"mes": "YYYY-MM"}
     Response 200: {"message": "relatorio enviado"}

GET  /api/v1/config
     Response 200: {"version": "0.1.0", "dev": true|false}
```

## Rotas / Paginas

| Rota                      | Pagina            | Acesso                        |
| ------------------------- | ----------------- | ----------------------------- |
| /login                    | Login             | publico                       |
| /privacidade              | Privacidade       | publico (one-time modal)      |
| /jornadas                 | JornadasMes       | autenticado                   |
| /jornadas/:id             | JornadaDetalhe    | autenticado                   |
| /jornadas/manual          | JornadaManual     | autenticado                   |
| /relatorios               | Relatorios        | autenticado                   |
| /cadastro                 | Cadastro          | autenticado                   |
| /senha                    | Senha             | autenticado                   |
| /configuracoes/smtp       | SMTPConfig        | autenticado                   |

## Integracoes Externas

| Servico     | Finalidade                                     | Protocolo                           |
| ----------- | ---------------------------------------------- | ----------------------------------- |
| SMTP (generico) | Envio do relatorio PDF mensal ao destinatario | smtplib — SMTP com TLS/STARTTLS, timeout 30s, retry 3x backoff 5s |

## Fluxo de Dados

- **Agente → Backend (sincronizacao):** Agente acumula marcacoes em SQLite local; a cada 30s tenta POST /api/v1/marcacoes com idempotency_key; backend aplica regra de conflito RN-012; Agente atualiza estado local conforme resposta
- **Backend → Frontend (SPA):** Em producao, FastAPI serve o bundle React estatico em `/`; requests API vao para `/api/v1/`; em dev, Vite dev server (porta 5173) e o backend (porta 8765) rodam separados com CORS permissivo via TIMESHEET_DEV=true
- **Backend → SMTP (relatorio):** APScheduler job dispara geracao PDF no dia 1 mensal; PDF e armazenado em `pdfs/`; smtplib envia ao email_destinatario; historico registrado independentemente do resultado do envio

## Glossario

| Termo                    | Definicao                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------------- |
| Terceiro                 | Prestador de servico que usa o sistema para registrar sua jornada                           |
| Empresa Contratante      | Empresa que recebe o relatorio mensal do Terceiro por e-mail                                |
| Jornada                  | Registro diario de trabalho com 4 marcacoes, atividade e status                            |
| Marcacao                 | Um dos 4 pontos da jornada: INICIO_JORNADA, SAIDA_ALMOCO, RETORNO_ALMOCO, FIM_JORNADA      |
| Agente Desktop           | Processo .NET 8 rodando como Windows Service que monitora eventos do SO e sincroniza marcacoes |
| Idempotency Key          | UUID v4 que garante que a mesma marcacao nao seja registrada duas vezes                     |
| KEK                      | Key Encryption Key — chave mestra que protege a chave do banco SQLCipher                   |
| DPAPI                    | Data Protection API do Windows — usada para proteger KEK e tokens do agente em producao    |
| Single-tenant            | Sistema projetado para um unico Terceiro por instalacao                                     |
| RN-012                   | Regra de conflito de sincronizacao: AJUSTE_WEB > last-write-wins > Agente                  |
